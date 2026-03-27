#!/usr/bin/env python3
"""
Validate parsed skills against the canonical JSON schema contract.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.schema_contract import DEFAULT_SCHEMA_PATH, iter_validation_errors


def iter_skill_files(paths: list[Path]) -> list[Path]:
    """Expand files/directories into a stable list of JSON files."""
    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            files.extend(sorted(path.glob("*.json")))
        elif path.is_file():
            files.append(path)
    return sorted(dict.fromkeys(files))


def validate_file(path: Path, schema_path: Path, max_errors: int) -> list[str]:
    """Return schema validation errors for a single file."""
    try:
        skill = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"<json>: Invalid JSON: {exc}"]

    errors = []
    for error in iter_validation_errors(skill, schema_path):
        location = ".".join(str(part) for part in error.absolute_path) or "<root>"
        errors.append(f"{location}: {error.message}")
        if len(errors) >= max_errors:
            break
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate skill JSON files against the canonical schema")
    parser.add_argument(
        "paths",
        nargs="*",
        default=["parsed"],
        help="Files or directories to validate (default: parsed)",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=DEFAULT_SCHEMA_PATH,
        help="Path to schema JSON",
    )
    parser.add_argument(
        "--max-errors-per-file",
        type=int,
        default=20,
        help="Maximum validation errors to print per file",
    )
    args = parser.parse_args()

    files = iter_skill_files([Path(path) for path in args.paths])
    if not files:
        print("No JSON files found to validate.")
        return 1

    invalid = 0
    for path in files:
        errors = validate_file(path, args.schema, args.max_errors_per_file)
        if errors:
            invalid += 1
            print(f"FAIL {path}")
            for message in errors:
                print(f"  - {message}")

    valid = len(files) - invalid
    print(f"\nValidated {len(files)} file(s): {valid} passed, {invalid} failed")
    return 0 if invalid == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
