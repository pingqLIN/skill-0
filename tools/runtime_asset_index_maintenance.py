#!/usr/bin/env python3
"""Audited Runtime Asset Index migration and incremental indexing CLI."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import time
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from asset_registry.sqlite import (
    INDEX_POLICY,
    IndexSchemaError,
    MigrationError,
    apply_migrations,
    backup_database,
    connect_sqlite,
    load_migrations,
    preflight_index_schema,
    preview_migrations,
    verify_database,
)
from tools.runtime_asset_drift_doctor import build_doctor_report
from vector_db.search import SemanticSearch


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _migration_rows(connection, migration_dir: Path) -> list[dict[str, str]]:
    return [
        {
            "migration_id": item.migration_id,
            "checksum": item.checksum,
            "state": item.state,
        }
        for item in preview_migrations(connection, load_migrations(migration_dir))
    ]


def inspect_index(index_db: Path, migration_dir: Path) -> dict[str, Any]:
    if not index_db.is_file():
        raise FileNotFoundError(index_db)
    with connect_sqlite(index_db, policy=INDEX_POLICY, mode="read_only") as connection:
        schema = preflight_index_schema(connection)
        migrations = _migration_rows(connection, migration_dir)
        integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
    if integrity != "ok":
        raise IndexSchemaError("index_integrity_check_failed")
    return {
        "index_db": str(index_db.resolve()),
        "bytes": index_db.stat().st_size,
        "sha256": _sha256(index_db),
        "integrity": integrity,
        "schema": schema,
        "migrations": migrations,
    }


def apply_index_migrations(
    index_db: Path,
    migration_dir: Path,
    backup_path: Path,
) -> dict[str, Any]:
    before = inspect_index(index_db, migration_dir)
    if any(item["state"] == "checksum_drift" for item in before["migrations"]):
        raise IndexSchemaError("migration_checksum_drift")
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    backup_integrity = backup_database(index_db, backup_path)
    backup_sha256 = _sha256(backup_path)
    started = time.perf_counter()
    with connect_sqlite(index_db, policy=INDEX_POLICY, mode="maintenance") as connection:
        preflight_index_schema(connection)
        applied = apply_migrations(connection, load_migrations(migration_dir))
    elapsed = time.perf_counter() - started
    after = inspect_index(index_db, migration_dir)
    if any(item["state"] != "applied" for item in after["migrations"]):
        raise IndexSchemaError("migration_postcheck_failed")
    return {
        "before": before,
        "backup": {
            "path": str(backup_path.resolve()),
            "bytes": backup_path.stat().st_size,
            "sha256": backup_sha256,
            "integrity": backup_integrity,
        },
        "applied": list(applied),
        "elapsed_seconds": elapsed,
        "after": after,
    }


@contextmanager
def _configured_model_version(version: str | None) -> Iterator[None]:
    key = "SKILL0_EMBEDDING_MODEL_VERSION"
    previous = os.environ.get(key)
    if version:
        os.environ[key] = version
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = previous


def index_twice(
    *,
    index_db: Path,
    parsed_dir: Path,
    governance_db: Path,
    migration_dir: Path,
    model_name: str | None = None,
    model_version: str | None = None,
    allow_nonhealthy_evidence: bool = False,
    smoke_query: str | None = None,
) -> dict[str, Any]:
    inspection = inspect_index(index_db, migration_dir)
    if any(item["state"] != "applied" for item in inspection["migrations"]):
        raise IndexSchemaError("asset_index_state_migration_required")
    pre_doctor = build_doctor_report(
        parsed_dir=parsed_dir,
        index_db=index_db,
        governance_db=governance_db,
        migration_dir=migration_dir,
    )
    blocking_findings = {
        key: pre_doctor["findings"][key]
        for key in (
            "duplicate_canonical_identity",
            "authority_missing",
            "migration_checksum_drift",
            "unknown",
        )
        if pre_doctor["findings"][key]
    }
    if blocking_findings and not allow_nonhealthy_evidence:
        return {
            "accepted": False,
            "rehearsal_only": False,
            "stage": "preflight",
            "inspection": inspection,
            "doctor": pre_doctor,
            "blocking_findings": blocking_findings,
        }

    started = time.perf_counter()
    with _configured_model_version(model_version):
        with SemanticSearch(
            index_db,
            model_name=model_name,
            initialize_schema=False,
        ) as search:
            first = search.index_assets(parsed_dir, show_progress=False)
            second = search.index_assets(parsed_dir, show_progress=False)
            model_id, resolved_model_version = search._embedding_identity()
            smoke_results = (
                [asdict(item) for item in search.search_assets(smoke_query, limit=5)]
                if smoke_query
                else []
            )
    elapsed = time.perf_counter() - started
    if second.changed != 0 or second.removed != 0:
        raise RuntimeError("second_incremental_index_run_was_not_noop")
    doctor = build_doctor_report(
        parsed_dir=parsed_dir,
        index_db=index_db,
        governance_db=governance_db,
        migration_dir=migration_dir,
    )
    accepted = doctor["state"] == "healthy"
    return {
        "accepted": accepted,
        "rehearsal_only": bool(allow_nonhealthy_evidence and not accepted),
        "stage": "completed",
        "inspection": inspection,
        "pre_doctor": pre_doctor,
        "index_db": str(index_db.resolve()),
        "parsed_dir": str(parsed_dir.resolve()),
        "first": vars(first),
        "second": vars(second),
        "model_identity": {
            "model_id": model_id,
            "model_version": resolved_model_version,
        },
        "search_smoke": {
            "query": smoke_query,
            "results": smoke_results,
        },
        "elapsed_seconds": elapsed,
        "doctor": doctor,
    }


def _write_output(payload: dict[str, Any], output: Path | None) -> None:
    rendered = json.dumps(payload, ensure_ascii=False, indent=2)
    print(rendered)
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index-db", type=Path, default=Path("skills.db"))
    parser.add_argument(
        "--migration-dir", type=Path, default=ROOT / "migrations/index"
    )
    parser.add_argument("--output", type=Path)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("preview", help="Read-only schema and migration preview")
    apply_parser = subparsers.add_parser(
        "apply", help="Preflight, backup, apply, and post-check migrations"
    )
    apply_parser.add_argument("--backup", type=Path, required=True)
    index_parser = subparsers.add_parser(
        "index", help="Run incremental indexing twice and emit doctor evidence"
    )
    index_parser.add_argument("--parsed-dir", type=Path, default=Path("parsed"))
    index_parser.add_argument(
        "--governance-db",
        type=Path,
        default=Path("governance/db/governance.db"),
    )
    index_parser.add_argument("--model-name")
    index_parser.add_argument("--model-version")
    index_parser.add_argument(
        "--smoke-query",
        help="Run one read-only Asset search and include projected results in evidence",
    )
    index_parser.add_argument(
        "--allow-nonhealthy-evidence",
        action="store_true",
        help=(
            "Permit a derived-index rehearsal without claiming operator acceptance; "
            "the JSON result remains accepted=false"
        ),
    )
    args = parser.parse_args(argv)
    try:
        if args.command == "preview":
            payload = {"operation": "preview", **inspect_index(args.index_db, args.migration_dir)}
        elif args.command == "apply":
            payload = {
                "operation": "apply",
                "captured_at": datetime.now(timezone.utc).isoformat(),
                **apply_index_migrations(
                    args.index_db,
                    args.migration_dir,
                    args.backup,
                ),
            }
        else:
            payload = {
                "operation": "index",
                "captured_at": datetime.now(timezone.utc).isoformat(),
                **index_twice(
                    index_db=args.index_db,
                    parsed_dir=args.parsed_dir,
                    governance_db=args.governance_db,
                    migration_dir=args.migration_dir,
                    model_name=args.model_name,
                    model_version=args.model_version,
                    allow_nonhealthy_evidence=args.allow_nonhealthy_evidence,
                    smoke_query=args.smoke_query,
                ),
            }
        _write_output(payload, args.output)
        if args.command == "index" and not payload["accepted"]:
            if args.allow_nonhealthy_evidence:
                return 0
            return int(payload["doctor"]["exit_code"] or 2)
        return 0
    except (
        FileNotFoundError,
        IndexSchemaError,
        MigrationError,
        RuntimeError,
        sqlite3.DatabaseError,
        OSError,
    ) as exc:
        print(
            json.dumps(
                {
                    "operation": args.command,
                    "error": type(exc).__name__,
                    "detail": str(exc),
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
