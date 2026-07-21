from copy import deepcopy
from dataclasses import replace

import pytest

from asset_registry.contracts import collision_asset_id
from asset_registry.repositories import SkillParserAdapter
from runtime.knowledge import validate_knowledge_plane_extension
from runtime.validators import RuntimeContractValidationError


def _skill_document():
    return {
        "meta": {
            "skill_id": "claude__skill__knowledge_test",
            "name": "Knowledge test",
        },
        "original_definition": {
            "source": "converted-skills/knowledge-test/SKILL.md",
            "skill_name": "Knowledge Reference",
        },
        "decomposition": {
            "actions": [],
            "rules": [],
            "directives": [
                {"id": "d_001", "name": "Use the reference", "description": "Context"}
            ],
        },
    }


def _revision(skill_document, *, collision_identity=False):
    options = {}
    if collision_identity:
        options = {
            "asset_id": collision_asset_id(skill_document),
            "identity_strategy": "source_name_disambiguation",
        }
    return SkillParserAdapter().adapt(
        skill_document,
        source_path="knowledge-test.json",
        source_digest="sha256:" + "0" * 64,
        **options,
    )


def _contract(asset_revision):
    return {
        "schema_version": "1.0.0",
        "extension_id": "knowledge-plane:reference:v1",
        "asset_ref": {
            "asset_type": "skill",
            "asset_id": asset_revision.asset_id,
            "revision_id": asset_revision.revision_id,
            "content_hash": asset_revision.content_hash,
        },
        "bindings": [
            {
                "binding_id": "kpb_001",
                "directive_id": "d_001",
                "phases": ["planning", "validation"],
                "usage": "context-only",
                "required": True,
                "unavailable_policy": "fail-closed",
                "budget": {"max_sources": 1, "max_characters": 4000},
                "sources": [
                    {
                        "source_ref": "docs/reference",
                        "source_revision": "v1",
                        "content_digest": "sha256:" + "1" * 64,
                        "classification": "internal",
                        "authority": "context-only",
                        "retrieval_mode": "snapshot",
                    }
                ],
            }
        ],
        "evidence": {
            "record_binding_ids": True,
            "record_source_digests": True,
            "event_watermark_required": True,
        },
    }


def test_knowledge_plane_contract_accepts_exact_context_only_binding():
    asset_revision = _revision(_skill_document())
    validate_knowledge_plane_extension(asset_revision, _contract(asset_revision))


def test_knowledge_plane_contract_accepts_canonical_collision_identity():
    asset_revision = _revision(_skill_document(), collision_identity=True)
    assert asset_revision.asset_id != asset_revision.legacy_skill_id

    validate_knowledge_plane_extension(asset_revision, _contract(asset_revision))


@pytest.mark.parametrize(
    "changes",
    [
        {"asset_type": "knowledge"},
        {"content_hash": "sha256:" + "2" * 64},
        {"revision_id": "asset-revision:sha256:" + "3" * 64},
        {"identity_strategy": "legacy_exact", "asset_id": "claude__skill__wrong"},
    ],
)
def test_knowledge_plane_contract_rejects_fabricated_asset_revision(changes):
    canonical_revision = _revision(_skill_document(), collision_identity=True)
    fabricated_revision = replace(canonical_revision, **changes)
    contract = _contract(fabricated_revision)
    contract["asset_ref"]["asset_type"] = "skill"

    with pytest.raises(RuntimeContractValidationError, match="canonical AssetRevision"):
        validate_knowledge_plane_extension(fabricated_revision, contract)


@pytest.mark.parametrize(
    ("mutation", "error"),
    [
        (
            lambda contract: contract["asset_ref"].update(
                {"asset_id": "claude__skill__different"}
            ),
            "asset_id does not match",
        ),
        (
            lambda contract: contract["bindings"][0].update({"directive_id": "d_999"}),
            "Unknown Knowledge Plane Directive reference",
        ),
        (
            lambda contract: contract["bindings"][0].update(
                {"required": True, "unavailable_policy": "skip-binding"}
            ),
            "must fail closed",
        ),
    ],
)
def test_knowledge_plane_contract_rejects_semantic_drift(mutation, error):
    asset_revision = _revision(_skill_document())
    contract = _contract(asset_revision)
    mutation(contract)

    with pytest.raises(RuntimeContractValidationError, match=error):
        validate_knowledge_plane_extension(asset_revision, contract)


def test_knowledge_plane_contract_rejects_authority_or_asset_type_expansion():
    asset_revision = _revision(_skill_document())
    contract = _contract(asset_revision)
    contract["bindings"][0]["sources"][0]["authority"] = "approval"

    with pytest.raises(RuntimeContractValidationError, match="context-only"):
        validate_knowledge_plane_extension(asset_revision, contract)

    contract = _contract(asset_revision)
    contract["asset_ref"]["asset_type"] = "knowledge"
    with pytest.raises(RuntimeContractValidationError, match="skill"):
        validate_knowledge_plane_extension(asset_revision, contract)


def test_knowledge_plane_contract_rejects_duplicate_and_over_budget_sources():
    asset_revision = _revision(_skill_document())
    contract = _contract(asset_revision)
    contract["bindings"][0]["sources"].append(
        deepcopy(contract["bindings"][0]["sources"][0])
    )

    with pytest.raises(RuntimeContractValidationError) as error:
        validate_knowledge_plane_extension(asset_revision, contract)

    assert "source count exceeds budget" in str(error.value)
    assert "Duplicate Knowledge Plane source references" in str(error.value)


@pytest.mark.parametrize("field", ["source_ref", "source_revision"])
def test_knowledge_plane_contract_rejects_whitespace_only_provenance(field):
    asset_revision = _revision(_skill_document())
    contract = _contract(asset_revision)
    contract["bindings"][0]["sources"][0][field] = "   "

    with pytest.raises(RuntimeContractValidationError, match="does not match"):
        validate_knowledge_plane_extension(asset_revision, contract)
