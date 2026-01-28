#!/usr/bin/env python3
"""
Backfill governance metadata for converted skills.

Fills provenance + conversion fields based on local awesome-copilot repo and
converted-skills directory. Intended to make governance DB compliant.

Usage:
    python backfill_governance.py [--db PATH] [--dry-run] [--no-backup]
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from governance_db import GovernanceDB


DEFAULT_DB = Path(__file__).parent.parent / "governance" / "db" / "governance.db"
SOURCE_ROOT = Path(r"C:\Dev\skills\awesome-copilot")
INSTRUCTIONS_DIR = SOURCE_ROOT / "instructions"
CONVERTED_DIR = Path(__file__).parent.parent / "converted-skills"

AUTHOR_NAME = "GitHub, Inc."
AUTHOR_ORG = "GitHub"
LICENSE_SPDX = "MIT"
CONVERTER_VERSION = "skill-0 skill_converter (2026-01-27)"
TARGET_FORMAT = "SKILL.md"


def _git(*args: str, cwd: Path) -> str:
    return (
        subprocess.check_output(["git", "-C", str(cwd), *args], text=True).strip()
    )


def _normalize_repo_url(url: str) -> str:
    url = url.strip()
    if url.startswith("git@"):
        # git@github.com:org/repo.git -> https://github.com/org/repo
        _, rest = url.split("@", 1)
        host, path = rest.split(":", 1)
        url = f"https://{host}/{path}"
    if url.endswith(".git"):
        url = url[:-4]
    return url


def _iso_from_mtime(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime).isoformat()


def _backup_db(db_path: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = db_path.with_suffix(db_path.suffix + f".pre-backfill.{ts}.bak")
    shutil.copy2(db_path, backup)
    return backup


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-backup", action="store_true")
    args = ap.parse_args()

    if not INSTRUCTIONS_DIR.exists():
        raise SystemExit(f"Instructions dir not found: {INSTRUCTIONS_DIR}")
    if not CONVERTED_DIR.exists():
        raise SystemExit(f"Converted dir not found: {CONVERTED_DIR}")
    if not args.db.exists():
        raise SystemExit(f"Governance DB not found: {args.db}")

    repo_url = _normalize_repo_url(
        _git("config", "--get", "remote.origin.url", cwd=SOURCE_ROOT)
    )
    commit = _git("rev-parse", "HEAD", cwd=SOURCE_ROOT)
    license_url = f"{repo_url}/blob/{commit}/LICENSE"

    if not args.no_backup and not args.dry_run:
        backup = _backup_db(args.db)
        print(f"✅ DB backup created: {backup}")

    db = GovernanceDB(db_path=args.db)
    skills = db.list_skills(limit=10000)

    updated = 0
    skipped = 0
    missing = 0

    for skill in skills:
        name = skill.name
        original_path = INSTRUCTIONS_DIR / f"{name}.instructions.md"
        converted_path = CONVERTED_DIR / name / "SKILL.md"

        if not original_path.exists():
            print(f"⚠️  Missing original: {name} -> {original_path}")
            missing += 1
            continue

        updates = {
            "source_type": "github",
            "source_url": repo_url,
            "source_commit": commit,
            "source_path": str(original_path),
            "original_format": "instructions.md",
            "fetched_at": _iso_from_mtime(original_path),
            "author_name": AUTHOR_NAME,
            "author_org": AUTHOR_ORG,
            "license_spdx": LICENSE_SPDX,
            "license_url": license_url,
            "converter_version": CONVERTER_VERSION,
            "target_format": TARGET_FORMAT,
        }

        if converted_path.exists():
            updates["converted_at"] = _iso_from_mtime(converted_path)
        else:
            print(f"⚠️  Missing converted: {name} -> {converted_path}")

        if args.dry_run:
            updated += 1
            continue

        if db.update_skill(skill.skill_id, **updates):
            updated += 1
        else:
            skipped += 1

    print(
        f"\n✅ Backfill complete: updated={updated}, skipped={skipped}, missing_original={missing}"
    )
    print(f"Source: {repo_url} @ {commit}")
    print(f"License URL: {license_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
