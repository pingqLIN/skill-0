"""Regression tests for repo-local documentation validation helpers."""

import json
from pathlib import Path

from tools import check_doc_status_markers, check_shared_docs, check_shared_docs_mirror


def test_doc_status_markers_check_passes_on_repo_baseline():
    assert check_doc_status_markers.main() == 0


def test_doc_status_markers_tracks_historical_execution_snapshot():
    expected_historical_docs = {
        "reference.md",
        "docs/final-development-phase-plan-2026-03-23.md",
        "docs/implementation-summary.md",
        "docs/planning/current-execution-plan-2026-03-19.md",
        "docs/planning/plan.md",
        "docs/planning/plan-20-skills.md",
        "docs/planning/yolo-dev-plan.md",
        "docs/project-progress-report-2026-03-23.md",
    }
    assert expected_historical_docs.issubset(check_doc_status_markers.ARCHIVAL_DOCS)


def test_shared_docs_check_passes_on_repo_baseline():
    assert check_shared_docs.main() == 0


def test_shared_docs_check_tracks_ownership_boundary_markers():
    assert check_shared_docs.MODEL_BOUNDARY_MARKERS == [
        "1. `skill-0` owns the source documents",
        "2. shared source files live in `docs/shared/`",
        "3. `skill-0-GUI` mirrors selected files into its own `docs/shared/`",
    ]
    assert check_shared_docs.README_BOUNDARY_MARKERS == [
        "The mirrored copies should be treated as vendored contract documents, not independently authored files.",
    ]
    assert check_shared_docs.SESSION_RULE_BOUNDARY_MARKERS == [
        "3. `docs/shared/` in `skill-0` is the cross-repo documentation source of truth",
        "4. `skill-0-GUI/docs/shared/` contains mirrored copies of selected contract documents",
        "- mirrored docs in `skill-0-GUI/docs/shared/` are not independently authored",
    ]


def test_shared_docs_mirror_check_skips_when_gui_repo_is_unavailable(tmp_path):
    missing_gui_root = tmp_path / "missing-gui"
    errors, messages = check_shared_docs_mirror.validate_shared_docs_mirror(
        source_root=Path.cwd(),
        gui_root=missing_gui_root if missing_gui_root.exists() else None,
        require_gui_root=False,
    )
    assert errors == []
    assert messages == ["Shared docs mirror check skipped: skill-0-GUI mirror root not found."]


def test_shared_docs_mirror_check_detects_matching_mirror(tmp_path):
    source_root = tmp_path / "skill-0"
    gui_root = tmp_path / "skill-0-GUI"
    shared_dir = source_root / "docs" / "shared"
    mirror_dir = gui_root / "docs" / "shared"
    shared_dir.mkdir(parents=True)
    mirror_dir.mkdir(parents=True)

    manifest_entries = []
    for relative_path in check_shared_docs.SHARED_SOURCE_DOCS:
        source_name = Path(relative_path).name
        source_text = f"# {source_name}\nsource body for {source_name}\n"
        (shared_dir / source_name).write_text(source_text, encoding="utf-8")
        mirrored_text = (
            "<!--\n"
            "This file is mirrored into skill-0-GUI.\n"
            f"Source: ../skill-0/docs/shared/{source_name}\n"
            "Do not edit this copy directly; update the source document and rerun npm run docs:sync.\n"
            "-->\n\n"
            f"{source_text}"
        )
        (mirror_dir / source_name).write_text(mirrored_text, encoding="utf-8")
        manifest_entries.append({"source": source_name, "target": source_name})

    (gui_root / "shared-docs.manifest.json").write_text(
        json.dumps(manifest_entries, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    errors, messages = check_shared_docs_mirror.validate_shared_docs_mirror(
        source_root=source_root,
        gui_root=gui_root,
        require_gui_root=True,
    )

    assert errors == []
    assert len(messages) == len(check_shared_docs.SHARED_SOURCE_DOCS)


def test_shared_docs_mirror_check_detects_outdated_mirror(tmp_path):
    source_root = tmp_path / "skill-0"
    gui_root = tmp_path / "skill-0-GUI"
    shared_dir = source_root / "docs" / "shared"
    mirror_dir = gui_root / "docs" / "shared"
    shared_dir.mkdir(parents=True)
    mirror_dir.mkdir(parents=True)

    manifest_entries = []
    for relative_path in check_shared_docs.SHARED_SOURCE_DOCS:
        source_name = Path(relative_path).name
        source_text = f"# {source_name}\nsource body for {source_name}\n"
        (shared_dir / source_name).write_text(source_text, encoding="utf-8")
        mirrored_body = "outdated body\n" if source_name == "README.md" else source_text
        mirrored_text = (
            "<!--\n"
            "This file is mirrored into skill-0-GUI.\n"
            f"Source: ../skill-0/docs/shared/{source_name}\n"
            "Do not edit this copy directly; update the source document and rerun npm run docs:sync.\n"
            "-->\n\n"
            f"{mirrored_body}"
        )
        (mirror_dir / source_name).write_text(mirrored_text, encoding="utf-8")
        manifest_entries.append({"source": source_name, "target": source_name})

    (gui_root / "shared-docs.manifest.json").write_text(
        json.dumps(manifest_entries, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    errors, _messages = check_shared_docs_mirror.validate_shared_docs_mirror(
        source_root=source_root,
        gui_root=gui_root,
        require_gui_root=True,
    )

    assert any("Mirrored shared doc drift detected." in error for error in errors)
