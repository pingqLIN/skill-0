from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.validators import load_json, validate_cross_references, validate_schema


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a SKILL-0 v4 runtime contract")
    parser.add_argument("contract", type=Path)
    parser.add_argument("--schema", type=Path, default=Path("schema/skill-runtime-contract.schema.json"))
    parser.add_argument("--skill", type=Path, help="Optional parsed skill document for ARD cross-reference validation")
    args = parser.parse_args()

    contract = load_json(args.contract)
    schema = load_json(args.schema)
    validate_schema(contract, schema)
    if args.skill:
        validate_cross_references(load_json(args.skill), contract)
    print(f"VALID: {args.contract}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        raise SystemExit(1)
