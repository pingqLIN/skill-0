"""Domain values shared by Runtime Asset repository adapters."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AssetRevision:
    asset_id: str
    revision_id: str
    asset_type: str
    content_hash: str
    source_digest: str
    source_path: Path
    payload: dict[str, Any]
    legacy_skill_id: str
    identity_strategy: str


@dataclass(frozen=True)
class SnapshotDiagnostic:
    code: str
    path: str
    detail: str
