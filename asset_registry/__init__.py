"""Compatibility-first Runtime Asset contracts and storage boundaries."""

from .contracts import (
    AssetContractError,
    asset_envelope_to_skill,
    canonical_content_digest,
    skill_document_to_asset_envelope,
    validate_asset_envelope,
)
from .models import AssetRevision, SnapshotDiagnostic
from .repositories import (
    AssetIdentityAmbiguousError,
    AssetNotFoundError,
    AssetRepository,
    AssetRepositoryError,
    AssetSnapshotBuildError,
    LegacySkillAssetRepository,
    SkillParserAdapter,
    StaleSourceSnapshotError,
)
from .search import AssetSearchResult, BoundedSearchExecutor, SearchOverloadedError

__all__ = [
    "AssetContractError",
    "asset_envelope_to_skill",
    "canonical_content_digest",
    "skill_document_to_asset_envelope",
    "validate_asset_envelope",
    "AssetIdentityAmbiguousError",
    "AssetNotFoundError",
    "AssetRepository",
    "AssetRepositoryError",
    "AssetRevision",
    "AssetSnapshotBuildError",
    "LegacySkillAssetRepository",
    "SkillParserAdapter",
    "SnapshotDiagnostic",
    "StaleSourceSnapshotError",
    "AssetSearchResult",
    "BoundedSearchExecutor",
    "SearchOverloadedError",
]
