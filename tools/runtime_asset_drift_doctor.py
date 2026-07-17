#!/usr/bin/env python3
"""Read-only Registry/Index/Governance drift doctor for Runtime Assets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from asset_registry.repositories import (
    AssetSnapshotBuildError,
    LegacySkillAssetRepository,
)
from asset_registry.sqlite import load_migrations, preview_migrations


EXIT_CODES = {
    "healthy": 0,
    "stale-derived-projection": 1,
    "authority-missing": 2,
    "unknown": 3,
}


def _readonly(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(
        f"file:{path.resolve().as_posix()}?mode=ro", uri=True
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only=ON")
    return connection


def _table_exists(connection: sqlite3.Connection, name: str) -> bool:
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None


def _index_findings(
    index_db: Path,
    revisions,
) -> tuple[dict[str, list[Any]], int]:
    findings = {
        "pending_projection": [],
        "stale_index_identity": [],
        "model_version_drift": [],
        "unknown": [],
    }
    if not index_db.exists():
        findings["pending_projection"] = [item.source_path.as_posix() for item in revisions]
        return findings, 0
    try:
        with _readonly(index_db) as connection:
            if not _table_exists(connection, "asset_index_state"):
                findings["pending_projection"] = [
                    item.source_path.as_posix() for item in revisions
                ]
                return findings, 0
            rows = [
                dict(row)
                for row in connection.execute(
                    "SELECT * FROM asset_index_state ORDER BY source_path"
                )
            ]
    except sqlite3.DatabaseError as exc:
        findings["unknown"].append(
            {"code": "index_database_invalid", "detail": type(exc).__name__}
        )
        return findings, 0

    by_source = {item.source_path.as_posix(): item for item in revisions}
    indexed_sources = set()
    model_pairs = set()
    for row in rows:
        source_path = str(row["source_path"])
        indexed_sources.add(source_path)
        model_pairs.add((row["embedding_model_id"], row["embedding_model_version"]))
        revision = by_source.get(source_path)
        if revision is None:
            findings["stale_index_identity"].append(
                {"source_path": source_path, "reason": "source_removed"}
            )
        elif (
            row["asset_id"] != revision.asset_id
            or row["revision_id"] != revision.revision_id
            or row["content_hash"] != revision.content_hash
        ):
            findings["stale_index_identity"].append(
                {"source_path": source_path, "reason": "identity_mismatch"}
            )
    findings["pending_projection"] = sorted(set(by_source) - indexed_sources)
    if len(model_pairs) > 1:
        findings["model_version_drift"] = [
            {"model_id": model_id, "model_version": model_version}
            for model_id, model_version in sorted(model_pairs)
        ]
    return findings, len(rows)


def _authority_findings(governance_db: Path, revisions) -> list[dict[str, str]]:
    if not governance_db.exists():
        return [{"asset_id": "*", "reason": "governance_database_missing"}]
    try:
        with _readonly(governance_db) as connection:
            if not _table_exists(connection, "skills") or not _table_exists(
                connection, "skill_revisions"
            ):
                return [{"asset_id": "*", "reason": "governance_schema_missing"}]
            skill_columns = {
                row[1] for row in connection.execute("PRAGMA table_info(skills)")
            }
            revision_columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(skill_revisions)")
            }
            required_skills = {"skill_id", "canonical_skill_id", "current_revision_id"}
            required_revisions = {
                "skill_id", "revision_id", "artifact_digest", "status", "is_current"
            }
            if not required_skills <= skill_columns or not required_revisions <= revision_columns:
                return [{"asset_id": "*", "reason": "governance_schema_incompatible"}]
            rows = connection.execute(
                """
                SELECT s.canonical_skill_id, s.current_revision_id,
                       sr.revision_id, sr.artifact_digest, sr.status, sr.is_current
                FROM skills s
                LEFT JOIN skill_revisions sr
                  ON sr.skill_id=s.skill_id AND sr.revision_id=s.current_revision_id
                WHERE s.canonical_skill_id IS NOT NULL
                """
            ).fetchall()
    except sqlite3.DatabaseError as exc:
        return [{"asset_id": "*", "reason": f"governance_database_invalid:{type(exc).__name__}"}]

    bindings = {str(row["canonical_skill_id"]): row for row in rows}
    findings = []
    for revision in revisions:
        row = bindings.get(revision.asset_id)
        if row is None:
            findings.append({"asset_id": revision.asset_id, "reason": "binding_missing"})
        elif not row["current_revision_id"] or not row["revision_id"]:
            findings.append({"asset_id": revision.asset_id, "reason": "current_revision_missing"})
        elif row["status"] != "approved" or not bool(row["is_current"]):
            findings.append({"asset_id": revision.asset_id, "reason": "revision_not_approved_current"})
        elif row["artifact_digest"] != revision.content_hash:
            findings.append({"asset_id": revision.asset_id, "reason": "artifact_digest_mismatch"})
    return findings


def _migration_findings(index_db: Path, migration_dir: Path):
    migrations = load_migrations(migration_dir)
    if not index_db.exists():
        statuses = [
            {
                "migration_id": item.migration_id,
                "checksum": item.checksum,
                "state": "pending",
            }
            for item in migrations
        ]
    else:
        try:
            with _readonly(index_db) as connection:
                statuses = [
                    {
                        "migration_id": item.migration_id,
                        "checksum": item.checksum,
                        "state": item.state,
                    }
                    for item in preview_migrations(connection, migrations)
                ]
        except sqlite3.DatabaseError as exc:
            return [], [
                {"code": "migration_status_unavailable", "detail": type(exc).__name__}
            ]
    drift = [item for item in statuses if item["state"] == "checksum_drift"]
    return statuses, drift


def build_doctor_report(
    *,
    parsed_dir: Path,
    index_db: Path,
    governance_db: Path,
    migration_dir: Path | None = None,
) -> dict[str, Any]:
    migration_dir = migration_dir or ROOT / "migrations/index"
    findings: dict[str, list[Any]] = {
        "pending_projection": [],
        "stale_index_identity": [],
        "duplicate_canonical_identity": [],
        "model_version_drift": [],
        "authority_missing": [],
        "migration_status": [],
        "migration_checksum_drift": [],
        "unknown": [],
    }
    try:
        repository = LegacySkillAssetRepository(parsed_dir)
        revisions = repository.list_revisions()
    except AssetSnapshotBuildError as exc:
        findings["unknown"] = [
            {"code": item.code, "path": item.path, "detail": item.detail}
            for item in exc.diagnostics
        ]
        state = "unknown"
        return {
            "schema_version": "1.0.0",
            "state": state,
            "exit_code": EXIT_CODES[state],
            "snapshot_id": None,
            "counts": {"registry_revisions": 0, "index_rows": 0},
            "findings": findings,
        }

    findings["duplicate_canonical_identity"] = list(
        repository.ambiguous_asset_ids
    )
    index_findings, index_count = _index_findings(index_db, revisions)
    for key, values in index_findings.items():
        findings[key].extend(values)
    findings["authority_missing"] = _authority_findings(governance_db, revisions)
    (
        findings["migration_status"],
        findings["migration_checksum_drift"],
    ) = _migration_findings(index_db, migration_dir)

    if findings["unknown"] or findings["migration_checksum_drift"]:
        state = "unknown"
    elif findings["authority_missing"] or findings["duplicate_canonical_identity"]:
        state = "authority-missing"
    elif (
        findings["pending_projection"]
        or findings["stale_index_identity"]
        or findings["model_version_drift"]
    ):
        state = "stale-derived-projection"
    else:
        state = "healthy"
    return {
        "schema_version": "1.0.0",
        "state": state,
        "exit_code": EXIT_CODES[state],
        "snapshot_id": repository.snapshot_id,
        "counts": {
            "registry_revisions": len(revisions),
            "index_rows": index_count,
        },
        "findings": findings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parsed-dir", type=Path, default=Path("parsed"))
    parser.add_argument("--index-db", type=Path, default=Path("skills.db"))
    parser.add_argument(
        "--governance-db",
        type=Path,
        default=Path("governance/db/governance.db"),
    )
    parser.add_argument(
        "--migration-dir", type=Path, default=ROOT / "migrations/index"
    )
    parser.add_argument("--format", choices=("json", "text"), default="text")
    args = parser.parse_args(argv)
    report = build_doctor_report(
        parsed_dir=args.parsed_dir,
        index_db=args.index_db,
        governance_db=args.governance_db,
        migration_dir=args.migration_dir,
    )
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"State: {report['state']}")
        for key, values in report["findings"].items():
            print(f"{key}: {len(values)}")
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
