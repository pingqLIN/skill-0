from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4

from .models import RunStatus, RuntimeEvent, RuntimeEventType


_STATUS_BY_EVENT: dict[RuntimeEventType, RunStatus] = {
    RuntimeEventType.RUN_CREATED: RunStatus.CREATED,
    RuntimeEventType.PLAN_CREATED: RunStatus.PLANNED,
    RuntimeEventType.PREFLIGHT_PASSED: RunStatus.PREFLIGHT,
    RuntimeEventType.POLICY_ALLOWED: RunStatus.READY,
    RuntimeEventType.POLICY_DENIED: RunStatus.DENIED,
    RuntimeEventType.APPROVAL_REQUIRED: RunStatus.AWAITING_APPROVAL,
    RuntimeEventType.APPROVAL_GRANTED: RunStatus.READY,
    RuntimeEventType.ACTION_PREPARED: RunStatus.READY,
    RuntimeEventType.ACTION_STARTED: RunStatus.RUNNING,
    RuntimeEventType.ACTION_OUTCOME_UNKNOWN: RunStatus.RECONCILIATION_REQUIRED,
    RuntimeEventType.VALIDATION_SUCCEEDED: RunStatus.VALIDATING,
    RuntimeEventType.VALIDATION_FAILED: RunStatus.FAILED,
    RuntimeEventType.ACTION_FAILED: RunStatus.FAILED,
    RuntimeEventType.COMPENSATION_QUEUED: RunStatus.RECOVERY_PENDING,
    RuntimeEventType.COMPENSATION_STARTED: RunStatus.COMPENSATING,
    RuntimeEventType.COMPENSATION_RETRY_SCHEDULED: RunStatus.COMPENSATING,
    RuntimeEventType.COMPENSATION_SUCCEEDED: RunStatus.COMPENSATING,
    RuntimeEventType.COMPENSATION_FAILED: RunStatus.COMPENSATING,
    RuntimeEventType.RECONCILIATION_REQUIRED: RunStatus.RECONCILIATION_REQUIRED,
    RuntimeEventType.RUN_SUCCEEDED: RunStatus.SUCCEEDED,
    RuntimeEventType.RUN_FAILED: RunStatus.FAILED,
    RuntimeEventType.RUN_COMPENSATED: RunStatus.COMPENSATED,
    RuntimeEventType.RUN_RECOVERY_FAILED: RunStatus.RECOVERY_FAILED,
    RuntimeEventType.RUN_SUSPENDED: RunStatus.HITL_REQUIRED,
    RuntimeEventType.RUN_CANCELLED: RunStatus.CANCELLED,
}

_UNIQUE_TERMINAL_EVENTS = {
    RuntimeEventType.RUN_SUCCEEDED,
    RuntimeEventType.RUN_FAILED,
    RuntimeEventType.RUN_COMPENSATED,
    RuntimeEventType.RUN_RECOVERY_FAILED,
    RuntimeEventType.RUN_CANCELLED,
}

_OUTCOME_EVENTS = {
    RuntimeEventType.RUN_SUCCEEDED,
    RuntimeEventType.RUN_FAILED,
}
_FINAL_TERMINAL_EVENTS = {
    RuntimeEventType.RUN_COMPENSATED,
    RuntimeEventType.RUN_CANCELLED,
}
_ALLOWED_AFTER_OUTCOME = {
    RuntimeEventType.COMPENSATION_QUEUED,
    RuntimeEventType.COMPENSATION_STARTED,
    RuntimeEventType.COMPENSATION_RETRY_SCHEDULED,
    RuntimeEventType.COMPENSATION_SUCCEEDED,
    RuntimeEventType.COMPENSATION_FAILED,
    RuntimeEventType.RECONCILIATION_REQUIRED,
    RuntimeEventType.APPROVAL_REQUIRED,
    RuntimeEventType.APPROVAL_GRANTED,
    RuntimeEventType.RUN_COMPENSATED,
    RuntimeEventType.RUN_RECOVERY_FAILED,
    RuntimeEventType.RUN_SUSPENDED,
    RuntimeEventType.RUN_CANCELLED,
}


def projected_status_for_event(event_type: RuntimeEventType) -> RunStatus | None:
    return _STATUS_BY_EVENT.get(event_type)


def validate_event_type_sequence(event_types: Iterable[RuntimeEventType]) -> None:
    outcome: RuntimeEventType | None = None
    final_terminal: RuntimeEventType | None = None
    for event_type in event_types:
        if final_terminal is not None:
            raise ValueError(f"event appended after final terminal {final_terminal.value}")
        if outcome is not None and event_type not in _ALLOWED_AFTER_OUTCOME:
            raise ValueError(f"event {event_type.value} is invalid after outcome {outcome.value}")
        if event_type in _OUTCOME_EVENTS:
            if outcome is not None:
                raise ValueError("multiple runtime outcome events are not allowed")
            outcome = event_type
        if event_type in _FINAL_TERMINAL_EVENTS:
            final_terminal = event_type


class RuntimeLedger:
    """SQLite-backed append-only event ledger.

    `journal_mode=DELETE` plus `synchronous=FULL` is the conservative P0
    default. WAL remains opt-in until the deployment validates its SQLite
    version and backup/recovery procedure.
    """

    def __init__(
        self,
        path: str | Path,
        *,
        journal_mode: str = "DELETE",
        read_only: bool = False,
    ) -> None:
        mode = journal_mode.upper()
        if mode not in {"DELETE", "WAL"}:
            raise ValueError("journal_mode must be DELETE or WAL")
        self.path = Path(path)
        self.read_only = read_only
        if read_only:
            if not self.path.exists():
                raise FileNotFoundError(self.path)
            uri = f"{self.path.resolve().as_uri()}?mode=ro"
            self.connection = sqlite3.connect(
                uri,
                uri=True,
                timeout=30.0,
                isolation_level=None,
            )
        else:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.connection = sqlite3.connect(
                self.path,
                timeout=30.0,
                isolation_level=None,
            )
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys=ON")
        if read_only:
            self.connection.execute("PRAGMA query_only=ON")
        else:
            self.connection.execute("PRAGMA synchronous=FULL")
            self.connection.execute(f"PRAGMA journal_mode={mode}")
            self._migrate()

    @property
    def sqlite_version(self) -> str:
        return sqlite3.sqlite_version

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "RuntimeLedger":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    def _migrate(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS runtime_runs (
                run_id TEXT PRIMARY KEY,
                skill_name TEXT NOT NULL,
                skill_version TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS runtime_events (
                event_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL REFERENCES runtime_runs(run_id) ON DELETE RESTRICT,
                sequence INTEGER NOT NULL,
                schema_version TEXT NOT NULL,
                event_type TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                skill_name TEXT NOT NULL,
                skill_version TEXT NOT NULL,
                action_id TEXT,
                idempotency_key TEXT,
                external_resource_id TEXT,
                payload_json TEXT NOT NULL,
                UNIQUE(run_id, sequence)
            );
            CREATE INDEX IF NOT EXISTS idx_runtime_events_run
                ON runtime_events(run_id, sequence);
            CREATE INDEX IF NOT EXISTS idx_runtime_events_type
                ON runtime_events(event_type);
            CREATE INDEX IF NOT EXISTS idx_runtime_events_idempotency
                ON runtime_events(idempotency_key)
                WHERE idempotency_key IS NOT NULL;

            CREATE TABLE IF NOT EXISTS runtime_idempotency_claims (
                idempotency_key TEXT PRIMARY KEY,
                run_id TEXT NOT NULL REFERENCES runtime_runs(run_id) ON DELETE RESTRICT,
                action_id TEXT NOT NULL,
                purpose TEXT NOT NULL,
                claimed_at TEXT NOT NULL
            );

            CREATE TRIGGER IF NOT EXISTS trg_runtime_events_no_update
            BEFORE UPDATE ON runtime_events
            BEGIN
                SELECT RAISE(ABORT, 'runtime_events is append-only');
            END;

            CREATE TRIGGER IF NOT EXISTS trg_runtime_events_no_delete
            BEFORE DELETE ON runtime_events
            BEGIN
                SELECT RAISE(ABORT, 'runtime_events is append-only');
            END;

            CREATE TRIGGER IF NOT EXISTS trg_runtime_claims_no_update
            BEFORE UPDATE ON runtime_idempotency_claims
            BEGIN
                SELECT RAISE(ABORT, 'runtime_idempotency_claims is immutable');
            END;

            CREATE TRIGGER IF NOT EXISTS trg_runtime_claims_no_delete
            BEFORE DELETE ON runtime_idempotency_claims
            BEGIN
                SELECT RAISE(ABORT, 'runtime_idempotency_claims is immutable');
            END;
            """
        )

    def create_run(self, *, skill_name: str, skill_version: str, run_id: str | None = None) -> str:
        rid = run_id or str(uuid4())
        event = RuntimeEvent(
            run_id=rid,
            event_type=RuntimeEventType.RUN_CREATED,
            skill_name=skill_name,
            skill_version=skill_version,
        )
        cur = self.connection.cursor()
        try:
            cur.execute("BEGIN IMMEDIATE")
            cur.execute(
                "INSERT INTO runtime_runs(run_id, skill_name, skill_version, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (rid, skill_name, skill_version, RunStatus.CREATED.value, event.occurred_at, event.occurred_at),
            )
            self._insert_event(cur, event, sequence=1)
            cur.execute("COMMIT")
        except Exception:
            if self.connection.in_transaction:
                cur.execute("ROLLBACK")
            raise
        return rid

    def append_event(self, event: RuntimeEvent) -> RuntimeEvent:
        cur = self.connection.cursor()
        try:
            cur.execute("BEGIN IMMEDIATE")
            stored = self._append_event_in_transaction(cur, event)
            cur.execute("COMMIT")
            return stored
        except Exception:
            if self.connection.in_transaction:
                cur.execute("ROLLBACK")
            raise

    @staticmethod
    def _claim_in_transaction(
        cur: sqlite3.Cursor,
        *,
        key: str,
        run_id: str,
        action_id: str,
        purpose: str,
        claimed_at: str,
    ) -> str:
        existing = cur.execute(
            "SELECT run_id, action_id, purpose FROM runtime_idempotency_claims WHERE idempotency_key=?",
            (key,),
        ).fetchone()
        owner = (run_id, action_id, purpose)
        if existing is None:
            cur.execute(
                "INSERT INTO runtime_idempotency_claims(idempotency_key, run_id, action_id, purpose, claimed_at) VALUES (?, ?, ?, ?, ?)",
                (key, run_id, action_id, purpose, claimed_at),
            )
            return "created"
        if (existing["run_id"], existing["action_id"], existing["purpose"]) == owner:
            return "owned"
        return "conflict"

    def ensure_idempotency_claim(
        self,
        *,
        key: str,
        run_id: str,
        action_id: str,
        purpose: str,
        claimed_at: str,
    ) -> str:
        """Return `created`, `owned`, or `conflict` for an idempotency claim."""
        cur = self.connection.cursor()
        try:
            cur.execute("BEGIN IMMEDIATE")
            result = self._claim_in_transaction(
                cur,
                key=key,
                run_id=run_id,
                action_id=action_id,
                purpose=purpose,
                claimed_at=claimed_at,
            )
            cur.execute("COMMIT")
            return result
        except Exception:
            if self.connection.in_transaction:
                cur.execute("ROLLBACK")
            raise

    def claim_idempotency(
        self,
        *,
        key: str,
        run_id: str,
        action_id: str,
        purpose: str,
        claimed_at: str,
    ) -> bool:
        return (
            self.ensure_idempotency_claim(
                key=key,
                run_id=run_id,
                action_id=action_id,
                purpose=purpose,
                claimed_at=claimed_at,
            )
            != "conflict"
        )

    def append_claimed_event(self, event: RuntimeEvent, *, purpose: str) -> RuntimeEvent | None:
        """Atomically claim an idempotency key and append its journal event.

        Same-owner retries are allowed. Claims owned by a different run,
        action, or purpose are rejected without appending an event.
        """
        if not event.idempotency_key:
            raise ValueError("append_claimed_event requires event.idempotency_key")
        if not event.action_id:
            raise ValueError("append_claimed_event requires event.action_id")
        cur = self.connection.cursor()
        try:
            cur.execute("BEGIN IMMEDIATE")
            claim = self._claim_in_transaction(
                cur,
                key=event.idempotency_key,
                run_id=event.run_id,
                action_id=event.action_id,
                purpose=purpose,
                claimed_at=event.occurred_at,
            )
            if claim == "conflict":
                cur.execute("ROLLBACK")
                return None
            stored = self._append_event_in_transaction(cur, event)
            cur.execute("COMMIT")
            return stored
        except Exception:
            if self.connection.in_transaction:
                cur.execute("ROLLBACK")
            raise

    def _append_event_in_transaction(self, cur: sqlite3.Cursor, event: RuntimeEvent) -> RuntimeEvent:
        run = cur.execute(
            "SELECT run_id, skill_name, skill_version FROM runtime_runs WHERE run_id=?",
            (event.run_id,),
        ).fetchone()
        if run is None:
            raise KeyError(f"Unknown run_id: {event.run_id}")
        if event.skill_name != run["skill_name"] or event.skill_version != run["skill_version"]:
            raise ValueError("runtime event skill identity does not match its run")
        if event.schema_version != "4.0.0":
            raise ValueError("unsupported runtime event schema version")
        try:
            datetime.fromisoformat(event.occurred_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("invalid runtime event timestamp") from exc
        existing_event_types = [
            RuntimeEventType(row[0])
            for row in cur.execute(
                "SELECT event_type FROM runtime_events WHERE run_id=? ORDER BY sequence",
                (event.run_id,),
            ).fetchall()
        ]
        validate_event_type_sequence([*existing_event_types, event.event_type])
        if event.event_type in _UNIQUE_TERMINAL_EVENTS:
            duplicate = cur.execute(
                "SELECT 1 FROM runtime_events WHERE run_id=? AND event_type=? LIMIT 1",
                (event.run_id, event.event_type.value),
            ).fetchone()
            if duplicate is not None:
                raise ValueError("duplicate runtime terminal event")
        sequence = int(
            cur.execute(
                "SELECT COALESCE(MAX(sequence), 0) + 1 FROM runtime_events WHERE run_id=?",
                (event.run_id,),
            ).fetchone()[0]
        )
        stored = RuntimeEvent(
            event_id=event.event_id,
            run_id=event.run_id,
            sequence=sequence,
            schema_version=event.schema_version,
            event_type=event.event_type,
            occurred_at=event.occurred_at,
            skill_name=event.skill_name,
            skill_version=event.skill_version,
            action_id=event.action_id,
            idempotency_key=event.idempotency_key,
            external_resource_id=event.external_resource_id,
            payload=event.payload,
        )
        self._insert_event(cur, stored, sequence=sequence)
        status = _STATUS_BY_EVENT.get(event.event_type)
        if status is not None:
            cur.execute(
                "UPDATE runtime_runs SET status=?, updated_at=? WHERE run_id=?",
                (status.value, event.occurred_at, event.run_id),
            )
        return stored

    def _insert_event(self, cur: sqlite3.Cursor, event: RuntimeEvent, *, sequence: int) -> None:
        cur.execute(
            """INSERT INTO runtime_events(
                event_id, run_id, sequence, schema_version, event_type, occurred_at,
                skill_name, skill_version, action_id, idempotency_key,
                external_resource_id, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                event.event_id,
                event.run_id,
                sequence,
                event.schema_version,
                event.event_type.value,
                event.occurred_at,
                event.skill_name,
                event.skill_version,
                event.action_id,
                event.idempotency_key,
                event.external_resource_id,
                json.dumps(event.payload, ensure_ascii=False, sort_keys=True),
            ),
        )

    def get_run(self, run_id: str) -> dict[str, Any]:
        row = self.connection.execute("SELECT * FROM runtime_runs WHERE run_id=?", (run_id,)).fetchone()
        if row is None:
            raise KeyError(run_id)
        return dict(row)

    def get_idempotency_claim(self, key: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT * FROM runtime_idempotency_claims WHERE idempotency_key=?", (key,)
        ).fetchone()
        return dict(row) if row is not None else None

    def list_events(self, run_id: str) -> list[RuntimeEvent]:
        rows = self.connection.execute(
            "SELECT * FROM runtime_events WHERE run_id=? ORDER BY sequence", (run_id,)
        ).fetchall()
        return [self._row_to_event(row) for row in rows]

    def list_events_for_skill(self, skill_name: str, skill_version: str | None = None) -> list[RuntimeEvent]:
        if skill_version is None:
            rows = self.connection.execute(
                "SELECT * FROM runtime_events WHERE skill_name=? ORDER BY occurred_at, run_id, sequence",
                (skill_name,),
            ).fetchall()
        else:
            rows = self.connection.execute(
                "SELECT * FROM runtime_events WHERE skill_name=? AND skill_version=? ORDER BY occurred_at, run_id, sequence",
                (skill_name, skill_version),
            ).fetchall()
        return [self._row_to_event(row) for row in rows]

    @staticmethod
    def _row_to_event(row: sqlite3.Row) -> RuntimeEvent:
        return RuntimeEvent(
            event_id=row["event_id"],
            run_id=row["run_id"],
            sequence=row["sequence"],
            schema_version=row["schema_version"],
            event_type=RuntimeEventType(row["event_type"]),
            occurred_at=row["occurred_at"],
            skill_name=row["skill_name"],
            skill_version=row["skill_version"],
            action_id=row["action_id"],
            idempotency_key=row["idempotency_key"],
            external_resource_id=row["external_resource_id"],
            payload=json.loads(row["payload_json"]),
        )

    def iter_recovery_candidates(self, run_id: str) -> Iterable[RuntimeEvent]:
        """Yield succeeded primary actions in strict reverse execution order."""
        events = self.list_events(run_id)
        compensated_keys = {
            event.idempotency_key
            for event in events
            if event.event_type == RuntimeEventType.COMPENSATION_SUCCEEDED and event.idempotency_key
        }
        for event in reversed(events):
            if event.event_type != RuntimeEventType.ACTION_SUCCEEDED:
                continue
            strategy = event.payload.get("compensation", {}).get("strategy")
            if strategy not in {"auto_rollback", "manual_approval", "human_intervention"}:
                continue
            if strategy == "auto_rollback":
                key = event.payload.get("resolved_compensation_idempotency_key")
                if key and key in compensated_keys:
                    continue
            yield event

    def iter_pending_compensations(self, run_id: str) -> Iterable[RuntimeEvent]:
        for event in self.iter_recovery_candidates(run_id):
            if event.payload.get("compensation", {}).get("strategy") == "auto_rollback":
                yield event

    def iter_ambiguous_actions(self, run_id: str) -> Iterable[RuntimeEvent]:
        events = self.list_events(run_id)
        terminal = {
            (event.action_id, event.idempotency_key)
            for event in events
            if event.event_type
            in {
                RuntimeEventType.ACTION_SUCCEEDED,
                RuntimeEventType.ACTION_FAILED,
                RuntimeEventType.ACTION_OUTCOME_UNKNOWN,
            }
        }
        for event in events:
            if (
                event.event_type == RuntimeEventType.ACTION_STARTED
                and event.idempotency_key
                and (event.action_id, event.idempotency_key) not in terminal
            ):
                yield event

    def count_events(
        self,
        run_id: str,
        event_type: RuntimeEventType,
        *,
        idempotency_key: str | None = None,
    ) -> int:
        if idempotency_key is None:
            row = self.connection.execute(
                "SELECT COUNT(*) FROM runtime_events WHERE run_id=? AND event_type=?",
                (run_id, event_type.value),
            ).fetchone()
        else:
            row = self.connection.execute(
                "SELECT COUNT(*) FROM runtime_events WHERE run_id=? AND event_type=? AND idempotency_key=?",
                (run_id, event_type.value, idempotency_key),
            ).fetchone()
        return int(row[0])

    def has_event(
        self,
        run_id: str,
        event_type: RuntimeEventType,
        *,
        idempotency_key: str | None = None,
    ) -> bool:
        return self.count_events(run_id, event_type, idempotency_key=idempotency_key) > 0
