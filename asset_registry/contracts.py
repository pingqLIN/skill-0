"""Runtime Asset Envelope v1 and the lossless Skill compatibility mapping."""

from __future__ import annotations

from copy import deepcopy
import re
from typing import Any, Mapping

from runtime.digest import canonical_digest


ASSET_SCHEMA_VERSION = "1.0.0"
SUPPORTED_ASSET_TYPE = "skill"
SHA256_PREFIX = "sha256:"
ASSET_ID_PATTERN = re.compile(
    r"^(?:claude|mcp)__[a-z0-9_]+__[a-z0-9][a-z0-9_]*$"
)


class AssetContractError(ValueError):
    """Raised when an Asset envelope fails a closed contract check."""


def canonical_content_digest(document: Mapping[str, Any]) -> str:
    """Use the exact digest implementation that Runtime governance authorizes."""

    return canonical_digest(document)


def collision_asset_id(skill_document: Mapping[str, Any]) -> str:
    """Derive a stable Asset ID only from explicit source identity metadata."""

    meta = skill_document.get("meta")
    original = skill_document.get("original_definition")
    if not isinstance(meta, Mapping) or not isinstance(original, Mapping):
        raise AssetContractError("collision identity requires original_definition")
    legacy_skill_id = _require_non_empty_string(meta, "skill_id")
    parts = legacy_skill_id.split("__", 2)
    if len(parts) != 3:
        raise AssetContractError("legacy skill_id cannot provide Asset namespace")
    source_name = _require_non_empty_string(original, "skill_name").lower()
    slug = re.sub(r"[^a-z0-9]+", "_", source_name).strip("_")
    candidate = f"{parts[0]}__{parts[1]}__{slug}"
    if not ASSET_ID_PATTERN.fullmatch(candidate):
        raise AssetContractError("source identity cannot produce a valid asset_id")
    return candidate


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
    asset_id: str | None = None,
    identity_strategy: str = "legacy_exact",
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
    resolved_asset_id = asset_id or canonical_skill_id
    if identity_strategy == "legacy_exact":
        if resolved_asset_id != canonical_skill_id:
            raise AssetContractError("legacy_exact identity must preserve skill_id")
    elif identity_strategy == "source_name_disambiguation":
        if resolved_asset_id != collision_asset_id(skill_document):
            raise AssetContractError("asset_id does not match source identity")
    else:
        raise AssetContractError("unsupported identity strategy")

    envelope = {
        "schema_version": ASSET_SCHEMA_VERSION,
        "asset_id": resolved_asset_id,
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
            "canonical_asset_id": resolved_asset_id,
        },
        "identity": {
            "strategy": identity_strategy,
            "legacy_skill_id": canonical_skill_id,
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
    identity = envelope.get("identity")
    if identity is None:
        identity = {
            "strategy": "legacy_exact",
            "legacy_skill_id": canonical_skill_id,
        }
    if not isinstance(identity, Mapping):
        raise AssetContractError("identity must be an object")
    if identity.get("legacy_skill_id") != canonical_skill_id:
        raise AssetContractError("identity legacy_skill_id does not match payload")
    strategy = identity.get("strategy")
    if strategy == "legacy_exact":
        expected_asset_id = canonical_skill_id
    elif strategy == "source_name_disambiguation":
        expected_asset_id = collision_asset_id(payload)
    else:
        raise AssetContractError("unsupported identity strategy")
    if envelope.get("asset_id") != expected_asset_id:
        raise AssetContractError("asset_id does not match identity strategy")

    expected_hash = canonical_content_digest(payload)
    if envelope.get("content_hash") != expected_hash:
        raise AssetContractError("content_hash does not match payload")
    if envelope.get("revision_id") != f"asset-revision:{expected_hash}":
        raise AssetContractError("revision_id does not match content_hash")
    if provenance.get("canonical_skill_id") != canonical_skill_id:
        raise AssetContractError("provenance canonical_skill_id does not match payload")
    canonical_asset_id = provenance.get("canonical_asset_id")
    if canonical_asset_id is not None and canonical_asset_id != envelope.get("asset_id"):
        raise AssetContractError("provenance canonical_asset_id does not match asset_id")
    _require_non_empty_string(provenance, "source_path")


def asset_envelope_to_skill(envelope: Mapping[str, Any]) -> dict[str, Any]:
    """Return the unchanged legacy Skill payload after closed validation."""

    validate_asset_envelope(envelope)
    return deepcopy(dict(envelope["payload"]))
