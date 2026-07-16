#!/usr/bin/env python3
"""Fail-closed production checks for the Runtime v4 operational boundary."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.routers.runs_v4 import (  # noqa: E402
    DEFAULT_RUNTIME_HITL_TTL_SECONDS,
    runtime_binding_key_configuration_issue,
    runtime_hitl_ttl_configuration_issue,
    runtime_journal_mode_configuration_issue,
)


RUNTIME_TABLES = {
    "runtime_runs": set(),
    "runtime_events": set(),
    "runtime_execution_bases": {"governance_revision_id"},
    "runtime_hitl_items": {"expires_at"},
    "runtime_hitl_decisions": set(),
    "runtime_resume_claims": set(),
}
GOVERNANCE_TABLES = {
    "skills": {"canonical_skill_id", "current_revision_id"},
    "skill_revisions": {"artifact_digest", "is_current", "status"},
}


def _read_only_connection(path: Path) -> sqlite3.Connection:
    uri = f"{path.resolve().as_uri()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True, timeout=10.0)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only=ON")
    return connection


def _check_sqlite(
    label: str,
    path: Path,
    required_tables: dict[str, set[str]],
    *,
    expected_journal_mode: str | None = None,
) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    details: dict[str, Any] = {"path": str(path), "exists": path.is_file()}
    if not path.is_file():
        return [f"{label}_missing:{path}"], details
    try:
        with _read_only_connection(path) as connection:
            quick_check = connection.execute("PRAGMA quick_check").fetchone()[0]
            details["quick_check"] = quick_check
            if quick_check != "ok":
                errors.append(f"{label}_quick_check_failed")
            journal_mode = connection.execute("PRAGMA journal_mode").fetchone()[0]
            details["journal_mode"] = journal_mode
            if expected_journal_mode and journal_mode.lower() != expected_journal_mode.lower():
                errors.append(
                    f"{label}_journal_mode:{journal_mode}:expected:{expected_journal_mode}"
                )
            tables = {
                row["name"]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            for table, required_columns in required_tables.items():
                if table not in tables:
                    errors.append(f"{label}_table_missing:{table}")
                    continue
                columns = {
                    row["name"]
                    for row in connection.execute(f"PRAGMA table_info({table})")
                }
                for column in sorted(required_columns - columns):
                    errors.append(f"{label}_column_missing:{table}.{column}")
    except sqlite3.Error as exc:
        errors.append(f"{label}_unreadable:{type(exc).__name__}")
    return errors, details


def _check_backups(
    backup_dir: Path,
    *,
    max_age_days: int,
) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    details: dict[str, Any] = {"path": str(backup_dir), "latest": {}}
    now = datetime.now(timezone.utc).timestamp()
    for prefix in ("skills", "governance", "runtime"):
        matches = sorted(
            backup_dir.glob(f"{prefix}_*.db"),
            key=lambda candidate: candidate.stat().st_mtime,
            reverse=True,
        )
        if not matches:
            errors.append(f"backup_missing:{prefix}")
            continue
        latest = matches[0]
        age_days = int((now - latest.stat().st_mtime) // 86_400)
        details["latest"][prefix] = {
            "path": str(latest),
            "age_days": age_days,
        }
        integrity_errors, integrity = _check_sqlite(
            f"{prefix}_backup",
            latest,
            {},
        )
        errors.extend(integrity_errors)
        details["latest"][prefix]["quick_check"] = integrity.get("quick_check")
        if age_days > max_age_days:
            errors.append(f"backup_stale:{prefix}:{age_days}d")
    return errors, details


def run_doctor(
    *,
    production: bool,
    require_backups: bool,
    backup_dir: Path,
    max_backup_age_days: int,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    checks: dict[str, Any] = {}

    env_name = os.getenv("SKILL0_ENV", "development").strip().lower()
    if production and env_name not in {"production", "prod"}:
        errors.append("SKILL0_ENV_must_be_production")

    if production:
        binding_issue = runtime_binding_key_configuration_issue(
            os.getenv("SKILL0_RUNTIME_BINDING_KEY"),
            jwt_secret_key=os.getenv("JWT_SECRET_KEY"),
        )
        if binding_issue:
            errors.append(binding_issue)
        actors = {
            value.strip()
            for value in os.getenv("SKILL0_RUNTIME_DECISION_ACTORS", "").split(",")
            if value.strip()
        }
        if not actors or any(
            actor.lower().startswith(("change_me", "change-me"))
            for actor in actors
        ):
            errors.append(
                "SKILL0_RUNTIME_DECISION_ACTORS must name explicit approver subjects"
            )
        ttl_issue = runtime_hitl_ttl_configuration_issue(
            os.getenv(
                "SKILL0_RUNTIME_HITL_TTL_SECONDS",
                str(DEFAULT_RUNTIME_HITL_TTL_SECONDS),
            )
        )
        if ttl_issue:
            errors.append(ttl_issue)
        if os.getenv("SKILL0_RUNTIME_ALLOW_INITIALIZE", "false").lower() == "true":
            issue = "runtime_initialization_is_enabled"
            if require_backups:
                errors.append(issue)
            else:
                warnings.append(issue)

    runtime_path = Path(
        os.getenv("SKILL0_RUNTIME_DB_PATH", "governance/db/runtime.db")
    )
    governance_path = Path(
        os.getenv("SKILL0_GOVERNANCE_DB_PATH", "governance/db/governance.db")
    )
    skills_path = Path(os.getenv("SKILL0_DB_PATH", "skills.db"))
    parsed_dir = Path(os.getenv("SKILL0_PARSED_DIR", "parsed"))
    expected_runtime_journal = os.getenv(
        "SKILL0_RUNTIME_JOURNAL_MODE", "DELETE"
    ).upper()
    journal_issue = runtime_journal_mode_configuration_issue(
        expected_runtime_journal,
        require_wal=production,
    )
    if journal_issue:
        errors.append(journal_issue)
        expected_runtime_journal = None

    for label, path, tables, journal in (
        ("skills_db", skills_path, {}, None),
        ("governance_db", governance_path, GOVERNANCE_TABLES, None),
        ("runtime_db", runtime_path, RUNTIME_TABLES, expected_runtime_journal),
    ):
        db_errors, details = _check_sqlite(
            label,
            path,
            tables,
            expected_journal_mode=journal,
        )
        errors.extend(db_errors)
        checks[label] = details

    parsed_count = len(list(parsed_dir.glob("*.json"))) if parsed_dir.is_dir() else 0
    checks["parsed"] = {"path": str(parsed_dir), "json_count": parsed_count}
    if parsed_count == 0:
        errors.append(f"parsed_artifacts_missing:{parsed_dir}")

    if runtime_path.is_file():
        try:
            with _read_only_connection(runtime_path) as connection:
                legacy_hitl = connection.execute(
                    "SELECT COUNT(*) FROM runtime_hitl_items WHERE expires_at IS NULL"
                ).fetchone()[0]
                legacy_basis = connection.execute(
                    "SELECT COUNT(*) FROM runtime_execution_bases "
                    "WHERE governance_revision_id IS NULL"
                ).fetchone()[0]
            if legacy_hitl:
                warnings.append(f"legacy_hitl_items_expired:{legacy_hitl}")
            if legacy_basis:
                warnings.append(f"legacy_execution_bases_non_resumable:{legacy_basis}")
        except sqlite3.Error:
            pass

    if require_backups:
        backup_errors, backup_details = _check_backups(
            backup_dir,
            max_age_days=max_backup_age_days,
        )
        errors.extend(backup_errors)
        checks["backups"] = backup_details

    return {
        "status": "healthy" if not errors else "failed",
        "errors": errors,
        "warnings": warnings,
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate Runtime v4 production storage and security posture"
    )
    parser.add_argument("--production", action="store_true")
    parser.add_argument("--require-backups", action="store_true")
    parser.add_argument("--backup-dir", type=Path, default=Path("backups"))
    parser.add_argument("--max-backup-age-days", type=int, default=2)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.max_backup_age_days < 0:
        parser.error("--max-backup-age-days must be non-negative")
    report = run_doctor(
        production=args.production,
        require_backups=args.require_backups,
        backup_dir=args.backup_dir,
        max_backup_age_days=args.max_backup_age_days,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"Runtime doctor: {report['status']}")
        for issue in report["errors"]:
            print(f"[FAIL] {issue}")
        for warning in report["warnings"]:
            print(f"[WARN] {warning}")
    return 0 if report["status"] == "healthy" else 1


if __name__ == "__main__":
    raise SystemExit(main())
