"""Regression tests for VectorStore write semantics."""

import numpy as np
import pytest

pytest.importorskip("sqlite_vec")

from vector_db.vector_store import VectorStore


def _skill(filename: str, title: str = "Fixture skill") -> dict:
    return {
        "_filename": filename,
        "meta": {
            "title": title,
            "description": "Fixture description",
            "skill_layer": "claude_skill",
            "schema_version": "2.4.0",
        },
        "decomposition": {
            "actions": [{"id": "a_001"}],
            "rules": [{"id": "r_001"}],
            "directives": [{"id": "d_001"}],
        },
    }


def _embedding(values: list[float]) -> np.ndarray:
    return np.array(values, dtype=np.float32)


def test_insert_skills_batch_inserts_rows_in_one_public_call(tmp_path):
    with VectorStore(tmp_path / "skills.db", dimension=4) as store:
        ids = store.insert_skills_batch(
            [_skill("one.json", "One"), _skill("two.json", "Two")],
            [_embedding([0.1, 0.2, 0.3, 0.4]), _embedding([0.4, 0.3, 0.2, 0.1])],
        )

        assert ids == [1, 2]
        assert store.get_statistics()["total_skills"] == 2


def test_insert_skills_batch_rejects_mismatched_inputs_without_partial_write(tmp_path):
    with VectorStore(tmp_path / "skills.db", dimension=4) as store:
        with pytest.raises(ValueError, match="same length"):
            store.insert_skills_batch(
                [_skill("one.json"), _skill("two.json")],
                [_embedding([0.1, 0.2, 0.3, 0.4])],
            )

        assert store.get_statistics()["total_skills"] == 0


def test_insert_skills_batch_rolls_back_when_embedding_validation_fails(tmp_path):
    with VectorStore(tmp_path / "skills.db", dimension=4) as store:
        with pytest.raises(ValueError, match="embedding must have shape"):
            store.insert_skills_batch(
                [_skill("one.json"), _skill("two.json")],
                [_embedding([0.1, 0.2, 0.3, 0.4]), _embedding([0.1, 0.2])],
            )

        assert store.get_statistics()["total_skills"] == 0
