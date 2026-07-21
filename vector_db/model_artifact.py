"""Fail-closed authority checks for production embedding model artifacts."""

from __future__ import annotations

import hashlib
import hmac
import os
from pathlib import Path


MODEL_ENV = "SKILL0_EMBEDDING_MODEL"
DIGEST_ENV = "SKILL0_EMBEDDING_MODEL_ARTIFACT_DIGEST"
_VERSION_ENV = "SKILL0_EMBEDDING_MODEL_VERSION"
_DIGEST_PREFIX = "sha256:"
_DIGEST_LENGTH = len(_DIGEST_PREFIX) + 64
_MANIFEST_VERSION = b"skill0-embedding-artifact-v1\0"
_PRODUCTION_VALUES = frozenset({"production", "prod"})


class EmbeddingModelArtifactError(RuntimeError):
    """A production model artifact did not meet its authority contract."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _is_production(env_value: str | None) -> bool:
    return (env_value or "").strip().lower() in _PRODUCTION_VALUES


def _normalise_expected_digest(expected_digest: str | None) -> str:
    if not expected_digest:
        raise EmbeddingModelArtifactError("embedding_model_artifact_digest_required")
    if (
        len(expected_digest) != _DIGEST_LENGTH
        or not expected_digest.startswith(_DIGEST_PREFIX)
        or any(character not in "0123456789abcdef" for character in expected_digest[7:])
    ):
        raise EmbeddingModelArtifactError("embedding_model_artifact_digest_invalid")
    return expected_digest


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise EmbeddingModelArtifactError("embedding_model_artifact_unreadable") from exc
    return digest.hexdigest()


def _write_field(manifest: "hashlib._Hash", value: bytes) -> None:
    """Write a length-framed manifest field so filenames cannot collide."""
    manifest.update(len(value).to_bytes(8, "big"))
    manifest.update(value)


def compute_model_artifact_digest(path: str | Path) -> str:
    """Return the canonical digest of a materialized, symlink-free model tree."""
    root = Path(path)
    if not root.is_absolute():
        raise EmbeddingModelArtifactError("embedding_model_artifact_path_not_absolute")
    if root.is_symlink():
        raise EmbeddingModelArtifactError("embedding_model_artifact_symlink")
    if not root.exists():
        raise EmbeddingModelArtifactError("embedding_model_artifact_path_missing")
    if not root.is_dir():
        raise EmbeddingModelArtifactError("embedding_model_artifact_path_not_directory")

    files: list[Path] = []
    try:
        for candidate in root.rglob("*"):
            if candidate.is_symlink():
                raise EmbeddingModelArtifactError("embedding_model_artifact_symlink")
            if candidate.is_dir():
                continue
            if not candidate.is_file():
                raise EmbeddingModelArtifactError("embedding_model_artifact_non_regular_file")
            files.append(candidate)
    except OSError as exc:
        raise EmbeddingModelArtifactError("embedding_model_artifact_unreadable") from exc

    if not files:
        raise EmbeddingModelArtifactError("embedding_model_artifact_tree_empty")

    manifest = hashlib.sha256(_MANIFEST_VERSION)
    for candidate in sorted(files, key=lambda item: item.relative_to(root).as_posix()):
        relative = candidate.relative_to(root).as_posix().encode("utf-8")
        try:
            size = candidate.stat().st_size
        except OSError as exc:
            raise EmbeddingModelArtifactError("embedding_model_artifact_unreadable") from exc
        manifest.update(b"F")
        _write_field(manifest, relative)
        _write_field(manifest, str(size).encode("ascii"))
        _write_field(manifest, _file_digest(candidate).encode("ascii"))
    return _DIGEST_PREFIX + manifest.hexdigest()


def verify_production_model_artifact(
    model_name: str,
    expected_digest: str | None = None,
) -> str:
    """Verify the configured artifact and return its canonical digest.

    This function intentionally accepts only a materialized absolute directory;
    production must not authorize a remote model identifier or cache alias.
    """
    expected = _normalise_expected_digest(
        expected_digest if expected_digest is not None else os.environ.get(DIGEST_ENV)
    )
    actual = compute_model_artifact_digest(model_name)
    if not hmac.compare_digest(actual, expected):
        raise EmbeddingModelArtifactError("embedding_model_artifact_digest_mismatch")
    return actual


def production_model_artifact_issue(
    env_value: str | None,
    model_name: str | None,
    expected_digest: str | None,
) -> str | None:
    """Return a stable redacted issue code, or ``None`` outside production."""
    if not _is_production(env_value):
        return None
    if os.environ.get(_VERSION_ENV):
        return "embedding_model_version_override_forbidden"
    if not model_name:
        return "embedding_model_artifact_path_required"
    try:
        verify_production_model_artifact(model_name, expected_digest)
    except EmbeddingModelArtifactError as exc:
        return exc.code
    return None
