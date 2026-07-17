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


def _write_skill(
    path: Path,
    skill_id: str,
    *,
    name: str = "fixture",
    source_name: str | None = None,
) -> None:
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
    if source_name is not None:
        document["original_definition"] = {
            "source": f"converted-skills/{source_name}/SKILL.md",
            "skill_name": source_name,
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


def test_repository_rejects_direct_to_derived_canonical_collision(tmp_path):
    _write_skill(tmp_path / "99-direct.json", "claude__skill__target")
    _write_skill(
        tmp_path / "10-one.json",
        "claude__skill__legacy",
        source_name="target",
    )
    _write_skill(
        tmp_path / "11-two.json",
        "claude__skill__legacy",
        source_name="other",
    )
    with pytest.raises(AssetSnapshotBuildError) as error:
        LegacySkillAssetRepository(tmp_path)
    assert error.value.diagnostics[0].code == "canonical_identity_collision"


def test_repository_rejects_derived_to_derived_canonical_collision(tmp_path):
    _write_skill(
        tmp_path / "10-one.json",
        "claude__skill__legacy_one",
        source_name="shared",
    )
    _write_skill(
        tmp_path / "11-two.json",
        "claude__skill__legacy_one",
        source_name="one_other",
    )
    _write_skill(
        tmp_path / "20-three.json",
        "claude__skill__legacy_two",
        source_name="shared",
    )
    _write_skill(
        tmp_path / "21-four.json",
        "claude__skill__legacy_two",
        source_name="two_other",
    )
    with pytest.raises(AssetSnapshotBuildError) as error:
        LegacySkillAssetRepository(tmp_path)
    assert error.value.diagnostics[0].code == "canonical_identity_collision"


def test_repository_rejects_derived_id_that_shadows_legacy_alias(tmp_path):
    _write_skill(
        tmp_path / "10-one.json",
        "claude__skill__legacy_one",
        source_name="legacy_two",
    )
    _write_skill(
        tmp_path / "11-two.json",
        "claude__skill__legacy_one",
        source_name="one_other",
    )
    _write_skill(
        tmp_path / "20-three.json",
        "claude__skill__legacy_two",
        source_name="two_first",
    )
    _write_skill(
        tmp_path / "21-four.json",
        "claude__skill__legacy_two",
        source_name="two_second",
    )
    with pytest.raises(AssetSnapshotBuildError) as error:
        LegacySkillAssetRepository(tmp_path)
    assert error.value.diagnostics[0].code == "canonical_identity_collision"


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


def test_checked_in_corpus_disambiguates_canonical_ids_and_preserves_legacy_alias(root):
    repository = LegacySkillAssetRepository(root / "parsed")
    assert repository.asset_count == 196
    assert repository.ambiguous_asset_ids == ()
    assert repository.ambiguous_legacy_aliases == (
        "claude__skill__java_to_java_upgrade",
    )
    revisions = repository.list_asset_revisions(
        "claude__skill__java_to_java_upgrade"
    )
    assert {item.asset_id for item in revisions} == {
        "claude__skill__java_11_to_java_17_upgrade",
        "claude__skill__java_17_to_java_21_upgrade",
        "claude__skill__java_21_to_java_25_upgrade",
    }
    with pytest.raises(AssetIdentityAmbiguousError):
        repository.get_revision("claude__skill__java_to_java_upgrade")
