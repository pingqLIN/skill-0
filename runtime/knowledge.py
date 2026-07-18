"""Fail-closed validation for the Knowledge Plane extension contract."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from asset_registry.contracts import AssetContractError, skill_document_to_asset_envelope
from asset_registry.models import AssetRevision

from .validators import RuntimeContractValidationError, load_json, validate_schema


DEFAULT_SCHEMA_PATH = (
    Path(__file__).resolve().parents[1]
    / "schema"
    / "knowledge-plane-extension-contract.schema.json"
)


def validate_knowledge_plane_extension(
    asset_revision: AssetRevision,
    contract: dict[str, Any],
) -> None:
    """Validate schema, exact Asset identity, and Directive cross-references.

    This validator does not retrieve source content or authorize Runtime work.
    Knowledge Plane sources remain context-only inputs.
    """

    validate_schema(contract, load_json(DEFAULT_SCHEMA_PATH))
    problems: list[str] = []

    try:
        canonical_envelope = skill_document_to_asset_envelope(
            asset_revision.payload,
            source_path=asset_revision.source_path.as_posix(),
            source_digest=asset_revision.source_digest,
            asset_id=asset_revision.asset_id,
            identity_strategy=asset_revision.identity_strategy,
        )
    except AssetContractError as exc:
        problems.append(f"Invalid canonical AssetRevision: {exc}")
    else:
        revision_fields = {
            "asset_type": asset_revision.asset_type,
            "asset_id": asset_revision.asset_id,
            "revision_id": asset_revision.revision_id,
            "content_hash": asset_revision.content_hash,
        }
        for field, actual in revision_fields.items():
            if actual != canonical_envelope[field]:
                problems.append(f"Invalid canonical AssetRevision {field}")
        if asset_revision.legacy_skill_id != canonical_envelope["identity"]["legacy_skill_id"]:
            problems.append("Invalid canonical AssetRevision legacy_skill_id")

    asset_ref = contract["asset_ref"]
    if asset_ref["asset_type"] != asset_revision.asset_type:
        problems.append("Knowledge Plane asset_type does not match canonical Asset revision")
    if asset_ref["asset_id"] != asset_revision.asset_id:
        problems.append("Knowledge Plane asset_id does not match canonical Skill identity")
    if asset_ref["content_hash"] != asset_revision.content_hash:
        problems.append("Knowledge Plane content_hash does not match canonical Skill payload")
    if asset_ref["revision_id"] != asset_revision.revision_id:
        problems.append("Knowledge Plane revision_id does not match canonical Skill payload")

    directive_ids = {
        directive.get("id")
        for directive in asset_revision.payload.get("decomposition", {}).get("directives", [])
    }
    bindings = contract["bindings"]
    binding_ids = [binding["binding_id"] for binding in bindings]
    duplicate_binding_ids = sorted(
        binding_id for binding_id in set(binding_ids) if binding_ids.count(binding_id) > 1
    )
    if duplicate_binding_ids:
        problems.append(f"Duplicate Knowledge Plane bindings: {duplicate_binding_ids}")

    for binding in bindings:
        directive_id = binding["directive_id"]
        if directive_id not in directive_ids:
            problems.append(f"Unknown Knowledge Plane Directive reference: {directive_id}")
        if binding["required"] and binding["unavailable_policy"] != "fail-closed":
            problems.append(
                f"Required Knowledge Plane binding must fail closed: {binding['binding_id']}"
            )
        if len(binding["sources"]) > binding["budget"]["max_sources"]:
            problems.append(
                f"Knowledge Plane source count exceeds budget: {binding['binding_id']}"
            )
        source_refs = [source["source_ref"] for source in binding["sources"]]
        duplicates = sorted(
            source_ref for source_ref in set(source_refs) if source_refs.count(source_ref) > 1
        )
        if duplicates:
            problems.append(
                f"Duplicate Knowledge Plane source references in {binding['binding_id']}: {duplicates}"
            )

    if problems:
        raise RuntimeContractValidationError("\n".join(problems))
