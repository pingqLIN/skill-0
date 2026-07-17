from __future__ import annotations

import json

import numpy as np
import pytest

from asset_registry.sqlite import apply_migrations, load_migrations
from vector_db.search import SemanticSearch


class CountingEmbedder:
    dimension = 384

    def __init__(self):
        self.embedded = 0
        self.fail = False

    def embed_skills(self, skills, show_progress=True):
        del show_progress
        if self.fail:
            raise RuntimeError("injected embedding failure")
        self.embedded += len(skills)
        return [np.full(self.dimension, index + 1, dtype=np.float32) for index, _ in enumerate(skills)]

    def embed_query(self, query):
        del query
        return np.zeros(self.dimension, dtype=np.float32)


def _write_skill(path, skill_id, *, parser_version="1.0.0"):
    document = {
        "meta": {
            "skill_id": skill_id,
            "name": path.stem,
            "title": path.stem,
            "description": "incremental index fixture",
            "skill_layer": "claude_skill",
            "schema_version": "2.4.0",
            "parsed_by": "incremental-test",
            "parser_version": parser_version,
        },
        "decomposition": {"actions": [], "rules": [], "directives": []},
    }
    path.write_text(json.dumps(document), encoding="utf-8")


@pytest.fixture
def incremental_search(root, tmp_path):
    parsed_dir = tmp_path / "parsed"
    parsed_dir.mkdir()
    _write_skill(parsed_dir / "one.json", "claude__skill__one")
    _write_skill(parsed_dir / "two.json", "claude__skill__two")
    search = SemanticSearch(tmp_path / "index.db", model_name="fixture-model")
    apply_migrations(search.store.conn, load_migrations(root / "migrations/index"))
    embedder = CountingEmbedder()
    search._embedder = embedder
    yield search, embedder, parsed_dir
    search.close()


def test_second_incremental_run_embeds_nothing(incremental_search):
    search, embedder, parsed_dir = incremental_search
    first = search.index_assets(parsed_dir, show_progress=False)
    second = search.index_assets(parsed_dir, show_progress=False)

    assert (first.changed, first.unchanged) == (2, 0)
    assert (second.changed, second.unchanged) == (0, 2)
    assert embedder.embedded == 2


def test_parser_and_representation_drift_select_only_affected_revisions(
    incremental_search,
):
    search, embedder, parsed_dir = incremental_search
    search.index_assets(parsed_dir, show_progress=False)
    _write_skill(
        parsed_dir / "one.json",
        "claude__skill__one",
        parser_version="1.1.0",
    )
    parser_drift = search.index_assets(parsed_dir, show_progress=False)
    representation_drift = search.index_assets(
        parsed_dir,
        representation_version="skill-text-v2",
        show_progress=False,
    )

    assert (parser_drift.changed, parser_drift.unchanged) == (1, 1)
    assert (representation_drift.changed, representation_drift.unchanged) == (2, 0)
    assert embedder.embedded == 5


def test_removed_source_is_pruned(incremental_search):
    search, _embedder, parsed_dir = incremental_search
    search.index_assets(parsed_dir, show_progress=False)
    (parsed_dir / "two.json").unlink()
    report = search.index_assets(parsed_dir, show_progress=False)

    assert report.removed == 1
    assert [row["source_path"] for row in search.store.get_index_state()] == ["one.json"]


def test_embedding_failure_preserves_existing_projection(incremental_search):
    search, embedder, parsed_dir = incremental_search
    search.index_assets(parsed_dir, show_progress=False)
    before = search.store.get_index_state()
    _write_skill(parsed_dir / "one.json", "claude__skill__one", parser_version="broken")
    embedder.fail = True

    with pytest.raises(RuntimeError, match="injected embedding failure"):
        search.index_assets(parsed_dir, show_progress=False)
    assert search.store.get_index_state() == before


def test_search_and_list_hot_paths_exclude_raw_json(incremental_search):
    search, _embedder, parsed_dir = incremental_search
    search.index_assets(parsed_dir, show_progress=False)
    results = search.search("fixture", limit=1)
    listed = search.store.get_all_skills()

    assert results and "raw_json" not in results[0]
    assert listed and all("raw_json" not in row for row in listed)
