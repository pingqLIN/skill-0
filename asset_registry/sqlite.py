"""SQLite-only connection, migration, and backup boundaries for P0 Asset work."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import sqlite3
from typing import Iterable, Literal


RUNNER_VERSION = "1.0.0"


@dataclass(frozen=True)
class SQLitePolicy:
    name: str
    foreign_keys: bool
    busy_timeout_ms: int
    journal_mode: str
    synchronous: str
    transaction_mode: Literal["DEFERRED", "IMMEDIATE"]


REGISTRY_POLICY = SQLitePolicy("registry", True, 2_000, "DELETE", "FULL", "IMMEDIATE")
INDEX_POLICY = SQLitePolicy("index", True, 2_000, "DELETE", "FULL", "IMMEDIATE")
RUNTIME_POLICY = SQLitePolicy("runtime", True, 2_000, "DELETE", "FULL", "IMMEDIATE")


@dataclass(frozen=True)
class Migration:
    migration_id: str
    sql: str
    checksum: str

    @classmethod
    def from_path(cls, path: Path) -> "Migration":
        sql = path.read_text(encoding="utf-8")
        checksum = "sha256:" + hashlib.sha256(sql.encode("utf-8")).hexdigest()
        return cls(path.stem, sql, checksum)


@dataclass(frozen=True)
class MigrationStatus:
    migration_id: str
    checksum: str
    state: Literal["pending", "applied", "checksum_drift"]


class MigrationError(RuntimeError):
    pass


class MigrationChecksumError(MigrationError):
    pass


class SQLiteContentionError(MigrationError):
    pass


class IndexSchemaError(MigrationError):
    pass


def connect_sqlite(
    path: Path,
    *,
    policy: SQLitePolicy,
    mode: Literal["read_only", "existing", "read_write", "maintenance"] = "read_only",
    check_same_thread: bool = True,
) -> sqlite3.Connection:
    """Open one explicit unit-of-work connection without implicit DDL."""

    resolved = path.resolve()
    if mode == "read_only":
        connection = sqlite3.connect(
            f"file:{resolved.as_posix()}?mode=ro",
            uri=True,
            timeout=policy.busy_timeout_ms / 1000,
            check_same_thread=check_same_thread,
        )
    elif mode == "existing":
        connection = sqlite3.connect(
            f"file:{resolved.as_posix()}?mode=rw",
            uri=True,
            timeout=policy.busy_timeout_ms / 1000,
            check_same_thread=check_same_thread,
        )
    else:
        connection = sqlite3.connect(
            resolved,
            timeout=policy.busy_timeout_ms / 1000,
            check_same_thread=check_same_thread,
        )
    connection.row_factory = sqlite3.Row
    connection.execute(f"PRAGMA busy_timeout={policy.busy_timeout_ms}")
    connection.execute(f"PRAGMA foreign_keys={'ON' if policy.foreign_keys else 'OFF'}")
    if mode != "read_only":
        connection.execute(f"PRAGMA journal_mode={policy.journal_mode}")
        connection.execute(f"PRAGMA synchronous={policy.synchronous}")
    return connection


def load_migrations(directory: Path) -> tuple[Migration, ...]:
    return tuple(Migration.from_path(path) for path in sorted(directory.glob("*.sql")))


def _applied_migrations(connection: sqlite3.Connection) -> dict[str, str]:
    exists = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
    ).fetchone()
    if not exists:
        return {}
    return {
        row["migration_id"]: row["checksum"]
        for row in connection.execute(
            "SELECT migration_id, checksum FROM schema_migrations"
        )
    }


def preview_migrations(
    connection: sqlite3.Connection, migrations: Iterable[Migration]
) -> tuple[MigrationStatus, ...]:
    applied = _applied_migrations(connection)
    statuses = []
    for migration in migrations:
        existing = applied.get(migration.migration_id)
        if existing is None:
            state = "pending"
        elif existing == migration.checksum:
            state = "applied"
        else:
            state = "checksum_drift"
        statuses.append(MigrationStatus(migration.migration_id, migration.checksum, state))
    return tuple(statuses)


def preflight_index_schema(
    connection: sqlite3.Connection,
    *,
    expected_dimension: int = 384,
) -> dict[str, object]:
    """Fail before migration when the target is not an existing legacy Index."""

    objects = {
        str(row["name"]): str(row["sql"] or "")
        for row in connection.execute(
            "SELECT name, sql FROM sqlite_master WHERE type IN ('table', 'view')"
        )
    }
    required = {"skills", "skill_embeddings"}
    missing = sorted(required - set(objects))
    if missing:
        raise IndexSchemaError("index_schema_missing:" + ",".join(missing))
    skill_columns = {
        str(row[1]) for row in connection.execute("PRAGMA table_info(skills)")
    }
    required_columns = {
        "id",
        "name",
        "filename",
        "description",
        "category",
        "version",
        "action_count",
        "rule_count",
        "directive_count",
        "raw_json",
    }
    missing_columns = sorted(required_columns - skill_columns)
    if missing_columns:
        raise IndexSchemaError(
            "index_skills_columns_missing:" + ",".join(missing_columns)
        )
    vector_sql = objects["skill_embeddings"].replace(" ", "").lower()
    expected_vector = f"embeddingfloat[{expected_dimension}]"
    if expected_vector not in vector_sql:
        raise IndexSchemaError(
            f"index_embedding_dimension_mismatch:expected={expected_dimension}"
        )
    return {
        "required_objects": sorted(required),
        "skills_columns": sorted(skill_columns),
        "embedding_dimension": expected_dimension,
    }


def _statements(sql: str) -> tuple[str, ...]:
    statements: list[str] = []
    buffer = ""
    for line in sql.splitlines(keepends=True):
        buffer += line
        if sqlite3.complete_statement(buffer):
            statement = buffer.strip()
            if statement:
                statements.append(statement)
            buffer = ""
    if buffer.strip():
        raise MigrationError("incomplete migration SQL")
    return tuple(statements)


def apply_migrations(
    connection: sqlite3.Connection, migrations: Iterable[Migration]
) -> tuple[str, ...]:
    """Apply ordered migrations and immutable checksums in one transaction each."""

    migrations = tuple(migrations)
    drift = [item for item in preview_migrations(connection, migrations) if item.state == "checksum_drift"]
    if drift:
        raise MigrationChecksumError(f"migration checksum drift: {drift[0].migration_id}")

    applied_ids: list[str] = []
    for migration in migrations:
        status = next(
            item for item in preview_migrations(connection, (migration,))
        )
        if status.state == "applied":
            continue
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    migration_id TEXT PRIMARY KEY,
                    checksum TEXT NOT NULL,
                    applied_at TEXT NOT NULL,
                    runner_version TEXT NOT NULL
                )
                """
            )
            for statement in _statements(migration.sql):
                connection.execute(statement)
            connection.execute(
                "INSERT INTO schema_migrations(migration_id, checksum, applied_at, runner_version) VALUES (?, ?, ?, ?)",
                (
                    migration.migration_id,
                    migration.checksum,
                    datetime.now(timezone.utc).isoformat(),
                    RUNNER_VERSION,
                ),
            )
            connection.commit()
        except sqlite3.OperationalError as exc:
            connection.rollback()
            if "locked" in str(exc).lower() or "busy" in str(exc).lower():
                raise SQLiteContentionError("sqlite_write_contention") from exc
            raise MigrationError(str(exc)) from exc
        except Exception:
            connection.rollback()
            raise
        applied_ids.append(migration.migration_id)
    return tuple(applied_ids)


def backup_database(source: Path, destination: Path) -> str:
    """Create and integrity-check a recoverable SQLite backup."""

    if destination.exists():
        raise FileExistsError(destination)
    with connect_sqlite(source, policy=INDEX_POLICY, mode="read_only") as source_db:
        with sqlite3.connect(destination) as backup_db:
            source_db.backup(backup_db)
    return verify_database(destination)


def verify_database(path: Path) -> str:
    with connect_sqlite(path, policy=INDEX_POLICY, mode="read_only") as connection:
        result = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
        if result != "ok":
            raise MigrationError(f"backup integrity check failed: {result}")
        connection.execute("SELECT name FROM sqlite_master LIMIT 1").fetchall()
    return result
