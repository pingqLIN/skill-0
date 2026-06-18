"""Validate the shared-doc source set and its canonical documentation.

This keeps the documented shared-doc contract from drifting away from the
actual files under docs/shared/.
"""

from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parent.parent
SHARED_DOC_MODEL = "docs/shared-documentation-model.md"
SHARED_DOC_README = "docs/shared/README.md"
SHARED_SESSION_RULES = "docs/shared/04-cross-repo-session-rules.md"
STATUS_MARKER = "Implementation status:"
SHARED_SOURCE_DOCS = [
    "docs/shared/README.md",
    "docs/shared/01-parser-contract.md",
    "docs/shared/02-mode-and-equivalence-contract.md",
    "docs/shared/03-shared-terminology.md",
    "docs/shared/04-cross-repo-session-rules.md",
]
MODEL_BOUNDARY_MARKERS = [
    "1. `skill-0` owns the source documents",
    "2. shared source files live in `docs/shared/`",
    "3. `skill-0-GUI` mirrors selected files into its own `docs/shared/`",
]
README_BOUNDARY_MARKERS = [
    "The mirrored copies should be treated as vendored contract documents, not independently authored files.",
]
SESSION_RULE_BOUNDARY_MARKERS = [
    "3. `docs/shared/` in `skill-0` is the cross-repo documentation source of truth",
    "4. `skill-0-GUI/docs/shared/` contains mirrored copies of selected contract documents",
    "- mirrored docs in `skill-0-GUI/docs/shared/` are not independently authored",
]


def _read_text(path_str: str) -> str:
    return (REPO_ROOT / path_str).read_text(encoding="utf-8")


def _has_early_status_marker(path_str: str) -> bool:
    lines = _read_text(path_str).splitlines()
    head = "\n".join(lines[:12])
    return STATUS_MARKER in head


def _actual_shared_docs() -> list[str]:
    shared_dir = REPO_ROOT / "docs" / "shared"
    return sorted(path.relative_to(REPO_ROOT).as_posix() for path in shared_dir.glob("*.md"))


def main() -> int:
    errors: list[str] = []

    if not _has_early_status_marker(SHARED_DOC_MODEL):
        errors.append(f"{SHARED_DOC_MODEL} must declare an early implementation status marker.")

    actual_docs = _actual_shared_docs()
    if actual_docs != sorted(SHARED_SOURCE_DOCS):
        errors.append(
            "docs/shared/ source set drifted from the canonical list.\n"
            f"  expected: {sorted(SHARED_SOURCE_DOCS)}\n"
            f"  actual:   {actual_docs}"
        )

    model_text = _read_text(SHARED_DOC_MODEL)
    readme_text = _read_text(SHARED_DOC_README)
    session_rules_text = _read_text(SHARED_SESSION_RULES)

    for path_str in SHARED_SOURCE_DOCS:
        if path_str not in model_text:
            errors.append(f"{SHARED_DOC_MODEL} must list {path_str} in the shared source set.")
        basename = Path(path_str).name
        if basename not in readme_text:
            errors.append(f"{SHARED_DOC_README} must mention {basename}.")

    for marker in MODEL_BOUNDARY_MARKERS:
        if marker not in model_text:
            errors.append(f"{SHARED_DOC_MODEL} must keep the ownership boundary marker: {marker}")

    for marker in README_BOUNDARY_MARKERS:
        if marker not in readme_text:
            errors.append(f"{SHARED_DOC_README} must keep the ownership boundary marker: {marker}")

    for marker in SESSION_RULE_BOUNDARY_MARKERS:
        if marker not in session_rules_text:
            errors.append(f"{SHARED_SESSION_RULES} must keep the provenance boundary marker: {marker}")

    if errors:
        print("Shared docs check failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Shared docs check passed.")
    print(f"- Shared doc model: {SHARED_DOC_MODEL}")
    print(f"- Shared source files: {len(SHARED_SOURCE_DOCS)}")
    for path_str in SHARED_SOURCE_DOCS:
        print(f"  - {path_str}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
