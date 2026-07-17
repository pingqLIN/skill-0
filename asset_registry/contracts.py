"""Runtime Asset Envelope v1 and the lossless Skill compatibility mapping."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from runtime.digest import canonical_digest


ASSET_SCHEMA_VERSION = "1.0.0"
SUPPORTED_ASSET_TYPE = "skill"
SHA256_PREFIX = "sha256:"


class AssetContractError(ValueError):
    """Raised when an Asset envelope fails a closed contract check."""


def canonical_content_digest(document: Mapping[str, Any]) -> str:
    """Use the exact digest implementation that Runtime governance authorizes."""

    return canonical_digest(document)


def _require_non_empty_string(container: Mapping[str, Any], key: str) -> str:
    value = container.get(key)
    if not isinstance(value, str) or not value.strip():
        raise AssetContractError(f"{key} must be a non-empty string")
    return value


def skill_document_to_asset_envelope(
    skill_document: Mapping[str, Any],
    *,
    source_path: str,
    source_digest: str,
) -> dict[str, Any]:
    """Map one canonical Skill document to a deterministic Asset envelope.

    The payload is copied without normalization. Runtime Asset is an identity and
    provenance envelope; it is not a new ARD decomposition format.
    """

    meta = skill_document.get("meta")
    if not isinstance(meta, Mapping):
        raise AssetContractError("payload.meta must be an object")
    canonical_skill_id = _require_non_empty_string(meta, "skill_id")
    name = _require_non_empty_string(meta, "name")
    parser_id = str(meta.get("parsed_by") or "legacy-unknown")
    parser_version = str(
        meta.get("parser_version") or meta.get("schema_version") or "legacy-unknown"
    )
    if not source_digest.startswith(SHA256_PREFIX) or len(source_digest) != 71:
        raise AssetContractError("source_digest must be a sha256 digest")
    if not source_path:
        raise AssetContractError("source_path must be a non-empty string")

    payload = deepcopy(dict(skill_document))
    content_hash = canonical_content_digest(payload)
    envelope = {
        "schema_version": ASSET_SCHEMA_VERSION,
        "asset_id": canonical_skill_id,
        "revision_id": f"asset-revision:{content_hash}",
        "asset_type": SUPPORTED_ASSET_TYPE,
        "name": name,
        "summary": str(meta.get("description") or ""),
        "payload": payload,
        "content_hash": content_hash,
        "source_digest": source_digest,
        "parser_id": parser_id,
        "parser_version": parser_version,
        "provenance": {
            "source_path": source_path,
            "canonical_skill_id": canonical_skill_id,
        },
        "lifecycle": {"status": "active"},
    }
    validate_asset_envelope(envelope)
    return envelope


def validate_asset_envelope(envelope: Mapping[str, Any]) -> None:
    """Apply semantic checks that JSON Schema cannot express."""

    if envelope.get("asset_type") != SUPPORTED_ASSET_TYPE:
        raise AssetContractError("unsupported asset_type")
    payload = envelope.get("payload")
    if not isinstance(payload, Mapping):
        raise AssetContractError("payload must be an object")
    provenance = envelope.get("provenance")
    if not isinstance(provenance, Mapping):
        raise AssetContractError("provenance must be an object")

    meta = payload.get("meta")
    if not isinstance(meta, Mapping):
        raise AssetContractError("payload.meta must be an object")
    canonical_skill_id = _require_non_empty_string(meta, "skill_id")
    expected_asset_id = canonical_skill_id
    if envelope.get("asset_id") != expected_asset_id:
        raise AssetContractError("asset_id does not match payload.meta.skill_id")

    expected_hash = canonical_content_digest(payload)
    if envelope.get("content_hash") != expected_hash:
        raise AssetContractError("content_hash does not match payload")
    if envelope.get("revision_id") != f"asset-revision:{expected_hash}":
        raise AssetContractError("revision_id does not match content_hash")
    if provenance.get("canonical_skill_id") != canonical_skill_id:
        raise AssetContractError("provenance canonical_skill_id does not match payload")
    _require_non_empty_string(provenance, "source_path")


def asset_envelope_to_skill(envelope: Mapping[str, Any]) -> dict[str, Any]:
    """Return the unchanged legacy Skill payload after closed validation."""

    validate_asset_envelope(envelope)
    return deepcopy(dict(envelope["payload"]))
