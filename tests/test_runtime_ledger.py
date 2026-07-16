from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from runtime.ledger import RuntimeLedger
from runtime.models import RuntimeEvent, RuntimeEventType


def test_append_sequence_and_reopen(tmp_path):
    database = tmp_path / "ledger.db"
    with RuntimeLedger(database) as ledger:
        run_id = ledger.create_run(skill_name="demo", skill_version="1")
        ledger.append_event(
            RuntimeEvent(
                run_id=run_id,
                event_type=RuntimeEventType.PLAN_CREATED,
                skill_name="demo",
                skill_version="1",
            )
        )
        assert [event.sequence for event in ledger.list_events(run_id)] == [1, 2]
    with RuntimeLedger(database) as reopened:
        assert len(reopened.list_events(run_id)) == 2
        assert reopened.get_run(run_id)["status"] == "planned"


def test_idempotency_claim_distinguishes_created_owned_and_conflict(tmp_path):
    with RuntimeLedger(tmp_path / "ledger.db") as ledger:
        first = ledger.create_run(skill_name="demo", skill_version="1")
        second = ledger.create_run(skill_name="demo", skill_version="1")
        args = dict(key="k1", action_id="a_001", purpose="compensation")
        assert ledger.ensure_idempotency_claim(
            run_id=first, claimed_at="2026-01-01T00:00:00+00:00", **args
        ) == "created"
        assert ledger.ensure_idempotency_claim(
            run_id=first, claimed_at="2026-01-01T00:00:01+00:00", **args
        ) == "owned"
        assert ledger.ensure_idempotency_claim(
            run_id=second, claimed_at="2026-01-01T00:00:02+00:00", **args
        ) == "conflict"


def test_event_and_claim_tables_are_immutable(tmp_path):
    with RuntimeLedger(tmp_path / "ledger.db") as ledger:
        run_id = ledger.create_run(skill_name="demo", skill_version="1")
        ledger.claim_idempotency(
            key="immutable-key",
            run_id=run_id,
            action_id="a_001",
            purpose="primary",
            claimed_at="2026-01-01T00:00:00+00:00",
        )
        with pytest.raises(sqlite3.DatabaseError, match="append-only"):
            ledger.connection.execute("UPDATE runtime_events SET payload_json='{}'")
        with pytest.raises(sqlite3.DatabaseError, match="immutable"):
            ledger.connection.execute(
                "DELETE FROM runtime_idempotency_claims WHERE idempotency_key='immutable-key'"
            )


def test_claim_and_prepared_event_are_atomic_on_conflict(tmp_path):
    with RuntimeLedger(tmp_path / "ledger.db") as ledger:
        first = ledger.create_run(skill_name="demo", skill_version="1")
        second = ledger.create_run(skill_name="demo", skill_version="1")
        event1 = RuntimeEvent(
            run_id=first,
            event_type=RuntimeEventType.ACTION_PREPARED,
            skill_name="demo",
            skill_version="1",
            action_id="a_001",
            idempotency_key="same-key",
        )
        event2 = RuntimeEvent(
            run_id=second,
            event_type=RuntimeEventType.ACTION_PREPARED,
            skill_name="demo",
            skill_version="1",
            action_id="a_001",
            idempotency_key="same-key",
        )
        assert ledger.append_claimed_event(event1, purpose="primary") is not None
        assert ledger.append_claimed_event(event2, purpose="primary") is None
        assert [e.event_type for e in ledger.list_events(second)] == [
            RuntimeEventType.RUN_CREATED
        ]


def test_sql_migration_is_idempotent_and_enforces_append_only(tmp_path):
    migration = (Path(__file__).resolve().parents[1] / "migrations" / "001_runtime_ledger.sql").read_text(encoding="utf-8")
    connection = sqlite3.connect(tmp_path / "migration.db", isolation_level=None)
    try:
        connection.executescript(migration)
        connection.executescript(migration)
        basis_columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(runtime_execution_bases)"
            ).fetchall()
        }
        assert "governance_revision_id" in basis_columns
        hitl_columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(runtime_hitl_items)"
            ).fetchall()
        }
        assert "expires_at" in hitl_columns
        connection.execute(
            "INSERT INTO runtime_runs(run_id, skill_name, skill_version, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("run-1", "demo", "1", "created", "2026-01-01", "2026-01-01"),
        )
        connection.execute(
            "INSERT INTO runtime_events(event_id, run_id, sequence, schema_version, event_type, occurred_at, skill_name, skill_version, payload_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("event-1", "run-1", 1, "4.0.0", "run_created", "2026-01-01", "demo", "1", "{}"),
        )
        with pytest.raises(sqlite3.DatabaseError, match="append-only"):
            connection.execute("DELETE FROM runtime_events WHERE event_id='event-1'")
    finally:
        connection.close()


def test_read_only_ledger_does_not_create_or_mutate_database(tmp_path):
    missing = tmp_path / "missing.db"
    with pytest.raises(FileNotFoundError):
        RuntimeLedger(missing, read_only=True)
    assert not missing.exists()

    database = tmp_path / "runtime.db"
    with RuntimeLedger(database) as ledger:
        run_id = ledger.create_run(skill_name="demo", skill_version="1")
    before = database.read_bytes()
    with RuntimeLedger(database, read_only=True) as reader:
        assert reader.get_run(run_id)["run_id"] == run_id
    assert database.read_bytes() == before


def test_legacy_hitl_item_migrates_to_fail_closed_expired_state(tmp_path):
    database = tmp_path / "legacy-runtime.db"
    with sqlite3.connect(database) as connection:
        connection.executescript(
            """
            CREATE TABLE runtime_runs (
                run_id TEXT PRIMARY KEY,
                skill_name TEXT NOT NULL,
                skill_version TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE runtime_hitl_items (
                item_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                skill_id TEXT NOT NULL,
                action_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                status TEXT NOT NULL,
                basis_digest TEXT NOT NULL,
                request_summary_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            INSERT INTO runtime_runs VALUES (
                'run-legacy', 'demo', '1', 'awaiting_approval',
                '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00'
            );
            INSERT INTO runtime_hitl_items VALUES (
                'item-legacy', 'run-legacy', 'claude__skill__legacy', 'a_001',
                'action_approval', 'pending', 'basis', '{}',
                '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00'
            );
            """
        )

    with RuntimeLedger(database) as ledger:
        item = ledger.get_hitl_item("item-legacy")
        assert item["expires_at"] is None
        assert item["status"] == "expired"
        with pytest.raises(sqlite3.DatabaseError, match="projection update"):
            ledger.connection.execute(
                "UPDATE runtime_hitl_items SET expires_at=? WHERE item_id=?",
                ("2099-01-01T00:00:00+00:00", "item-legacy"),
            )


def test_ledger_rejects_event_identity_drift_and_duplicate_terminal(tmp_path):
    with RuntimeLedger(tmp_path / "runtime.db") as ledger:
        run_id = ledger.create_run(skill_name="demo", skill_version="1")
        with pytest.raises(ValueError, match="skill identity"):
            ledger.append_event(
                RuntimeEvent(
                    run_id=run_id,
                    event_type=RuntimeEventType.RUN_FAILED,
                    skill_name="different",
                    skill_version="1",
                )
            )
        event = RuntimeEvent(
            run_id=run_id,
            event_type=RuntimeEventType.RUN_FAILED,
            skill_name="demo",
            skill_version="1",
        )
        ledger.append_event(event)
        with pytest.raises(ValueError, match="invalid after outcome"):
            ledger.append_event(
                RuntimeEvent(
                    run_id=run_id,
                    event_type=RuntimeEventType.RUN_FAILED,
                    skill_name="demo",
                    skill_version="1",
                )
            )


def test_ledger_rejects_general_events_after_outcome_and_final_terminal(tmp_path):
    with RuntimeLedger(tmp_path / "runtime.db") as ledger:
        run_id = ledger.create_run(skill_name="demo", skill_version="1")
        ledger.append_event(
            RuntimeEvent(
                run_id=run_id,
                event_type=RuntimeEventType.RUN_FAILED,
                skill_name="demo",
                skill_version="1",
            )
        )
        ledger.append_event(
            RuntimeEvent(
                run_id=run_id,
                event_type=RuntimeEventType.RUN_CANCELLED,
                skill_name="demo",
                skill_version="1",
            )
        )
        with pytest.raises(ValueError, match="after final terminal"):
            ledger.append_event(
                RuntimeEvent(
                    run_id=run_id,
                    event_type=RuntimeEventType.PLAN_CREATED,
                    skill_name="demo",
                    skill_version="1",
                )
            )
