"""Narrow Runtime Asset repository protocols and the legacy corpus adapter."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Protocol

from runtime.digest import canonical_digest

from .contracts import (
    AssetContractError,
    collision_asset_id,
    skill_document_to_asset_envelope,
)
from .models import AssetRevision, SnapshotDiagnostic


class AssetRepositoryError(RuntimeError):
    code = "asset_repository_error"


class AssetNotFoundError(AssetRepositoryError):
    code = "asset_not_found"


class AssetIdentityAmbiguousError(AssetRepositoryError):
    code = "ambiguous_asset_identity"


class StaleSourceSnapshotError(AssetRepositoryError):
    code = "stale_source_snapshot"


class AssetSnapshotBuildError(AssetRepositoryError):
    code = "invalid_source_snapshot"

    def __init__(self, diagnostics: tuple[SnapshotDiagnostic, ...]):
        super().__init__(self.code)
        self.diagnostics = diagnostics


class AssetRepository(Protocol):
    snapshot_id: str

    def get_revision(
        self, asset_id: str, revision_id: str | None = None
    ) -> AssetRevision: ...

    def assert_fresh(self) -> None: ...

    def list_revisions(self) -> tuple[AssetRevision, ...]: ...

    def list_asset_revisions(self, asset_id: str) -> tuple[AssetRevision, ...]: ...


class SkillParserAdapter:
    """Wrap existing canonical Skill output without changing parser behavior."""

    def adapt(
        self,
        document: dict,
        *,
        source_path: str,
        source_digest: str,
        asset_id: str | None = None,
        identity_strategy: str = "legacy_exact",
    ) -> AssetRevision:
        envelope = skill_document_to_asset_envelope(
            document,
            source_path=source_path,
            source_digest=source_digest,
            asset_id=asset_id,
            identity_strategy=identity_strategy,
        )
        return AssetRevision(
            asset_id=envelope["asset_id"],
            revision_id=envelope["revision_id"],
            asset_type=envelope["asset_type"],
            content_hash=envelope["content_hash"],
            source_digest=envelope["source_digest"],
            source_path=Path(source_path),
            payload=envelope["payload"],
            legacy_skill_id=envelope["identity"]["legacy_skill_id"],
            identity_strategy=envelope["identity"]["strategy"],
        )


@dataclass(frozen=True)
class _FileStamp:
    relative_path: str
    size: int
    modified_ns: int


class LegacySkillAssetRepository:
    """Immutable process-local view of the checked-in canonical Skill corpus.

    Ambiguous IDs are retained as conflicts so unrelated assets remain
    available. Malformed documents reject the replacement snapshot.
    """

    def __init__(self, corpus_dir: Path, *, adapter: SkillParserAdapter | None = None):
        self.corpus_dir = corpus_dir.resolve()
        self.adapter = adapter or SkillParserAdapter()
        self._available: dict[str, AssetRevision] = {}
        self._ambiguous: dict[str, tuple[AssetRevision, ...]] = {}
        self._legacy_aliases: dict[str, tuple[str, ...]] = {}
        self._file_stamps: tuple[_FileStamp, ...] = ()
        self._directory_modified_ns = 0
        self.snapshot_id = ""
        self._build()

    @property
    def ambiguous_asset_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._ambiguous))

    @property
    def ambiguous_legacy_aliases(self) -> tuple[str, ...]:
        return tuple(sorted(self._legacy_aliases))

    @property
    def asset_count(self) -> int:
        return len(self._available) + sum(len(items) for items in self._ambiguous.values())

    def _build(self) -> None:
        diagnostics: list[SnapshotDiagnostic] = []
        grouped: defaultdict[str, list[AssetRevision]] = defaultdict(list)
        stamps: list[_FileStamp] = []
        if not self.corpus_dir.is_dir():
            raise AssetSnapshotBuildError(
                (SnapshotDiagnostic("missing_corpus", str(self.corpus_dir), "directory not found"),)
            )

        for path in sorted(self.corpus_dir.glob("*.json"), key=lambda item: item.name):
            relative_path = path.relative_to(self.corpus_dir).as_posix()
            try:
                raw = path.read_bytes()
                document = json.loads(raw.decode("utf-8"))
                raw_digest = "sha256:" + hashlib.sha256(raw).hexdigest()
                revision = self.adapter.adapt(
                    document,
                    source_path=relative_path,
                    source_digest=raw_digest,
                )
                stat = path.stat()
            except (OSError, UnicodeDecodeError, json.JSONDecodeError, AssetContractError) as exc:
                diagnostics.append(
                    SnapshotDiagnostic("malformed_document", relative_path, str(exc))
                )
                continue
            grouped[revision.asset_id].append(revision)
            stamps.append(_FileStamp(relative_path, stat.st_size, stat.st_mtime_ns))
        if diagnostics:
            raise AssetSnapshotBuildError(tuple(diagnostics))

        available: dict[str, AssetRevision] = {}
        ambiguous: dict[str, tuple[AssetRevision, ...]] = {}
        aliases: dict[str, tuple[str, ...]] = {}
        legacy_namespace = set(grouped)
        for legacy_id, revisions in grouped.items():
            if len(revisions) == 1:
                if legacy_id in available:
                    diagnostics.append(
                        SnapshotDiagnostic(
                            "canonical_identity_collision",
                            revisions[0].source_path.as_posix(),
                            legacy_id,
                        )
                    )
                    continue
                available[legacy_id] = revisions[0]
                continue
            resolved: list[AssetRevision] = []
            try:
                for revision in revisions:
                    derived_id = collision_asset_id(revision.payload)
                    resolved.append(
                        self.adapter.adapt(
                            revision.payload,
                            source_path=revision.source_path.as_posix(),
                            source_digest=revision.source_digest,
                            asset_id=derived_id,
                            identity_strategy="source_name_disambiguation",
                        )
                    )
            except AssetContractError:
                resolved = []
            resolved_ids = [item.asset_id for item in resolved]
            if resolved and len(set(resolved_ids)) == len(resolved_ids):
                conflicting_ids = sorted(
                    set(resolved_ids) & (set(available) | legacy_namespace)
                )
                if conflicting_ids:
                    diagnostics.extend(
                        SnapshotDiagnostic(
                            "canonical_identity_collision",
                            legacy_id,
                            asset_id,
                        )
                        for asset_id in conflicting_ids
                    )
                    continue
                available.update((item.asset_id, item) for item in resolved)
                aliases[legacy_id] = tuple(sorted(resolved_ids))
            else:
                ambiguous[legacy_id] = tuple(revisions)

        if diagnostics:
            raise AssetSnapshotBuildError(tuple(diagnostics))

        self._available = available
        self._ambiguous = ambiguous
        self._legacy_aliases = aliases
        self._file_stamps = tuple(stamps)
        self._directory_modified_ns = self.corpus_dir.stat().st_mtime_ns
        manifest = [
            {
                "path": revision.source_path.as_posix(),
                "asset_id": revision.asset_id,
                "legacy_skill_id": revision.legacy_skill_id,
                "identity_strategy": revision.identity_strategy,
                "source_digest": revision.source_digest,
                "content_hash": revision.content_hash,
                "parser_id": revision.payload.get("meta", {}).get(
                    "parsed_by", "legacy-unknown"
                ),
                "parser_version": revision.payload.get("meta", {}).get(
                    "parser_version",
                    revision.payload.get("meta", {}).get(
                        "schema_version", "legacy-unknown"
                    ),
                ),
            }
            for revision in self.list_revisions(check_fresh=False)
        ]
        self.snapshot_id = canonical_digest(
            {"manifest_version": "1.0.0", "entries": manifest}
        )

    def assert_fresh(self) -> None:
        """Fail closed without re-enumerating or reparsing the directory."""

        try:
            if self.corpus_dir.stat().st_mtime_ns != self._directory_modified_ns:
                raise StaleSourceSnapshotError(StaleSourceSnapshotError.code)
            for stamp in self._file_stamps:
                current = (self.corpus_dir / stamp.relative_path).stat()
                if current.st_size != stamp.size or current.st_mtime_ns != stamp.modified_ns:
                    raise StaleSourceSnapshotError(StaleSourceSnapshotError.code)
        except OSError as exc:
            raise StaleSourceSnapshotError(StaleSourceSnapshotError.code) from exc

    def get_revision(
        self, asset_id: str, revision_id: str | None = None
    ) -> AssetRevision:
        self.assert_fresh()
        if asset_id in self._ambiguous:
            raise AssetIdentityAmbiguousError(AssetIdentityAmbiguousError.code)
        if asset_id in self._legacy_aliases:
            raise AssetIdentityAmbiguousError(AssetIdentityAmbiguousError.code)
        revision = self._available.get(asset_id)
        if revision is None:
            raise AssetNotFoundError(AssetNotFoundError.code)
        if revision_id is not None and revision.revision_id != revision_id:
            raise AssetNotFoundError(AssetNotFoundError.code)
        return revision

    def list_revisions(self, *, check_fresh: bool = True) -> tuple[AssetRevision, ...]:
        if check_fresh:
            self.assert_fresh()
        revisions = list(self._available.values())
        for ambiguous in self._ambiguous.values():
            revisions.extend(ambiguous)
        return tuple(sorted(revisions, key=lambda item: item.source_path.as_posix()))

    def list_asset_revisions(self, asset_id: str) -> tuple[AssetRevision, ...]:
        self.assert_fresh()
        alias_targets = self._legacy_aliases.get(asset_id)
        if alias_targets is not None:
            return tuple(self._available[target] for target in alias_targets)
        if asset_id in self._ambiguous:
            return self._ambiguous[asset_id]
        revision = self._available.get(asset_id)
        if revision is None:
            raise AssetNotFoundError(AssetNotFoundError.code)
        return (revision,)
