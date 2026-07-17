from __future__ import annotations

from contextlib import closing
from dataclasses import replace
import sqlite3

import pytest

from vector_db.vector_store import VectorStore
from vector_db.search import SemanticSearch

from asset_registry.sqlite import (
    INDEX_POLICY,
    MigrationError,
    MigrationChecksumError,
    SQLiteContentionError,
    apply_migrations,
    backup_database,
    connect_sqlite,
    database_digest,
    load_migrations,
    preview_migrations,
    restore_database_from_backup,
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


def test_backup_closes_destination_for_atomic_replace(tmp_path):
    source = tmp_path / "source.db"
    backup = tmp_path / "backup.db"
    replacement = tmp_path / "replacement.db"
    _legacy_index(source)

    assert backup_database(source, backup) == "ok"
    assert backup_database(source, replacement) == "ok"

    replacement.replace(backup)
    with sqlite3.connect(backup) as connection:
        assert connection.execute("SELECT filename FROM skills").fetchone()[0] == "fixture.json"


def test_restore_database_from_backup_atomically_replaces_expected_target(tmp_path):
    source = tmp_path / "source.db"
    backup = tmp_path / "backup.db"
    target = tmp_path / "target.db"
    staging = tmp_path / ".target.restore.staging.db"
    _legacy_index(source)
    assert backup_database(source, backup) == "ok"
    with closing(sqlite3.connect(target)) as connection:
        connection.execute("CREATE TABLE broken(value TEXT)")
        connection.execute("INSERT INTO broken VALUES ('broken')")
        connection.commit()
    broken_digest = database_digest(target)

    result = restore_database_from_backup(
        backup,
        target,
        staging,
        expected_target_digest=broken_digest,
    )

    assert result["target_digest_before"] == broken_digest
    assert result["restored_integrity"] == "ok"
    assert not staging.exists()
    with sqlite3.connect(target) as connection:
        assert connection.execute("SELECT filename FROM skills").fetchone()[0] == "fixture.json"


def test_restore_database_refuses_changed_target(tmp_path):
    source = tmp_path / "source.db"
    backup = tmp_path / "backup.db"
    target = tmp_path / "target.db"
    staging = tmp_path / ".target.restore.staging.db"
    _legacy_index(source)
    _legacy_index(target)
    assert backup_database(source, backup) == "ok"

    with pytest.raises(MigrationError, match="target digest mismatch"):
        restore_database_from_backup(
            backup,
            target,
            staging,
            expected_target_digest="sha256:" + "0" * 64,
        )

    assert target.is_file()
    assert not staging.exists()


def test_existing_index_mode_never_creates_missing_database(tmp_path):
    database = tmp_path / "missing.db"
    with pytest.raises(sqlite3.OperationalError):
        VectorStore(database, initialize_schema=False)
    assert not database.exists()


def test_production_index_unit_of_work_uses_named_connection_policy(tmp_path):
    search = SemanticSearch(tmp_path / "index.db", model_name="fixture")
    try:
        base_connection = search.store.conn
        with search.open_unit_of_work() as first:
            assert first.store.conn is not base_connection
            assert first.store.conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
            assert first.store.conn.execute("PRAGMA busy_timeout").fetchone()[0] == 2000
        with search.open_unit_of_work() as second:
            assert second.store.conn is not base_connection
            assert second.store.conn is not first.store.conn
    finally:
        search.close()
