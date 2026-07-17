from __future__ import annotations

import json
from pathlib import Path

import pytest

from asset_registry.repositories import (
    AssetIdentityAmbiguousError,
    AssetNotFoundError,
    AssetSnapshotBuildError,
    LegacySkillAssetRepository,
    StaleSourceSnapshotError,
)


def _write_skill(path: Path, skill_id: str, *, name: str = "fixture") -> None:
    document = {
        "meta": {
            "skill_id": skill_id,
            "name": name,
            "description": "repository fixture",
            "parsed_by": "repository-test",
            "parser_version": "1.0.0",
        },
        "decomposition": {"actions": [], "rules": [], "directives": []},
    }
    path.write_text(json.dumps(document), encoding="utf-8")


def test_repository_builds_deterministic_snapshot_without_mutating_payload(tmp_path):
    _write_skill(tmp_path / "one.json", "claude__skill__one")
    first = LegacySkillAssetRepository(tmp_path)
    second = LegacySkillAssetRepository(tmp_path)
    revision = first.get_revision("claude__skill__one")

    assert first.snapshot_id == second.snapshot_id
    assert revision.asset_id == "claude__skill__one"
    assert revision.payload["meta"]["name"] == "fixture"


def test_repository_keeps_ambiguous_identity_as_conflict(tmp_path):
    _write_skill(tmp_path / "one.json", "claude__skill__duplicate", name="one")
    _write_skill(tmp_path / "two.json", "claude__skill__duplicate", name="two")
    repository = LegacySkillAssetRepository(tmp_path)

    assert repository.asset_count == 2
    assert repository.ambiguous_asset_ids == ("claude__skill__duplicate",)
    with pytest.raises(AssetIdentityAmbiguousError):
        repository.get_revision("claude__skill__duplicate")


def test_repository_rejects_malformed_replacement_snapshot(tmp_path):
    (tmp_path / "broken.json").write_text("{", encoding="utf-8")
    with pytest.raises(AssetSnapshotBuildError) as error:
        LegacySkillAssetRepository(tmp_path)
    assert error.value.diagnostics[0].code == "malformed_document"


def test_repository_fails_closed_after_source_change(tmp_path):
    source = tmp_path / "one.json"
    _write_skill(source, "claude__skill__one")
    repository = LegacySkillAssetRepository(tmp_path)
    _write_skill(source, "claude__skill__one", name="changed-name")

    with pytest.raises(StaleSourceSnapshotError):
        repository.get_revision("claude__skill__one")


def test_repository_requires_exact_revision_when_supplied(tmp_path):
    _write_skill(tmp_path / "one.json", "claude__skill__one")
    repository = LegacySkillAssetRepository(tmp_path)
    with pytest.raises(AssetNotFoundError):
        repository.get_revision(
            "claude__skill__one", "asset-revision:sha256:" + "0" * 64
        )


def test_checked_in_corpus_preserves_duplicate_as_ambiguity(root):
    repository = LegacySkillAssetRepository(root / "parsed")
    assert repository.asset_count == 196
    assert "claude__skill__java_to_java_upgrade" in repository.ambiguous_asset_ids
