from __future__ import annotations

import sqlite3

import pytest

from asset_registry.sqlite import IndexSchemaError, apply_migrations, load_migrations
from tools.runtime_asset_index_maintenance import (
    apply_index_migrations,
    index_twice,
    inspect_index,
)
from vector_db.search import IndexReport
from vector_db.vector_store import VectorStore


def test_preflight_rejects_non_index_sample_database(root, tmp_path):
    database = tmp_path / "sample.db"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE sample(id INTEGER PRIMARY KEY)")
    with pytest.raises(IndexSchemaError, match="index_schema_missing"):
        inspect_index(database, root / "migrations/index")


def test_apply_requires_preflight_and_creates_verified_backup(root, tmp_path):
    database = tmp_path / "index.db"
    backup = tmp_path / "backup.db"
    with VectorStore(database):
        pass
    result = apply_index_migrations(
        database,
        root / "migrations/index",
        backup,
    )
    assert result["applied"] == ["001_asset_index_state"]
    assert result["backup"]["integrity"] == "ok"
    assert backup.is_file()
    assert result["after"]["migrations"][0]["state"] == "applied"


def test_index_twice_requires_second_run_to_be_noop(root, tmp_path, monkeypatch):
    database = tmp_path / "index.db"
    parsed = tmp_path / "parsed"
    parsed.mkdir()
    with VectorStore(database) as store:
        apply_migrations(store.conn, load_migrations(root / "migrations/index"))

    calls = []

    class FakeSearch:
        def __init__(self, *args, **kwargs):
            calls.append((args, kwargs))

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def index_assets(self, parsed_dir, show_progress=False):
            del parsed_dir, show_progress
            return IndexReport(total=0, changed=0, unchanged=0, removed=0)

        def _embedding_identity(self):
            return "fixture-model", "fixture-v1"

        def search_assets(self, query, limit=5):
            assert query == "document processing"
            assert limit == 5
            return []

    monkeypatch.setattr(
        "tools.runtime_asset_index_maintenance.SemanticSearch", FakeSearch
    )
    refused = index_twice(
        index_db=database,
        parsed_dir=parsed,
        governance_db=tmp_path / "missing-governance.db",
        migration_dir=root / "migrations/index",
        model_version="fixture-v1",
    )
    assert refused["accepted"] is False
    assert refused["stage"] == "preflight"
    assert len(calls) == 0

    result = index_twice(
        index_db=database,
        parsed_dir=parsed,
        governance_db=tmp_path / "missing-governance.db",
        migration_dir=root / "migrations/index",
        model_version="fixture-v1",
        allow_nonhealthy_evidence=True,
        smoke_query="document processing",
    )
    assert len(calls) == 1
    assert result["second"]["changed"] == 0
    assert result["doctor"]["state"] == "authority-missing"
    assert result["accepted"] is False
    assert result["rehearsal_only"] is True
    assert result["inspection"]["integrity"] == "ok"
    assert result["model_identity"] == {
        "model_id": "fixture-model",
        "model_version": "fixture-v1",
    }
    assert result["search_smoke"] == {
        "query": "document processing",
        "results": [],
    }
