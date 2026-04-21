"""Check that live and archival planning documents carry the expected markers.

This keeps current execution entrypoints and historical planning documents from
drifting back into ambiguity during future edits.
"""

from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parent.parent

ARCHIVAL_DOCS = {
    "reference.md": "historical schema reference note",
    "docs/final-development-phase-plan-2026-03-23.md": "historical final-phase plan note",
    "docs/implementation-summary.md": "historical implementation-summary note",
    "docs/planning/current-execution-plan-2026-03-19.md": "historical execution-plan note",
    "docs/planning/plan.md": "historical planning note",
    "docs/planning/plan-20-skills.md": "historical expansion note",
    "docs/planning/yolo-dev-plan.md": "historical YOLO note",
    "docs/project-progress-report-2026-03-23.md": "historical project-progress note",
}

AUTHORITY_INDEX = "docs/document-authority-index-2026-03-27.md"
CURRENT_EXECUTION_PLAN = "docs/planning/executable-dev-plan-2026-03-31.zh-TW.md"
STATUS_MARKER = "Status note:"


def _read_text(path_str: str) -> str:
    return (REPO_ROOT / path_str).read_text(encoding="utf-8")


def _has_early_status_marker(path_str: str) -> bool:
    lines = _read_text(path_str).splitlines()
    head = "\n".join(lines[:12])
    return STATUS_MARKER in head


def main() -> int:
    errors: list[str] = []

    authority_text = _read_text(AUTHORITY_INDEX)
    if CURRENT_EXECUTION_PLAN not in authority_text:
        errors.append(
            f"{AUTHORITY_INDEX} must reference {CURRENT_EXECUTION_PLAN} as a current baseline document."
        )

    for path_str, description in ARCHIVAL_DOCS.items():
        if not _has_early_status_marker(path_str):
            errors.append(f"{path_str} is missing the required {description}.")

    if errors:
        print("Document status marker check failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Document status marker check passed.")
    print(f"- Current execution plan linked: {CURRENT_EXECUTION_PLAN}")
    for path_str in ARCHIVAL_DOCS:
        print(f"- Historical marker present: {path_str}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
