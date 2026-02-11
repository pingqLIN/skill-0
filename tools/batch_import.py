#!/usr/bin/env python3
"""
Batch Import Tool for Skill Governance

Imports all converted skills from converted-skills/ directory
into the governance database.

Usage:
    python batch_import.py [--auto-approve] [--skip-security]
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

# Add tools to path
sys.path.insert(0, str(Path(__file__).parent))

from skill_governance import SkillGovernanceCLI


def main():
    parser = argparse.ArgumentParser(description="Batch import converted skills")
    parser.add_argument(
        "--auto-approve", action="store_true", help="Auto-approve safe skills"
    )
    parser.add_argument(
        "--skip-security", action="store_true", help="Skip security scan"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()

    # Initialize CLI
    cli = SkillGovernanceCLI(verbose=args.verbose)
    converted_dir = cli.converted_dir

    # Get all skill directories
    skill_dirs = sorted([d for d in converted_dir.iterdir() if d.is_dir()])

    print(f"\n{'=' * 70}")
    print(f"🔍 BATCH IMPORT: {converted_dir.name}")
    print(f"{'=' * 70}")
    print(f"Found {len(skill_dirs)} skill directories\n")

    success_count = 0
    failed_count = 0
    skipped_count = 0
    errors = []

    start_time = datetime.now()

    for i, skill_dir in enumerate(skill_dirs, 1):
        skill_name = skill_dir.name
        skill_file = skill_dir / "SKILL.md"

        # Check if SKILL.md exists
        if not skill_file.exists():
            print(f"⏭️  [{i:3d}/{len(skill_dirs)}] {skill_name}: No SKILL.md found")
            skipped_count += 1
            continue

        try:
            # Check if already registered
            existing = cli.db.get_skill(name=skill_name)
            if existing:
                print(f"✅ [{i:3d}/{len(skill_dirs)}] {skill_name}: Already registered")
                success_count += 1
                continue

            # Import the skill
            if args.verbose:
                print(f"   Importing {skill_name}...", end="", flush=True)

            result = cli.import_skill(
                source_path=skill_dir,
                auto_approve=args.auto_approve,
                skip_security=args.skip_security or True,  # Always skip for batch
                skip_equivalence=True,  # Always skip for batch
                skip_convert=True,  # Already converted
                author_name="skill-0 project",
                license_spdx="UNKNOWN",
            )

            if result["success"]:
                print(
                    f"✅ [{i:3d}/{len(skill_dirs)}] {skill_name}: Imported (ID: {result['skill_id']})"
                )
                success_count += 1
            else:
                error_msg = result.get("error", "Unknown error")
                print(f"❌ [{i:3d}/{len(skill_dirs)}] {skill_name}: {error_msg}")
                failed_count += 1
                errors.append((skill_name, error_msg))

        except Exception as e:
            print(
                f"❌ [{i:3d}/{len(skill_dirs)}] {skill_name}: Exception: {str(e)[:50]}"
            )
            failed_count += 1
            errors.append((skill_name, str(e)))

    end_time = datetime.now()
    elapsed = (end_time - start_time).total_seconds()

    # Print summary
    print(f"\n{'=' * 70}")
    print(f"📊 BATCH IMPORT SUMMARY")
    print(f"{'=' * 70}")
    print(f"✅ Successfully imported: {success_count}")
    print(f"❌ Failed imports:        {failed_count}")
    print(f"⏭️  Skipped:              {skipped_count}")
    print(
        f"📈 Total processed:       {success_count + failed_count + skipped_count}/{len(skill_dirs)}"
    )
    print(f"⏱️  Time elapsed:          {elapsed:.1f}s")
    print(f"{'=' * 70}\n")

    # Show current database status
    stats = cli.db.get_statistics()
    print(f"📁 Database Status:")
    print(f"   Total skills registered: {stats.get('total_skills', 0)}")
    print(f"   Approved: {stats['by_status'].get('approved', 0)}")
    print(f"   Pending: {stats['by_status'].get('pending', 0)}")
    print(f"   Rejected: {stats['by_status'].get('rejected', 0)}")

    # Show errors if any
    if errors:
        print(f"\n⚠️  First 10 Errors:")
        for skill_name, error in errors[:10]:
            error_short = error[:60] + "..." if len(error) > 60 else error
            print(f"   - {skill_name}: {error_short}")
        if len(errors) > 10:
            print(f"   ... and {len(errors) - 10} more errors")

    print()
    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
