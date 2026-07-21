#!/usr/bin/env python3
"""Fail-closed P0.2 Governance authority bootstrap for Runtime Assets.

The utility deliberately separates read-only evidence generation from operator
decisions and database publication:

* ``preview`` builds a deterministic candidate packet and an optional empty
  decision template.
* ``validate-decision`` proves that a human-operator manifest covers the exact
  packet without writing a database.
* ``apply`` rebuilds the current packet, constructs a private staging database,
  verifies it with the drift doctor, and only then publishes it atomically.

This tool never creates approval decisions or claims a human reviewer identity.
"""

from __future__ import annotations

import argparse
from collections import Counter
from contextlib import closing
from datetime import datetime
import json
import os
from pathlib import Path
import sqlite3
import sys
from typing import Any, Mapping, Sequence
import uuid

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from asset_registry.repositories import LegacySkillAssetRepository
from runtime.digest import canonical_digest
from tools.governance_db import GovernanceDB
from tools.runtime_asset_drift_doctor import build_doctor_report
from tools.skill_scanner import SkillSecurityScanner


PACKET_SCHEMA_VERSION = "1.0.0"
DECISION_SCHEMA_VERSION = "1.0.0"
REPORT_SCHEMA_VERSION = "1.0.0"
PACKET_KIND = "runtime-asset-governance-candidate-packet"
DECISION_KIND = "runtime-asset-governance-operator-decision"
REQUIRED_REVIEWER_TYPE = "human_operator"


class BootstrapValidationError(ValueError):
    """Raised before publication when evidence or authority is incomplete."""


class BootstrapApplyError(RuntimeError):
    """Raised when staged construction or verification fails."""


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return canonical_digest(value)


def _scanner_rules_digest(scanner: SkillSecurityScanner) -> str:
    rules = [
        {
            "rule_id": rule.rule_id,
            "name": rule.name,
            "severity": rule.severity.value,
            "patterns": list(rule.patterns),
            "description": rule.description,
            "score_weight": rule.score_weight,
        }
        for rule in scanner.rules
    ]
    return _digest(
        {
            "scanner_version": scanner.VERSION,
            "rules": rules,
            "blocked_sources": scanner.blocked_sources,
        }
    )


def _scan_summary(scanner: SkillSecurityScanner, source_path: Path) -> dict[str, Any]:
    result = scanner.scan_skill(source_path)
    rule_counts = Counter(
        (finding.rule_id, finding.severity.value) for finding in result.findings
    )
    return {
        "risk_level": result.risk_level.value,
        "risk_score": result.risk_score,
        "blocked": result.blocked,
        "blocked_reason": result.blocked_reason,
        "files_scanned": result.files_scanned,
        "findings_count": len(result.findings),
        "findings_by_rule": [
            {
                "rule_id": rule_id,
                "severity": severity,
                "count": count,
            }
            for (rule_id, severity), count in sorted(rule_counts.items())
        ],
    }


def build_candidate_packet(
    parsed_dir: Path, *, expected_count: int | None = None
) -> dict[str, Any]:
    """Build deterministic, line-content-free review evidence for one snapshot."""

    parsed_dir = parsed_dir.resolve()
    repository = LegacySkillAssetRepository(parsed_dir)
    if repository.ambiguous_asset_ids:
        raise BootstrapValidationError(
            "ambiguous canonical Asset IDs: "
            + ", ".join(repository.ambiguous_asset_ids)
        )
    if expected_count is not None and repository.asset_count != expected_count:
        raise BootstrapValidationError(
            f"unexpected Runtime Asset count: expected {expected_count}, "
            f"found {repository.asset_count}"
        )

    scanner = SkillSecurityScanner()
    candidates: list[dict[str, Any]] = []
    asset_ids: set[str] = set()
    for revision in repository.list_revisions():
        if revision.asset_id in asset_ids:
            raise BootstrapValidationError(
                f"duplicate canonical Asset ID: {revision.asset_id}"
            )
        asset_ids.add(revision.asset_id)
        meta = revision.payload.get("meta")
        if not isinstance(meta, Mapping):
            raise BootstrapValidationError(
                f"missing payload.meta for {revision.source_path.as_posix()}"
            )
        candidates.append(
            {
                "asset_id": revision.asset_id,
                "revision_id": revision.revision_id,
                "asset_type": revision.asset_type,
                "version": "1.0.0",
                "content_hash": revision.content_hash,
                "source_digest": revision.source_digest,
                "source_path": revision.source_path.as_posix(),
                "legacy_skill_id": revision.legacy_skill_id,
                "identity_strategy": revision.identity_strategy,
                "display_title": str(meta.get("name") or revision.asset_id),
                "security_scan": _scan_summary(
                    scanner, parsed_dir / revision.source_path
                ),
            }
        )

    packet_body = {
        "schema_version": PACKET_SCHEMA_VERSION,
        "kind": PACKET_KIND,
        "snapshot_id": repository.snapshot_id,
        "candidate_count": len(candidates),
        "scanner": {
            "scanner_id": "tools.skill_scanner.SkillSecurityScanner",
            "scanner_version": scanner.VERSION,
            "rules_digest": _scanner_rules_digest(scanner),
            "redaction": "finding line content and matched text omitted",
        },
        "candidates": candidates,
    }
    return {**packet_body, "packet_digest": _digest(packet_body)}


def validate_candidate_packet(packet: Mapping[str, Any]) -> dict[str, Any]:
    if packet.get("schema_version") != PACKET_SCHEMA_VERSION:
        raise BootstrapValidationError("unsupported packet schema version")
    if packet.get("kind") != PACKET_KIND:
        raise BootstrapValidationError("invalid packet kind")
    supplied_digest = packet.get("packet_digest")
    if not isinstance(supplied_digest, str):
        raise BootstrapValidationError("packet digest is required")
    body = {key: value for key, value in packet.items() if key != "packet_digest"}
    if _digest(body) != supplied_digest:
        raise BootstrapValidationError("packet digest mismatch")
    candidates = packet.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise BootstrapValidationError("packet must contain candidates")
    if packet.get("candidate_count") != len(candidates):
        raise BootstrapValidationError("packet candidate count mismatch")
    asset_ids = [item.get("asset_id") for item in candidates if isinstance(item, Mapping)]
    if len(asset_ids) != len(candidates) or any(
        not isinstance(asset_id, str) or not asset_id for asset_id in asset_ids
    ):
        raise BootstrapValidationError("every packet candidate requires an Asset ID")
    if len(set(asset_ids)) != len(asset_ids):
        raise BootstrapValidationError("packet contains duplicate Asset IDs")
    return dict(packet)


def build_decision_template(packet: Mapping[str, Any]) -> dict[str, Any]:
    packet = validate_candidate_packet(packet)
    return {
        "schema_version": DECISION_SCHEMA_VERSION,
        "kind": DECISION_KIND,
        "packet_digest": packet["packet_digest"],
        "snapshot_id": packet["snapshot_id"],
        "reviewer_type": REQUIRED_REVIEWER_TYPE,
        "reviewer": "",
        "reviewed_at": "",
        "attestation": (
            "I reviewed every Asset decision for packet "
            f"{packet['packet_digest']}."
        ),
        "decisions": [
            {
                "asset_id": candidate["asset_id"],
                "decision": "",
                "reason": "",
            }
            for candidate in packet["candidates"]
        ],
    }


def _validate_reviewed_at(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BootstrapValidationError("reviewed_at is required")
    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise BootstrapValidationError("reviewed_at must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise BootstrapValidationError("reviewed_at must include a timezone")
    return value.strip()


def validate_operator_decision(
    packet: Mapping[str, Any], decision: Mapping[str, Any]
) -> dict[str, Any]:
    """Validate exact, complete human-operator coverage of one packet."""

    packet = validate_candidate_packet(packet)
    if decision.get("schema_version") != DECISION_SCHEMA_VERSION:
        raise BootstrapValidationError("unsupported decision schema version")
    if decision.get("kind") != DECISION_KIND:
        raise BootstrapValidationError("invalid decision kind")
    if decision.get("packet_digest") != packet["packet_digest"]:
        raise BootstrapValidationError("decision packet digest mismatch")
    if decision.get("snapshot_id") != packet["snapshot_id"]:
        raise BootstrapValidationError("decision snapshot mismatch")
    if decision.get("reviewer_type") != REQUIRED_REVIEWER_TYPE:
        raise BootstrapValidationError("reviewer_type must be human_operator")
    reviewer = decision.get("reviewer")
    if not isinstance(reviewer, str) or not reviewer.strip():
        raise BootstrapValidationError("human reviewer identity is required")
    _validate_reviewed_at(decision.get("reviewed_at"))
    expected_attestation = (
        "I reviewed every Asset decision for packet "
        f"{packet['packet_digest']}."
    )
    if decision.get("attestation") != expected_attestation:
        raise BootstrapValidationError(
            "operator attestation does not match the reviewed packet"
        )

    raw_decisions = decision.get("decisions")
    if not isinstance(raw_decisions, list):
        raise BootstrapValidationError("decisions must be a list")
    expected = {candidate["asset_id"] for candidate in packet["candidates"]}
    seen: dict[str, dict[str, str]] = {}
    for item in raw_decisions:
        if not isinstance(item, Mapping):
            raise BootstrapValidationError("every decision must be an object")
        asset_id = item.get("asset_id")
        if not isinstance(asset_id, str) or not asset_id:
            raise BootstrapValidationError("every decision requires an Asset ID")
        if asset_id in seen:
            raise BootstrapValidationError(f"duplicate decision: {asset_id}")
        if asset_id not in expected:
            raise BootstrapValidationError(f"unknown decision Asset ID: {asset_id}")
        disposition = item.get("decision")
        if disposition not in {"approve", "reject"}:
            raise BootstrapValidationError(
                f"decision must be approve or reject: {asset_id}"
            )
        reason = item.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            raise BootstrapValidationError(f"decision reason is required: {asset_id}")
        seen[asset_id] = {
            "asset_id": asset_id,
            "decision": disposition,
            "reason": reason.strip(),
        }
    missing = sorted(expected - set(seen))
    if missing:
        raise BootstrapValidationError(
            "decision omits packet Asset IDs: " + ", ".join(missing)
        )

    normalized = {
        "schema_version": DECISION_SCHEMA_VERSION,
        "kind": DECISION_KIND,
        "packet_digest": packet["packet_digest"],
        "snapshot_id": packet["snapshot_id"],
        "reviewer_type": REQUIRED_REVIEWER_TYPE,
        "reviewer": reviewer.strip(),
        "reviewed_at": _validate_reviewed_at(decision.get("reviewed_at")),
        "attestation": expected_attestation,
        "decisions": [seen[asset_id] for asset_id in sorted(seen)],
    }
    normalized["decision_digest"] = _digest(normalized)
    return normalized


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BootstrapValidationError(f"cannot read JSON evidence: {path}") from exc
    if not isinstance(value, dict):
        raise BootstrapValidationError(f"JSON evidence must be an object: {path}")
    return value


def _write_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_bytes(_canonical_json_bytes(value) + b"\n")
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _sqlite_integrity(path: Path) -> str:
    try:
        with closing(
            sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
        ) as conn:
            conn.execute("PRAGMA query_only=ON")
            row = conn.execute("PRAGMA integrity_check").fetchone()
    except sqlite3.DatabaseError as exc:
        raise BootstrapApplyError("staged Governance database is invalid") from exc
    return str(row[0]) if row else "missing"


def _verify_staged_database(
    *,
    database_path: Path,
    packet: Mapping[str, Any],
    decision: Mapping[str, Any],
    parsed_dir: Path,
    index_db: Path,
    migration_dir: Path,
) -> dict[str, Any]:
    expected = {candidate["asset_id"]: candidate for candidate in packet["candidates"]}
    decisions = {item["asset_id"]: item for item in decision["decisions"]}
    with closing(
        sqlite3.connect(
            f"file:{database_path.resolve().as_posix()}?mode=ro", uri=True
        )
    ) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only=ON")
        rows = conn.execute(
            """
            SELECT s.name, s.canonical_skill_id, s.current_revision_id,
                   sr.revision_id, sr.artifact_digest, sr.status, sr.is_current,
                   sr.approved_by, sr.approved_at
            FROM skills s
            JOIN skill_revisions sr
              ON sr.skill_id=s.skill_id AND sr.revision_id=s.current_revision_id
            WHERE s.canonical_skill_id IS NOT NULL
            ORDER BY s.canonical_skill_id
            """
        ).fetchall()
        audit_counts = {
            row["event_type"]: row["count"]
            for row in conn.execute(
                "SELECT event_type, COUNT(*) AS count FROM audit_log GROUP BY event_type"
            )
        }
        decision_events = [
            dict(row)
            for row in conn.execute(
                """
                SELECT event_type, skill_name, actor, details_json
                FROM audit_log
                WHERE event_type IN ('approve', 'reject')
                ORDER BY skill_name
                """
            )
        ]

    if len(rows) != len(expected):
        raise BootstrapApplyError("staged Governance row count mismatch")
    by_asset = {str(row["canonical_skill_id"]): row for row in rows}
    if set(by_asset) != set(expected):
        raise BootstrapApplyError("staged Governance canonical identity mismatch")
    for asset_id, candidate in expected.items():
        row = by_asset[asset_id]
        expected_status = (
            "approved" if decisions[asset_id]["decision"] == "approve" else "rejected"
        )
        if row["name"] != asset_id:
            raise BootstrapApplyError(f"Governance record name mismatch: {asset_id}")
        if row["artifact_digest"] != candidate["content_hash"]:
            raise BootstrapApplyError(f"Governance artifact digest mismatch: {asset_id}")
        if not row["current_revision_id"] or row["revision_id"] != row["current_revision_id"]:
            raise BootstrapApplyError(f"Governance current revision mismatch: {asset_id}")
        if not bool(row["is_current"]) or row["status"] != expected_status:
            raise BootstrapApplyError(f"Governance disposition mismatch: {asset_id}")
        if expected_status == "approved" and (
            row["approved_by"] != decision["reviewer"] or not row["approved_at"]
        ):
            raise BootstrapApplyError(f"Governance approval provenance missing: {asset_id}")

    expected_count = len(expected)
    required_audit = {
        "create": expected_count,
        "runtime_bind": expected_count,
        "approve": sum(
            item["decision"] == "approve" for item in decision["decisions"]
        ),
        "reject": sum(
            item["decision"] == "reject" for item in decision["decisions"]
        ),
    }
    for event_type, count in required_audit.items():
        if audit_counts.get(event_type, 0) != count:
            raise BootstrapApplyError(
                f"Governance audit count mismatch for {event_type}"
            )
    if len(decision_events) != expected_count:
        raise BootstrapApplyError("Governance decision evidence count mismatch")
    expected_evidence = {
        "packet_digest": packet["packet_digest"],
        "decision_digest": decision["decision_digest"],
        "snapshot_id": packet["snapshot_id"],
        "reviewer_type": decision["reviewer_type"],
        "reviewed_at": decision["reviewed_at"],
        "attestation": decision["attestation"],
    }
    for event in decision_events:
        asset_id = str(event["skill_name"])
        if asset_id not in decisions:
            raise BootstrapApplyError("Governance audit references an unknown Asset")
        try:
            details = json.loads(event["details_json"])
        except (TypeError, json.JSONDecodeError) as exc:
            raise BootstrapApplyError("Governance decision evidence is invalid") from exc
        if event["actor"] != decision["reviewer"]:
            raise BootstrapApplyError(
                f"Governance decision actor mismatch: {asset_id}"
            )
        if details.get("decision_evidence") != expected_evidence:
            raise BootstrapApplyError(
                f"Governance decision evidence mismatch: {asset_id}"
            )
        if details.get("reason") != decisions[asset_id]["reason"]:
            raise BootstrapApplyError(
                f"Governance decision reason mismatch: {asset_id}"
            )

    integrity = _sqlite_integrity(database_path)
    if integrity != "ok":
        raise BootstrapApplyError(f"SQLite integrity_check failed: {integrity}")
    doctor = build_doctor_report(
        parsed_dir=parsed_dir,
        index_db=index_db,
        governance_db=database_path,
        migration_dir=migration_dir,
    )
    all_approved = all(
        item["decision"] == "approve" for item in decision["decisions"]
    )
    expected_state = "healthy" if all_approved else "authority-missing"
    expected_exit = 0 if all_approved else 2
    if doctor["state"] != expected_state or doctor["exit_code"] != expected_exit:
        raise BootstrapApplyError(
            "staged doctor result does not match the operator dispositions"
        )
    return {
        "integrity_check": integrity,
        "governance_rows": len(rows),
        "audit_counts": audit_counts,
        "doctor": doctor,
    }


def apply_operator_decision(
    *,
    parsed_dir: Path,
    index_db: Path,
    migration_dir: Path,
    packet: Mapping[str, Any],
    decision: Mapping[str, Any],
    target_db: Path,
    expected_count: int = 196,
    publish: bool = True,
) -> dict[str, Any]:
    """Build, verify, and optionally publish a new authority database.

    Existing targets are intentionally refused. Replacement/restore is a separate
    operator workflow so this bootstrap cannot overwrite live authority state.
    """

    parsed_dir = parsed_dir.resolve()
    index_db = index_db.resolve()
    migration_dir = migration_dir.resolve()
    target_db = target_db.resolve()
    packet = validate_candidate_packet(packet)
    current_packet = build_candidate_packet(
        parsed_dir, expected_count=expected_count
    )
    if current_packet["packet_digest"] != packet["packet_digest"]:
        raise BootstrapValidationError("source snapshot changed after packet review")
    normalized_decision = validate_operator_decision(packet, decision)
    if target_db.exists():
        raise BootstrapApplyError(
            "target Governance database already exists; bootstrap will not overwrite it"
        )
    if not index_db.is_file():
        raise BootstrapApplyError("derived Index database is missing")

    target_db.parent.mkdir(parents=True, exist_ok=True)
    staging = target_db.with_name(f".{target_db.name}.{uuid.uuid4().hex}.staging")
    decisions = {
        item["asset_id"]: item for item in normalized_decision["decisions"]
    }
    decision_evidence = {
        "packet_digest": packet["packet_digest"],
        "decision_digest": normalized_decision["decision_digest"],
        "snapshot_id": packet["snapshot_id"],
        "reviewer_type": normalized_decision["reviewer_type"],
        "reviewed_at": normalized_decision["reviewed_at"],
        "attestation": normalized_decision["attestation"],
    }
    try:
        governance = GovernanceDB(staging)
        for candidate in packet["candidates"]:
            asset_id = candidate["asset_id"]
            item = decisions[asset_id]
            skill_id = governance.create_skill(
                name=asset_id,
                source_type="runtime_asset_registry",
                source_path=candidate["source_path"],
                author_name="Unknown",
                license_spdx="UNKNOWN",
                version=candidate["version"],
                original_format="parsed_json",
            )
            binding = governance.bind_runtime_artifact(
                skill_id,
                canonical_skill_id=asset_id,
                artifact_digest=candidate["content_hash"],
                bound_by=normalized_decision["reviewer"],
            )
            if binding is None:
                raise BootstrapApplyError(f"failed to bind Runtime Asset: {asset_id}")
            if item["decision"] == "approve":
                accepted = governance.approve_skill(
                    skill_id,
                    approved_by=normalized_decision["reviewer"],
                    reason=item["reason"],
                    decision_evidence=decision_evidence,
                )
            else:
                accepted = governance.reject_skill(
                    skill_id,
                    rejected_by=normalized_decision["reviewer"],
                    reason=item["reason"],
                    decision_evidence=decision_evidence,
                )
            if not accepted:
                raise BootstrapApplyError(
                    f"failed to apply operator disposition: {asset_id}"
                )

        verification = _verify_staged_database(
            database_path=staging,
            packet=packet,
            decision=normalized_decision,
            parsed_dir=parsed_dir,
            index_db=index_db,
            migration_dir=migration_dir,
        )
        all_approved = all(
            item["decision"] == "approve"
            for item in normalized_decision["decisions"]
        )
        if publish and not all_approved:
            raise BootstrapApplyError(
                "operator rejected one or more Assets; refusing to publish non-healthy authority"
            )
        if publish:
            try:
                os.link(staging, target_db)
            except FileExistsError as exc:
                raise BootstrapApplyError(
                    "target Governance database appeared before publication"
                ) from exc
            staging.unlink()
            published_path: str | None = str(target_db)
        else:
            published_path = None
        return {
            "schema_version": REPORT_SCHEMA_VERSION,
            "state": "published" if publish else "verified-staging",
            "packet_digest": packet["packet_digest"],
            "decision_digest": normalized_decision["decision_digest"],
            "snapshot_id": packet["snapshot_id"],
            "reviewer": normalized_decision["reviewer"],
            "reviewer_type": normalized_decision["reviewer_type"],
            "candidate_count": packet["candidate_count"],
            "published_database": published_path,
            "verification": verification,
        }
    finally:
        if staging.exists():
            staging.unlink()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="P0.2 Runtime Asset Governance authority bootstrap"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    preview = subparsers.add_parser("preview", help="build read-only review evidence")
    preview.add_argument("--parsed-dir", type=Path, default=ROOT / "parsed")
    preview.add_argument("--expected-count", type=int, default=196)
    preview.add_argument("--output", type=Path, required=True)
    preview.add_argument("--decision-template", type=Path)

    validate = subparsers.add_parser(
        "validate-decision", help="validate an operator decision without writes"
    )
    validate.add_argument("--packet", type=Path, required=True)
    validate.add_argument("--decision", type=Path, required=True)
    validate.add_argument("--output", type=Path)

    apply = subparsers.add_parser(
        "apply", help="stage, verify, and publish a new authority database"
    )
    apply.add_argument("--parsed-dir", type=Path, default=ROOT / "parsed")
    apply.add_argument("--expected-count", type=int, default=196)
    apply.add_argument("--index-db", type=Path, default=ROOT / "skills.db")
    apply.add_argument(
        "--migration-dir", type=Path, default=ROOT / "migrations" / "index"
    )
    apply.add_argument("--packet", type=Path, required=True)
    apply.add_argument("--decision", type=Path, required=True)
    apply.add_argument(
        "--target-db",
        type=Path,
        default=ROOT / "governance" / "db" / "governance.db",
    )
    apply.add_argument("--report", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "preview":
            packet = build_candidate_packet(
                args.parsed_dir, expected_count=args.expected_count
            )
            _write_json_atomic(args.output, packet)
            if args.decision_template:
                _write_json_atomic(
                    args.decision_template, build_decision_template(packet)
                )
            result = {
                "state": "awaiting-operator-decision",
                "packet_digest": packet["packet_digest"],
                "snapshot_id": packet["snapshot_id"],
                "candidate_count": packet["candidate_count"],
                "output": str(args.output.resolve()),
            }
        elif args.command == "validate-decision":
            packet = _read_json(args.packet)
            decision = _read_json(args.decision)
            normalized = validate_operator_decision(packet, decision)
            if args.output:
                _write_json_atomic(args.output, normalized)
            result = {
                "state": "valid",
                "packet_digest": normalized["packet_digest"],
                "decision_digest": normalized["decision_digest"],
                "decision_count": len(normalized["decisions"]),
            }
        else:
            packet = _read_json(args.packet)
            decision = _read_json(args.decision)
            result = apply_operator_decision(
                parsed_dir=args.parsed_dir,
                index_db=args.index_db,
                migration_dir=args.migration_dir,
                packet=packet,
                decision=decision,
                target_db=args.target_db,
                expected_count=args.expected_count,
            )
            _write_json_atomic(args.report, result)
    except BootstrapValidationError as exc:
        print(json.dumps({"state": "invalid", "error": str(exc)}))
        return 2
    except (BootstrapApplyError, OSError, sqlite3.DatabaseError) as exc:
        print(json.dumps({"state": "failed", "error": str(exc)}))
        return 3
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
