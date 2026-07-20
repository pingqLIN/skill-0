from __future__ import annotations

import sys
import types

import pytest

from vector_db.embedder import SkillEmbedder
from vector_db.model_artifact import compute_model_artifact_digest


class _DummyModel:
    def get_embedding_dimension(self) -> int:
        return SkillEmbedder.DEFAULT_DIMENSION


def _install_sentence_transformer(monkeypatch, *, local_available: bool):
    calls: list[dict[str, object]] = []
    module = types.ModuleType("sentence_transformers")
    monkeypatch.setenv("SKILL0_DEVICE", "cpu")

    def sentence_transformer(model_name, **kwargs):
        calls.append({"model_name": model_name, **kwargs})
        if kwargs.get("local_files_only") and not local_available:
            raise OSError("local model unavailable")
        return _DummyModel()

    module.SentenceTransformer = sentence_transformer
    monkeypatch.setitem(sys.modules, "sentence_transformers", module)
    return calls


def _configure_production_model(monkeypatch, tmp_path):
    model_dir = tmp_path / "model"
    model_dir.mkdir()
    (model_dir / "config.json").write_text("{}", encoding="utf-8")
    monkeypatch.setenv("SKILL0_EMBEDDING_MODEL", str(model_dir))
    monkeypatch.setenv(
        "SKILL0_EMBEDDING_MODEL_ARTIFACT_DIGEST",
        compute_model_artifact_digest(model_dir),
    )
    return model_dir


def test_production_embedder_refuses_remote_model_fallback(monkeypatch, tmp_path):
    calls = _install_sentence_transformer(monkeypatch, local_available=False)
    monkeypatch.setenv("SKILL0_ENV", "production")
    model_dir = _configure_production_model(monkeypatch, tmp_path)

    with pytest.raises(
        RuntimeError,
        match="production embedding model must be available locally",
    ):
        SkillEmbedder(str(model_dir))

    assert calls == [
        {
            "model_name": str(model_dir),
            "device": "cpu",
            "local_files_only": True,
        }
    ]


def test_development_embedder_preserves_remote_fallback(monkeypatch):
    calls = _install_sentence_transformer(monkeypatch, local_available=False)
    monkeypatch.setenv("SKILL0_ENV", "development")

    embedder = SkillEmbedder("development-model")

    assert embedder.dimension == SkillEmbedder.DEFAULT_DIMENSION
    assert calls == [
        {
            "model_name": "development-model",
            "device": "cpu",
            "local_files_only": True,
        },
        {"model_name": "development-model", "device": "cpu"},
    ]


def test_production_embedder_accepts_available_local_model(monkeypatch, tmp_path):
    calls = _install_sentence_transformer(monkeypatch, local_available=True)
    monkeypatch.setenv("SKILL0_ENV", "production")
    model_dir = _configure_production_model(monkeypatch, tmp_path)

    embedder = SkillEmbedder(str(model_dir))

    assert embedder.dimension == SkillEmbedder.DEFAULT_DIMENSION
    assert calls == [
        {
            "model_name": str(model_dir),
            "device": "cpu",
            "local_files_only": True,
        }
    ]
