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
