"""Transaction coverage for VectorStore writes."""

import pytest

sqlite_vec = pytest.importorskip("sqlite_vec")

import numpy as np

from vector_db.vector_store import VectorStore


def _skill(filename: str, title: str) -> dict:
    return {
        "_filename": filename,
        "meta": {
            "title": title,
            "description": f"{title} description",
            "skill_layer": "claude_skill",
            "schema_version": "2.4.0",
        },
        "decomposition": {
            "actions": [{"id": "a_001"}],
            "rules": [],
            "directives": [],
        },
    }


def _embedding(*values: float) -> np.ndarray:
    return np.array(values, dtype=np.float32)


def test_insert_skills_batch_commits_rows_and_embeddings(tmp_path):
    with VectorStore(tmp_path / "skills.db", dimension=3) as store:
        ids = store.insert_skills_batch(
            [_skill("one.json", "One"), _skill("two.json", "Two")],
            [_embedding(1.0, 0.0, 0.0), _embedding(0.0, 1.0, 0.0)],
        )

        rows = store.get_all_skills()

        assert ids == [1, 2]
        assert [row["filename"] for row in rows] == ["one.json", "two.json"]
        assert store.get_embedding(ids[0]).shape == (3,)
        assert store.get_embedding(ids[1]).shape == (3,)


def test_insert_skills_batch_rolls_back_partial_failure(tmp_path):
    with VectorStore(tmp_path / "skills.db", dimension=3) as store:
        with pytest.raises(ValueError, match="embedding must have shape"):
            store.insert_skills_batch(
                [_skill("one.json", "One"), _skill("two.json", "Two")],
                [_embedding(1.0, 0.0, 0.0), _embedding(0.0, 1.0)],
            )

        assert store.get_all_skills() == []
        embedding_count = store.conn.execute(
            "SELECT COUNT(*) FROM skill_embeddings"
        ).fetchone()[0]
        assert embedding_count == 0


def test_insert_skill_rolls_back_partial_failure(tmp_path):
    with VectorStore(tmp_path / "skills.db", dimension=3) as store:
        with pytest.raises(ValueError, match="embedding must have shape"):
            store.insert_skill(_skill("one.json", "One"), _embedding(1.0, 0.0))

        assert store.get_all_skills() == []
