from __future__ import annotations

from dataclasses import replace
import sqlite3

import pytest

from vector_db.vector_store import VectorStore

from asset_registry.sqlite import (
    INDEX_POLICY,
    MigrationChecksumError,
    SQLiteContentionError,
    apply_migrations,
    backup_database,
    connect_sqlite,
    load_migrations,
    preview_migrations,
    verify_database,
)


def _legacy_index(path):
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE skills (id INTEGER PRIMARY KEY, filename TEXT UNIQUE NOT NULL)"
        )
        connection.execute("INSERT INTO skills(filename) VALUES ('fixture.json')")


def test_fresh_current_and_legacy_fixtures_converge(root, tmp_path):
    migrations = load_migrations(root / "migrations/index")
    database = tmp_path / "legacy.db"
    _legacy_index(database)
    with connect_sqlite(database, policy=INDEX_POLICY, mode="maintenance") as connection:
        assert apply_migrations(connection, migrations) == ("001_asset_index_state",)
        assert apply_migrations(connection, migrations) == ()
        assert {item.state for item in preview_migrations(connection, migrations)} == {"applied"}
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    assert {"skills", "schema_migrations", "asset_index_state"} <= tables


def test_edited_migration_checksum_fails_closed(root, tmp_path):
    migrations = load_migrations(root / "migrations/index")
    database = tmp_path / "checksum.db"
    _legacy_index(database)
    with connect_sqlite(database, policy=INDEX_POLICY, mode="maintenance") as connection:
        apply_migrations(connection, migrations)
        edited = replace(migrations[0], checksum="sha256:" + "0" * 64)
        with pytest.raises(MigrationChecksumError):
            apply_migrations(connection, (edited,))


def test_two_writers_return_classified_contention(root, tmp_path):
    migrations = load_migrations(root / "migrations/index")
    database = tmp_path / "contention.db"
    _legacy_index(database)
    fast_policy = replace(INDEX_POLICY, busy_timeout_ms=10)
    with connect_sqlite(database, policy=fast_policy, mode="maintenance") as first:
        with connect_sqlite(database, policy=fast_policy, mode="maintenance") as second:
            first.execute("BEGIN IMMEDIATE")
            with pytest.raises(SQLiteContentionError, match="sqlite_write_contention"):
                apply_migrations(second, migrations)
            first.rollback()


def test_read_only_preview_does_not_create_migration_tables(root, tmp_path):
    migrations = load_migrations(root / "migrations/index")
    database = tmp_path / "preview.db"
    _legacy_index(database)
    with connect_sqlite(database, policy=INDEX_POLICY, mode="read_only") as connection:
        assert {item.state for item in preview_migrations(connection, migrations)} == {"pending"}
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT 1 FROM sqlite_master WHERE name='schema_migrations'"
        ).fetchone() is None


def test_backup_is_integrity_checked_and_readable(tmp_path):
    source = tmp_path / "source.db"
    backup = tmp_path / "backup.db"
    _legacy_index(source)
    assert backup_database(source, backup) == "ok"
    assert verify_database(backup) == "ok"
    with connect_sqlite(backup, policy=INDEX_POLICY, mode="read_only") as connection:
        assert connection.execute("SELECT filename FROM skills").fetchone()[0] == "fixture.json"


def test_existing_index_mode_never_creates_missing_database(tmp_path):
    database = tmp_path / "missing.db"
    with pytest.raises(sqlite3.OperationalError):
        VectorStore(database, initialize_schema=False)
    assert not database.exists()
