#!/usr/bin/env python3
"""
Add triggers/globs frontmatter fields to converted SKILL.md files.

Uses applyTo from original .instructions.md when available.
Falls back to parsing "Triggers on:" from description, else "**/*".
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


SOURCE_INSTRUCTIONS = Path(r"C:\Dev\skills\awesome-copilot\instructions")
CONVERTED_DIR = Path(__file__).parent.parent / "converted-skills"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _extract_frontmatter(content: str) -> tuple[str, str, str]:
    if not content.startswith("---"):
        return "", content, ""
    end = content.find("---", 3)
    if end == -1:
        return "", content, ""
    front = content[3:end]
    body = content[end + 3 :]
    return front, body, content[: end + 3]


def _parse_apply_to_from_instructions(path: Path) -> str | None:
    if not path.exists():
        return None
    content = _read_text(path)
    if not content.startswith("---"):
        return None
    end = content.find("---", 3)
    if end == -1:
        return None
    front = content[3:end]
    for line in front.splitlines():
        if line.strip().startswith("applyTo:"):
            value = line.split(":", 1)[1].strip().strip("'\"")
            return value or None
    return None


def _parse_apply_to_from_description(front: str) -> str | None:
    for line in front.splitlines():
        if line.strip().startswith("description:"):
            desc = line.split(":", 1)[1].strip().strip("'\"")
            m = re.search(r"Triggers on:\s*(.+)$", desc)
            if m:
                return m.group(1).strip().strip("'\"")
    return None


def _quote(value: str) -> str:
    escaped = value.replace('"', '\\"')
    return f"\"{escaped}\""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not CONVERTED_DIR.exists():
        raise SystemExit(f"Converted dir not found: {CONVERTED_DIR}")

    updated = 0
    skipped = 0
    missing = 0

    for skill_dir in sorted([p for p in CONVERTED_DIR.iterdir() if p.is_dir()]):
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            missing += 1
            continue

        content = _read_text(skill_md)
        front, body, _ = _extract_frontmatter(content)
        if not front:
            skipped += 1
            continue

        has_triggers = any(
            line.strip().startswith("triggers:") for line in front.splitlines()
        )
        has_globs = any(
            line.strip().startswith("globs:") for line in front.splitlines()
        )

        if has_triggers and has_globs:
            skipped += 1
            continue

        name = skill_dir.name
        apply_to = _parse_apply_to_from_instructions(
            SOURCE_INSTRUCTIONS / f"{name}.instructions.md"
        )
        if not apply_to:
            apply_to = _parse_apply_to_from_description(front)
        if not apply_to:
            apply_to = "**/*"

        new_lines = front.splitlines()
        if not has_triggers:
            new_lines.append(f"triggers: {_quote(apply_to)}")
        if not has_globs:
            new_lines.append(f"globs: {_quote(apply_to)}")

        new_front = "\n".join(new_lines)
        new_content = f"---\n{new_front}\n---{body}"

        if not args.dry_run:
            skill_md.write_text(new_content, encoding="utf-8")

        updated += 1

    print(f"✅ triggers/globs update: updated={updated}, skipped={skipped}, missing={missing}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
