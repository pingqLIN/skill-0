#!/usr/bin/env python3
"""
Backfill Empty Fields in governance.db

Fills 3 remaining empty columns:
  1. author_email — derived from author_org (GitHub → opensource@github.com)
  2. installed_path — derived from skill name → converted-skills/{name}/SKILL.md
  3. installed_at — derived from SKILL.md file mtime

Usage:
    python tools/backfill_empty_fields.py --dry-run   # preview
    python tools/backfill_empty_fields.py              # execute

Author: skill-0 project
Created: 2026-02-09
"""

import sys
import os
import argparse
from pathlib import Path
from datetime import datetime

# tools/ 路徑
sys.path.insert(0, str(Path(__file__).parent))

from governance_db import GovernanceDB

# author_org → email 映射
ORG_EMAIL_MAP = {
    "GitHub": "opensource@github.com",
    "Anthropic": "support@anthropic.com",
    "OpenAI": "support@openai.com",
}

# author_org → URL 映射
ORG_URL_MAP = {
    "GitHub": "https://github.com/github",
    "Anthropic": "https://github.com/anthropics",
    "OpenAI": "https://github.com/openai",
}

CONVERTED_SKILLS_DIR = Path(__file__).parent.parent / "converted-skills"


def derive_author_email(skill) -> str | None:
    """根據 author_org 推導 author_email"""
    org = skill.author_org or ""
    return ORG_EMAIL_MAP.get(org)


def derive_installed_path(skill) -> str | None:
    """根據 skill name 推導 installed_path"""
    skill_dir = CONVERTED_SKILLS_DIR / skill.name / "SKILL.md"
    if skill_dir.exists():
        return f"converted-skills/{skill.name}/SKILL.md"
    return None


def derive_author_url(skill) -> str | None:
    """根據 author_org 推導 author_url"""
    org = skill.author_org or ""
    return ORG_URL_MAP.get(org)


def derive_installed_at(skill) -> str | None:
    """根據 SKILL.md 的 mtime 推導 installed_at"""
    skill_file = CONVERTED_SKILLS_DIR / skill.name / "SKILL.md"
    if skill_file.exists():
        mtime = skill_file.stat().st_mtime
        return datetime.fromtimestamp(mtime).isoformat()
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Backfill empty fields in governance.db"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview changes without writing"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument(
        "--db", type=Path, default=None, help="Path to governance.db"
    )
    args = parser.parse_args()

    db = GovernanceDB(db_path=args.db) if args.db else GovernanceDB()
    skills = db.list_skills(limit=1000)

    print(f"\n{'=' * 60}")
    print(f"Empty Fields Backfill")
    print(f"{'=' * 60}")
    print(f"Total skills: {len(skills)}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print()

    stats = {
        "author_email": {"updated": 0, "skipped": 0},
        "author_url": {"updated": 0, "skipped": 0},
        "installed_path": {"updated": 0, "skipped": 0},
        "installed_at": {"updated": 0, "skipped": 0},
    }

    for skill in skills:
        updates = {}

        # 1. author_email
        if not skill.author_email:
            email = derive_author_email(skill)
            if email:
                updates["author_email"] = email
                stats["author_email"]["updated"] += 1
            else:
                stats["author_email"]["skipped"] += 1
        else:
            stats["author_email"]["skipped"] += 1

        # 2. author_url
        if not skill.author_url:
            url = derive_author_url(skill)
            if url:
                updates["author_url"] = url
                stats["author_url"]["updated"] += 1
            else:
                stats["author_url"]["skipped"] += 1
        else:
            stats["author_url"]["skipped"] += 1

        # 3. installed_path
        if not skill.installed_path:
            path = derive_installed_path(skill)
            if path:
                updates["installed_path"] = path
                stats["installed_path"]["updated"] += 1
            else:
                stats["installed_path"]["skipped"] += 1
        else:
            stats["installed_path"]["skipped"] += 1

        # 3. installed_at
        if not skill.installed_at:
            at = derive_installed_at(skill)
            if at:
                updates["installed_at"] = at
                stats["installed_at"]["updated"] += 1
            else:
                stats["installed_at"]["skipped"] += 1
        else:
            stats["installed_at"]["skipped"] += 1

        if not updates:
            continue

        if args.dry_run:
            if args.verbose:
                print(f"  [dry-run] {skill.name}:")
                for k, v in updates.items():
                    val = v if len(str(v)) < 60 else str(v)[:57] + "..."
                    print(f"    {k} = {val}")
        else:
            success = db.update_skill(skill.skill_id, **updates)
            if args.verbose and success:
                print(f"  [updated] {skill.name}: {list(updates.keys())}")
            elif not success:
                print(f"  [error] {skill.name}: update failed")

    # 結果報告
    print(f"\n{'=' * 60}")
    print(f"Results:")
    print(f"{'Field':<20} {'Updated':<10} {'Skipped':<10}")
    print(f"{'-' * 40}")
    for field, counts in stats.items():
        print(f"{field:<20} {counts['updated']:<10} {counts['skipped']:<10}")
    if args.dry_run:
        print(f"\n  (Dry run — no changes written)")
    print(f"{'=' * 60}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
