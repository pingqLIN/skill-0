"""Validate mirrored shared docs in the sibling ``skill-0-GUI`` repository."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Optional

try:
    from check_shared_docs import SHARED_SOURCE_DOCS
except ImportError:  # pragma: no cover - import path differs in pytest vs script mode
    from tools.check_shared_docs import SHARED_SOURCE_DOCS


REPO_ROOT = Path(__file__).resolve().parent.parent
BANNER_MARKERS = (
    "This file is mirrored into skill-0-GUI.",
    "Source:",
    "Do not edit this copy directly; update the source document and rerun npm run docs:sync.",
)
DEFAULT_GUI_ROOT_CANDIDATES = [
    REPO_ROOT.parent / "skill-0-GUI",
    Path("<skill-0-gui-root>"),
    Path("<skill-0-gui-root>"),
]


def _resolve_gui_root(explicit_root: Optional[str]) -> Optional[Path]:
    candidates: list[Path] = []
    if explicit_root:
        candidates.append(Path(explicit_root))
    env_root = os.environ.get("SKILL0_GUI_ROOT")
    if env_root:
        candidates.append(Path(env_root))
    candidates.extend(DEFAULT_GUI_ROOT_CANDIDATES)

    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.expanduser().resolve(strict=False)
        if resolved in seen:
            continue
        seen.add(resolved)
        if (resolved / "shared-docs.manifest.json").exists() and (resolved / "docs" / "shared").exists():
            return resolved
    return None


def _load_manifest(gui_root: Path) -> list[dict[str, str]]:
    manifest_path = gui_root / "shared-docs.manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, list):
        raise ValueError("shared-docs.manifest.json must contain a list")
    normalized: list[dict[str, str]] = []
    for entry in manifest:
        if not isinstance(entry, dict):
            raise ValueError("shared-docs.manifest.json entries must be objects")
        source = entry.get("source")
        target = entry.get("target")
        if not isinstance(source, str) or not isinstance(target, str):
            raise ValueError("shared-docs.manifest.json entries must define string source/target")
        normalized.append({"source": source, "target": target})
    return normalized


def _strip_banner(text: str) -> tuple[str, bool]:
    stripped = text.lstrip()
    if not stripped.startswith("<!--"):
        return text, False

    start_offset = len(text) - len(stripped)
    end_index = text.find("-->", start_offset)
    if end_index == -1:
        return text, False

    body = text[end_index + 3 :]
    if body.startswith("\r\n\r\n"):
        body = body[4:]
    elif body.startswith("\n\n"):
        body = body[2:]
    elif body.startswith("\r\n"):
        body = body[2:]
    elif body.startswith("\n"):
        body = body[1:]
    return body, True


def validate_shared_docs_mirror(
    *,
    source_root: Path,
    gui_root: Optional[Path],
    require_gui_root: bool = False,
) -> tuple[list[str], list[str]]:
    messages: list[str] = []
    errors: list[str] = []

    if gui_root is None:
        if require_gui_root:
            errors.append("Unable to resolve skill-0-GUI mirror root.")
        else:
            messages.append("Shared docs mirror check skipped: skill-0-GUI mirror root not found.")
        return errors, messages

    manifest = _load_manifest(gui_root)
    expected_names = sorted(Path(path_str).name for path_str in SHARED_SOURCE_DOCS)
    manifest_sources = sorted(entry["source"] for entry in manifest)
    manifest_targets = sorted(entry["target"] for entry in manifest)

    if manifest_sources != expected_names:
        errors.append(
            "shared-docs.manifest.json source set drifted from skill-0 canonical shared docs.\n"
            f"  expected: {expected_names}\n"
            f"  actual:   {manifest_sources}"
        )
    if manifest_targets != expected_names:
        errors.append(
            "shared-docs.manifest.json target set drifted from the canonical mirrored filenames.\n"
            f"  expected: {expected_names}\n"
            f"  actual:   {manifest_targets}"
        )

    mirror_dir = gui_root / "docs" / "shared"
    actual_mirror_docs = sorted(path.name for path in mirror_dir.glob("*.md"))
    if actual_mirror_docs != expected_names:
        errors.append(
            "skill-0-GUI/docs/shared source set drifted from the canonical list.\n"
            f"  expected: {expected_names}\n"
            f"  actual:   {actual_mirror_docs}"
        )

    for entry in manifest:
        source_name = entry["source"]
        target_name = entry["target"]
        source_path = source_root / "docs" / "shared" / source_name
        target_path = mirror_dir / target_name

        if not source_path.exists():
            errors.append(f"Missing canonical shared doc: {source_path}")
            continue
        if not target_path.exists():
            errors.append(f"Missing mirrored doc: {target_path}")
            continue

        source_text = source_path.read_text(encoding="utf-8")
        mirrored_text = target_path.read_text(encoding="utf-8")
        mirrored_body, has_banner = _strip_banner(mirrored_text)

        if not has_banner:
            errors.append(f"{target_path} is missing the mirrored-doc banner.")
            continue
        for marker in BANNER_MARKERS:
            if marker not in mirrored_text:
                errors.append(f"{target_path} is missing required banner text: {marker}")

        if mirrored_body != source_text:
            errors.append(
                "Mirrored shared doc drift detected.\n"
                f"  source: {source_path}\n"
                f"  mirror: {target_path}"
            )
        else:
            messages.append(f"checked {source_name} -> {target_path.relative_to(gui_root)}")

    return errors, messages


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gui-root", help="Path to the skill-0-GUI repository root.")
    parser.add_argument(
        "--source-root",
        default=str(REPO_ROOT),
        help="Path to the skill-0 repository root. Defaults to this repo.",
    )
    parser.add_argument(
        "--require-gui-root",
        action="store_true",
        help="Fail instead of skipping when the GUI mirror repository cannot be resolved.",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    gui_root = _resolve_gui_root(args.gui_root)
    source_root = Path(args.source_root).expanduser().resolve(strict=False)
    errors, messages = validate_shared_docs_mirror(
        source_root=source_root,
        gui_root=gui_root,
        require_gui_root=args.require_gui_root,
    )

    if errors:
        print("Shared docs mirror check failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Shared docs mirror check passed.")
    if gui_root is not None:
        print(f"- GUI mirror root: {gui_root}")
    for message in messages:
        print(f"- {message}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
