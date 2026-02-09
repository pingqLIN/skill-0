#!/usr/bin/env python3
"""
Backfill Source URLs for Converted Skills

Updates governance.db with original GitHub source URLs for all
converted skills that were imported from awesome-copilot.

Usage:
    python tools/backfill_source_urls.py [--dry-run] [-v]

Author: skill-0 project
Created: 2026-02-09
"""

import sys
import argparse
from pathlib import Path

# Add tools to path
sys.path.insert(0, str(Path(__file__).parent))

from governance_db import GovernanceDB

# awesome-copilot repo 是主要的 converted-skills 來源
AWESOME_COPILOT_BASE = "https://github.com/github/awesome-copilot/blob/main"

# 絕大部分技能是 instructions 格式，對應 instructions/ 目錄
INSTRUCTIONS_URL = f"{AWESOME_COPILOT_BASE}/instructions"

# 少數技能屬於專案內其他目錄結構，需要特殊映射
SPECIAL_MAPPINGS = {
    # awesome-copilot 的 collections 目錄
    "collections": f"{AWESOME_COPILOT_BASE}/collections",
    # awesome-copilot 的 skills 目錄
    "agents": f"{AWESOME_COPILOT_BASE}/skills/agents",
    "agent-skills": f"{AWESOME_COPILOT_BASE}/skills/agent-skills",
    "prompt": f"{AWESOME_COPILOT_BASE}/skills/prompt",
    "instructions": f"{AWESOME_COPILOT_BASE}/skills/instructions",
    # awesome-copilot 根目錄的其他項目
    "codexer": f"{AWESOME_COPILOT_BASE}/skills/codexer",
}

# 一些非 awesome-copilot 來源的技能
NON_AWESOME_COPILOT = {
    "reactjs": "https://github.com/anthropics/skills/tree/main/react-best-practices",
}


def derive_source_url(skill_name: str) -> str:
    """
    根據 skill 名稱推導原始 GitHub 來源 URL

    大多數 converted-skills 來自 awesome-copilot 的 instructions/ 目錄，
    格式為 {skill-name}.instructions.md
    """
    # 檢查特殊映射
    if skill_name in NON_AWESOME_COPILOT:
        return NON_AWESOME_COPILOT[skill_name]

    if skill_name in SPECIAL_MAPPINGS:
        return SPECIAL_MAPPINGS[skill_name]

    # 預設: awesome-copilot instructions 格式
    return f"{INSTRUCTIONS_URL}/{skill_name}.instructions.md"


def main():
    parser = argparse.ArgumentParser(
        description="Backfill source URLs for converted skills"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview changes without writing to DB"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument(
        "--db",
        type=Path,
        default=None,
        help="Path to governance.db (default: governance/db/governance.db)",
    )
    args = parser.parse_args()

    # 初始化 DB
    db = GovernanceDB(db_path=args.db) if args.db else GovernanceDB()

    # 取得所有技能
    skills = db.list_skills(limit=1000)

    print(f"\n{'=' * 60}")
    print(f"Source URL Backfill")
    print(f"{'=' * 60}")
    print(f"Total skills in DB: {len(skills)}")

    updated = 0
    skipped = 0
    already_set = 0

    for skill in skills:
        # 跳過已經指向具體文件的 URL（而非只有 repo 根目錄）
        if skill.source_url and skill.source_url.startswith("http"):
            # 如果 URL 只是 repo 根目錄，需要更新為精確連結
            is_repo_root = skill.source_url.rstrip("/") in (
                "https://github.com/github/awesome-copilot",
                "https://github.com/openai/skills",
                "https://github.com/anthropics/skills",
            )
            if not is_repo_root:
                if args.verbose:
                    print(f"  [skip] {skill.name}: already has precise URL")
                already_set += 1
                continue

        # 推導 URL
        url = derive_source_url(skill.name)

        if not url:
            if args.verbose:
                print(f"  [skip] {skill.name}: no URL mapping found")
            skipped += 1
            continue

        if args.dry_run:
            print(f"  [dry-run] {skill.name} -> {url}")
            updated += 1
        else:
            success = db.update_skill(
                skill.skill_id,
                source_url=url,
                source_type="github",
            )
            if success:
                if args.verbose:
                    print(f"  [updated] {skill.name} -> {url}")
                updated += 1
            else:
                print(f"  [error] {skill.name}: update failed")
                skipped += 1

    # 摘要
    print(f"\n{'=' * 60}")
    print(f"Results:")
    print(f"  Updated:     {updated}")
    print(f"  Already set: {already_set}")
    print(f"  Skipped:     {skipped}")
    if args.dry_run:
        print(f"\n  (Dry run — no changes written)")
    print(f"{'=' * 60}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
