from __future__ import annotations

import sys
import types

import pytest

from vector_db.embedder import SkillEmbedder


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


def test_production_embedder_refuses_remote_model_fallback(monkeypatch):
    calls = _install_sentence_transformer(monkeypatch, local_available=False)
    monkeypatch.setenv("SKILL0_ENV", "production")

    with pytest.raises(
        RuntimeError,
        match="production embedding model must be available locally",
    ):
        SkillEmbedder("operator-approved-model")

    assert calls == [
        {
            "model_name": "operator-approved-model",
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


def test_production_embedder_accepts_available_local_model(monkeypatch):
    calls = _install_sentence_transformer(monkeypatch, local_available=True)
    monkeypatch.setenv("SKILL0_ENV", "production")

    embedder = SkillEmbedder("operator-approved-model")

    assert embedder.dimension == SkillEmbedder.DEFAULT_DIMENSION
    assert calls == [
        {
            "model_name": "operator-approved-model",
            "device": "cpu",
            "local_files_only": True,
        }
    ]
