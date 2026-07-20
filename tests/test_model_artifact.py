from __future__ import annotations

import sys
import pytest

from vector_db.embedder import SkillEmbedder
from vector_db.model_artifact import (
    DIGEST_ENV,
    MODEL_ENV,
    EmbeddingModelArtifactError,
    compute_model_artifact_digest,
    production_model_artifact_issue,
    verify_production_model_artifact,
)
from vector_db.search import SemanticSearch


def _model_tree(tmp_path):
    model = tmp_path / "model"
    model.mkdir(parents=True)
    (model / "config.json").write_text('{"model_type":"fixture"}', encoding="utf-8")
    weights = model / "weights"
    weights.mkdir()
    (weights / "model.bin").write_bytes(b"fixture-weights")
    return model


def test_model_tree_digest_is_deterministic_and_versioned(tmp_path):
    first = _model_tree(tmp_path / "first")
    second = _model_tree(tmp_path / "second")

    assert compute_model_artifact_digest(first) == compute_model_artifact_digest(second)
    assert compute_model_artifact_digest(first).startswith("sha256:")


def test_model_tree_digest_changes_when_file_contents_change(tmp_path):
    model = _model_tree(tmp_path)
    before = compute_model_artifact_digest(model)
    (model / "weights" / "model.bin").write_bytes(b"replacement-weights")

    assert compute_model_artifact_digest(model) != before


@pytest.mark.parametrize(
    ("prepare", "code"),
    [
        (lambda root: root, "embedding_model_artifact_tree_empty"),
        (
            lambda root: (root / "link").symlink_to(root / "outside"),
            "embedding_model_artifact_symlink",
        ),
    ],
)
def test_model_tree_rejects_unsafe_shapes(tmp_path, prepare, code):
    root = tmp_path / "model"
    root.mkdir()
    prepare(root)

    with pytest.raises(EmbeddingModelArtifactError, match=code):
        compute_model_artifact_digest(root)


def test_production_verifier_requires_matching_lowercase_digest(tmp_path):
    model = _model_tree(tmp_path)
    digest = compute_model_artifact_digest(model)

    assert verify_production_model_artifact(str(model), digest) == digest
    with pytest.raises(EmbeddingModelArtifactError, match="embedding_model_artifact_digest_invalid"):
        verify_production_model_artifact(str(model), digest.upper())
    with pytest.raises(EmbeddingModelArtifactError, match="embedding_model_artifact_digest_mismatch"):
        verify_production_model_artifact(str(model), "sha256:" + "0" * 64)


def test_production_issue_is_redacted_and_forbids_version_override(monkeypatch, tmp_path):
    model = _model_tree(tmp_path)
    digest = compute_model_artifact_digest(model)
    monkeypatch.setenv("SKILL0_EMBEDDING_MODEL_VERSION", "untrusted-label")

    assert production_model_artifact_issue("production", str(model), digest) == (
        "embedding_model_version_override_forbidden"
    )
    monkeypatch.delenv("SKILL0_EMBEDDING_MODEL_VERSION")
    assert production_model_artifact_issue("development", str(model), digest) is None
    assert production_model_artifact_issue("production", str(model), digest) is None


def test_embedder_rejects_unapproved_model_before_transformer_import(monkeypatch, tmp_path):
    model = _model_tree(tmp_path)
    monkeypatch.setenv("SKILL0_ENV", "production")
    monkeypatch.setenv(MODEL_ENV, str(model))
    monkeypatch.setenv(DIGEST_ENV, "sha256:" + "0" * 64)
    monkeypatch.delitem(sys.modules, "sentence_transformers", raising=False)

    with pytest.raises(EmbeddingModelArtifactError, match="embedding_model_artifact_digest_mismatch"):
        SkillEmbedder(str(model))
    assert "sentence_transformers" not in sys.modules


def test_production_identity_uses_approved_artifact_not_version_override(monkeypatch, tmp_path):
    model = _model_tree(tmp_path)
    digest = compute_model_artifact_digest(model)
    monkeypatch.setenv("SKILL0_ENV", "production")
    monkeypatch.setenv(MODEL_ENV, str(model))
    monkeypatch.setenv(DIGEST_ENV, digest)
    monkeypatch.setenv("SKILL0_EMBEDDING_MODEL_VERSION", "untrusted-label")
    search = SemanticSearch(tmp_path / "index.db", model_name=str(model))
    try:
        with pytest.raises(EmbeddingModelArtifactError, match="embedding_model_version_override_forbidden"):
            search._embedding_identity()
    finally:
        search.close()
