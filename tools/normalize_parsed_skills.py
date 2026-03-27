#!/usr/bin/env python3
"""
Normalize legacy parsed skills to the canonical v2.4 schema contract.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.schema_contract import (
    DEFAULT_SCHEMA_PATH,
    iter_validation_errors,
    normalize_skill_document,
)


def iter_skill_files(parsed_dir: Path) -> list[Path]:
    return sorted(parsed_dir.glob("*.json"))


def normalize_file(path: Path, schema_path: Path, write: bool) -> tuple[bool, int]:
    original = json.loads(path.read_text(encoding="utf-8"))
    normalized = normalize_skill_document(original)
    changed = normalized != original

    if changed and write:
        path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    error_count = len(iter_validation_errors(normalized, schema_path))
    return changed, error_count


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize parsed skills toward the canonical v2.4 schema")
    parser.add_argument("--parsed-dir", type=Path, default=Path("parsed"), help="Directory containing parsed skill JSON")
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA_PATH, help="Schema path")
    parser.add_argument("--write", action="store_true", help="Write normalized output back to disk")
    args = parser.parse_args()

    files = iter_skill_files(args.parsed_dir)
    if not files:
        print(f"No parsed files found in {args.parsed_dir}")
        return 1

    changed_count = 0
    invalid_count = 0

    for path in files:
        changed, error_count = normalize_file(path, args.schema, args.write)
        changed_count += int(changed)
        invalid_count += int(error_count > 0)
        status = "CHANGED" if changed else "UNCHANGED"
        validation = "OK" if error_count == 0 else f"{error_count} error(s)"
        print(f"{status} {path} [{validation}]")

    print(
        f"\nProcessed {len(files)} file(s): "
        f"{changed_count} changed, {len(files) - changed_count} unchanged, {invalid_count} invalid after normalization"
    )
    return 0 if invalid_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
