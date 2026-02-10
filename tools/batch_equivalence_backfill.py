<<<<<<< Updated upstream
#!/usr/bin/env python3
"""
Batch equivalence testing and DB backfill.

Runs skill_tester on all skills missing equivalence results and records them
into the governance database.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from governance_db import GovernanceDB
from skill_tester import SkillEquivalenceTester


DEFAULT_DB = Path(__file__).parent.parent / "governance" / "db" / "governance.db"
INSTRUCTIONS_DIR = Path(r"C:\Dev\skills\awesome-copilot\instructions")
CONVERTED_DIR = Path(__file__).parent.parent / "converted-skills"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument(
        "--skip-existing",
        action="store_true",
        default=False,
        help="Skip skills that already have equivalence scores.",
    )
    args = ap.parse_args()

    if not INSTRUCTIONS_DIR.exists():
        raise SystemExit(f"Instructions dir not found: {INSTRUCTIONS_DIR}")
    if not CONVERTED_DIR.exists():
        raise SystemExit(f"Converted dir not found: {CONVERTED_DIR}")
    if not args.db.exists():
        raise SystemExit(f"Governance DB not found: {args.db}")

    db = GovernanceDB(db_path=args.db)
    tester = SkillEquivalenceTester(verbose=args.verbose)

    skills = db.list_skills(limit=10000)
    processed = 0
    skipped = 0
    errors = 0

    for skill in skills:
        if args.limit and processed >= args.limit:
            break

        if args.skip_existing and skill.equivalence_score is not None:
            skipped += 1
            continue

        name = skill.name
        original_path = INSTRUCTIONS_DIR / f"{name}.instructions.md"
        converted_path = CONVERTED_DIR / name

        if not original_path.exists() or not converted_path.exists():
            print(f"⚠️  Missing paths for {name}")
            errors += 1
            continue

        try:
            result = tester.test_equivalence(original_path, converted_path)
            if not args.dry_run:
                db.record_equivalence_test(skill.skill_id, result.to_dict())
            processed += 1
            status = "PASSED" if result.passed else "FAILED"
            print(f"✅ {name}: {status} ({result.overall_score:.1%})")
        except Exception as exc:
            print(f"❌ {name}: {exc}")
            errors += 1

    print(
        f"\n📊 Equivalence backfill: processed={processed}, skipped={skipped}, errors={errors}"
    )
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
=======
#!/usr/bin/env python3
"""
Batch equivalence testing and DB backfill.

Runs skill_tester on all skills missing equivalence results and records them
into the governance database.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from governance_db import GovernanceDB
from skill_tester import SkillEquivalenceTester


DEFAULT_DB = Path(__file__).parent.parent / "governance" / "db" / "governance.db"
INSTRUCTIONS_DIR = Path(r"C:\Dev\skills\awesome-copilot\instructions")
CONVERTED_DIR = Path(__file__).parent.parent / "converted-skills"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument(
        "--skip-existing",
        action="store_true",
        default=False,
        help="Skip skills that already have equivalence scores.",
    )
    args = ap.parse_args()

    if not INSTRUCTIONS_DIR.exists():
        raise SystemExit(f"Instructions dir not found: {INSTRUCTIONS_DIR}")
    if not CONVERTED_DIR.exists():
        raise SystemExit(f"Converted dir not found: {CONVERTED_DIR}")
    if not args.db.exists():
        raise SystemExit(f"Governance DB not found: {args.db}")

    db = GovernanceDB(db_path=args.db)
    tester = SkillEquivalenceTester(verbose=args.verbose)

    skills = db.list_skills(limit=10000)
    processed = 0
    skipped = 0
    errors = 0

    for skill in skills:
        if args.limit and processed >= args.limit:
            break

        if args.skip_existing and skill.equivalence_score is not None:
            skipped += 1
            continue

        name = skill.name
        original_path = INSTRUCTIONS_DIR / f"{name}.instructions.md"
        converted_path = CONVERTED_DIR / name

        if not original_path.exists() or not converted_path.exists():
            print(f"⚠️  Missing paths for {name}")
            errors += 1
            continue

        try:
            result = tester.test_equivalence(original_path, converted_path)
            if not args.dry_run:
                db.record_equivalence_test(skill.skill_id, result.to_dict())
            processed += 1
            status = "PASSED" if result.passed else "FAILED"
            print(f"✅ {name}: {status} ({result.overall_score:.1%})")
        except Exception as exc:
            print(f"❌ {name}: {exc}")
            errors += 1

    print(
        f"\n📊 Equivalence backfill: processed={processed}, skipped={skipped}, errors={errors}"
    )
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
>>>>>>> Stashed changes
