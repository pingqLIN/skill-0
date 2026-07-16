"""Render deterministic Runtime v4 Evidence from the append-only ledger."""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.evidence import build_evidence_summary, build_run_evidence
from runtime.ledger import RuntimeLedger
from runtime.validators import RuntimeContractValidationError, load_json, validate_schema


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render derived Runtime v4 Evidence")
    parser.add_argument("--db", type=Path, required=True, help="Runtime SQLite ledger")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--run-id")
    target.add_argument("--skill-name")
    parser.add_argument("--skill-version")
    parser.add_argument("--minimum-sample-size", type=int, default=10)
    parser.add_argument("--output", type=Path, help="Optional JSON output path")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.skill_name and not args.skill_version:
        parser.error("--skill-version is required with --skill-name")
    if not args.db.exists():
        print("Runtime ledger not found", file=sys.stderr)
        return 2

    try:
        with RuntimeLedger(args.db, read_only=True) as ledger:
            if args.run_id:
                try:
                    run = ledger.get_run(args.run_id)
                except KeyError:
                    print("Run not found", file=sys.stderr)
                    return 2
                summary = build_run_evidence(ledger.list_events(args.run_id), run=run)
            else:
                events = ledger.list_events_for_skill(args.skill_name, args.skill_version)
                if not events:
                    print("Skill Evidence source events not found", file=sys.stderr)
                    return 2
                summary = build_evidence_summary(
                    events,
                    skill_name=args.skill_name,
                    skill_version=args.skill_version,
                    minimum_confident_sample=max(1, args.minimum_sample_size),
                )

        validate_schema(
            summary,
            load_json(ROOT / "schema" / "evidence-summary.schema.json"),
        )
        if args.run_id:
            validate_schema(
                summary,
                load_json(ROOT / "schema" / "runtime-run-evidence.schema.json"),
            )
        rendered = json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True)
        if args.output:
            temp_path: Path | None = None
            try:
                with tempfile.NamedTemporaryFile(
                    "w",
                    encoding="utf-8",
                    delete=False,
                    dir=args.output.parent,
                    prefix=f"{args.output.name}.",
                    suffix=".tmp",
                ) as handle:
                    handle.write(rendered + "\n")
                    temp_path = Path(handle.name)
                os.replace(temp_path, args.output)
            finally:
                if temp_path is not None and temp_path.exists():
                    temp_path.unlink()
        else:
            print(rendered)
        return 0
    except (OSError, sqlite3.DatabaseError, RuntimeContractValidationError, ValueError):
        print("Unable to render Runtime Evidence", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
