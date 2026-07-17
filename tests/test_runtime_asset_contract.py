from __future__ import annotations

from copy import deepcopy
import json

import pytest
from jsonschema import FormatChecker
from jsonschema.validators import validator_for

from asset_registry.contracts import (
    AssetContractError,
    asset_envelope_to_skill,
    canonical_content_digest,
    collision_asset_id,
    skill_document_to_asset_envelope,
    validate_asset_envelope,
)


def _validator(schema):
    validator_class = validator_for(schema)
    validator_class.check_schema(schema)
    return validator_class(schema, format_checker=FormatChecker())


def test_runtime_asset_schema_accepts_skill_fixture(read_json):
    schema = read_json("schema/runtime-asset-envelope.schema.json")
    fixture = read_json("examples/runtime-asset-envelope.skill.valid.json")
    assert list(_validator(schema).iter_errors(fixture)) == []
    validate_asset_envelope(fixture)


@pytest.mark.parametrize(
    "name",
    [
        "runtime-asset-envelope.missing-revision.invalid.json",
        "runtime-asset-envelope.unsupported-type.invalid.json",
        "runtime-asset-envelope.malformed-provenance.invalid.json",
    ],
)
def test_runtime_asset_structural_failures_are_rejected(read_json, name):
    schema = read_json("schema/runtime-asset-envelope.schema.json")
    fixture = read_json(f"examples/{name}")
    assert list(_validator(schema).iter_errors(fixture))


def test_runtime_asset_digest_mismatch_fails_semantic_validation(read_json):
    fixture = read_json("examples/runtime-asset-envelope.digest-mismatch.invalid.json")
    with pytest.raises(AssetContractError, match="content_hash"):
        validate_asset_envelope(fixture)


def test_skill_mapping_is_deterministic_and_lossless(read_json):
    skill = read_json("tests/fixtures/valid_skill.json")
    skill["meta"]["parsed_by"] = "contract-test"
    skill["meta"]["parser_version"] = "2.4.0"
    first = skill_document_to_asset_envelope(
        skill,
        source_path="tests/fixtures/valid_skill.json",
        source_digest="sha256:" + "a" * 64,
    )
    second = skill_document_to_asset_envelope(
        deepcopy(skill),
        source_path="tests/fixtures/valid_skill.json",
        source_digest="sha256:" + "a" * 64,
    )
    assert first == second
    assert first["revision_id"] == f"asset-revision:{canonical_content_digest(skill)}"
    assert asset_envelope_to_skill(first) == skill


def test_asset_id_drift_fails_closed(read_json):
    envelope = read_json("examples/runtime-asset-envelope.skill.valid.json")
    envelope["asset_id"] = "claude__skill__other"
    with pytest.raises(AssetContractError, match="asset_id"):
        validate_asset_envelope(envelope)


def test_collision_identity_is_deterministic_and_payload_lossless(root):
    skill = json.loads(
        (root / "parsed/java-11-to-java-17-upgrade-skill.json").read_text(
            encoding="utf-8"
        )
    )
    asset_id = collision_asset_id(skill)
    envelope = skill_document_to_asset_envelope(
        skill,
        source_path="java-11-to-java-17-upgrade-skill.json",
        source_digest="sha256:" + "a" * 64,
        asset_id=asset_id,
        identity_strategy="source_name_disambiguation",
    )
    assert asset_id == "claude__skill__java_11_to_java_17_upgrade"
    assert envelope["identity"]["legacy_skill_id"] == (
        "claude__skill__java_to_java_upgrade"
    )
    assert asset_envelope_to_skill(envelope) == skill
    assert envelope["revision_id"] == f"asset-revision:{canonical_content_digest(skill)}"


def test_revision_namespace_confusion_fails_closed(read_json):
    envelope = read_json("examples/runtime-asset-envelope.skill.valid.json")
    envelope["revision_id"] = envelope["content_hash"]
    with pytest.raises(AssetContractError, match="revision_id"):
        validate_asset_envelope(envelope)


def test_legacy_compatibility_map_prohibits_global_replace(root):
    compatibility_map = json.loads(
        (root / "docs/contracts/runtime-asset-legacy-compatibility-map.json").read_text(
            encoding="utf-8"
        )
    )
    assert compatibility_map["global_replace_allowed"] is False
    categories = set(compatibility_map["categories"])
    assert {rule["category"] for rule in compatibility_map["path_rules"]} <= categories
    assert {
        "domain_generic",
        "skill_adapter_specific",
        "legacy_compatibility",
        "historical_migration",
        "fixture",
        "documentation_only",
    } == categories
