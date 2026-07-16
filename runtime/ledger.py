from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
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
    RuntimeEventType.APPROVAL_REJECTED: RunStatus.DENIED,
    RuntimeEventType.RUN_RESUME_STARTED: RunStatus.RUNNING,
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
    RuntimeEventType.MANUAL_RECOVERY_CONFIRMED: RunStatus.RECOVERY_PENDING,
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
    RuntimeEventType.APPROVAL_REJECTED,
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
    RuntimeEventType.APPROVAL_REJECTED,
    RuntimeEventType.RUN_COMPENSATED,
    RuntimeEventType.RUN_RECOVERY_FAILED,
    RuntimeEventType.RUN_SUSPENDED,
    RuntimeEventType.MANUAL_RECOVERY_CONFIRMED,
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

            CREATE TABLE IF NOT EXISTS runtime_hitl_items (
                item_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL REFERENCES runtime_runs(run_id) ON DELETE RESTRICT,
                skill_id TEXT NOT NULL,
                action_id TEXT NOT NULL,
                kind TEXT NOT NULL CHECK(kind IN ('action_approval', 'recovery_confirmation')),
                status TEXT NOT NULL CHECK(status IN ('pending', 'approved', 'rejected', 'confirmed')),
                basis_digest TEXT NOT NULL,
                request_summary_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE UNIQUE INDEX IF NOT EXISTS idx_runtime_hitl_pending
                ON runtime_hitl_items(run_id, action_id, kind)
                WHERE status='pending';
            CREATE INDEX IF NOT EXISTS idx_runtime_hitl_status
                ON runtime_hitl_items(status, created_at);

            CREATE TABLE IF NOT EXISTS runtime_execution_bases (
                run_id TEXT PRIMARY KEY REFERENCES runtime_runs(run_id) ON DELETE RESTRICT,
                skill_id TEXT NOT NULL,
                governance_revision_id TEXT,
                skill_source_digest TEXT NOT NULL,
                contract_digest TEXT NOT NULL,
                input_digest TEXT NOT NULL,
                preflight_digest TEXT NOT NULL,
                execution_digest TEXT NOT NULL,
                dry_run INTEGER NOT NULL CHECK(dry_run IN (0, 1)),
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS runtime_hitl_decisions (
                decision_id TEXT PRIMARY KEY,
                item_id TEXT NOT NULL REFERENCES runtime_hitl_items(item_id) ON DELETE RESTRICT,
                decision TEXT NOT NULL CHECK(decision IN ('approve', 'reject', 'confirm_recovered')),
                actor TEXT NOT NULL,
                reason_code TEXT NOT NULL,
                decided_at TEXT NOT NULL
            );
            CREATE UNIQUE INDEX IF NOT EXISTS idx_runtime_hitl_one_decision
                ON runtime_hitl_decisions(item_id);

            CREATE TABLE IF NOT EXISTS runtime_resume_claims (
                item_id TEXT PRIMARY KEY REFERENCES runtime_hitl_items(item_id) ON DELETE RESTRICT,
                run_id TEXT NOT NULL REFERENCES runtime_runs(run_id) ON DELETE RESTRICT,
                action_id TEXT NOT NULL,
                basis_digest TEXT NOT NULL,
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

            CREATE TRIGGER IF NOT EXISTS trg_runtime_hitl_decisions_no_update
            BEFORE UPDATE ON runtime_hitl_decisions
            BEGIN
                SELECT RAISE(ABORT, 'runtime_hitl_decisions is immutable');
            END;

            CREATE TRIGGER IF NOT EXISTS trg_runtime_hitl_decisions_no_delete
            BEFORE DELETE ON runtime_hitl_decisions
            BEGIN
                SELECT RAISE(ABORT, 'runtime_hitl_decisions is immutable');
            END;

            CREATE TRIGGER IF NOT EXISTS trg_runtime_hitl_items_no_delete
            BEFORE DELETE ON runtime_hitl_items
            BEGIN
                SELECT RAISE(ABORT, 'runtime_hitl_items cannot be deleted');
            END;

            CREATE TRIGGER IF NOT EXISTS trg_runtime_hitl_items_guard_update
            BEFORE UPDATE ON runtime_hitl_items
            WHEN NOT (
                OLD.status='pending'
                AND (
                    (NEW.status='approved' AND EXISTS (
                        SELECT 1 FROM runtime_hitl_decisions
                        WHERE item_id=OLD.item_id AND decision='approve'
                    ))
                    OR (NEW.status='rejected' AND EXISTS (
                        SELECT 1 FROM runtime_hitl_decisions
                        WHERE item_id=OLD.item_id AND decision='reject'
                    ))
                    OR (NEW.status='confirmed' AND EXISTS (
                        SELECT 1 FROM runtime_hitl_decisions
                        WHERE item_id=OLD.item_id AND decision='confirm_recovered'
                    ))
                )
                AND NEW.item_id=OLD.item_id
                AND NEW.run_id=OLD.run_id
                AND NEW.skill_id=OLD.skill_id
                AND NEW.action_id=OLD.action_id
                AND NEW.kind=OLD.kind
                AND NEW.basis_digest=OLD.basis_digest
                AND NEW.request_summary_json=OLD.request_summary_json
                AND NEW.created_at=OLD.created_at
            )
            BEGIN
                SELECT RAISE(ABORT, 'runtime_hitl_items projection update is invalid');
            END;

            CREATE TRIGGER IF NOT EXISTS trg_runtime_execution_bases_no_update
            BEFORE UPDATE ON runtime_execution_bases
            BEGIN
                SELECT RAISE(ABORT, 'runtime_execution_bases is immutable');
            END;

            CREATE TRIGGER IF NOT EXISTS trg_runtime_execution_bases_no_delete
            BEFORE DELETE ON runtime_execution_bases
            BEGIN
                SELECT RAISE(ABORT, 'runtime_execution_bases is immutable');
            END;


            CREATE TRIGGER IF NOT EXISTS trg_runtime_resume_claims_no_update
            BEFORE UPDATE ON runtime_resume_claims
            BEGIN
                SELECT RAISE(ABORT, 'runtime_resume_claims is immutable');
            END;

            CREATE TRIGGER IF NOT EXISTS trg_runtime_resume_claims_no_delete
            BEFORE DELETE ON runtime_resume_claims
            BEGIN
                SELECT RAISE(ABORT, 'runtime_resume_claims is immutable');
            END;
            """
        )
        execution_basis_columns = {
            row["name"]
            for row in self.connection.execute(
                "PRAGMA table_info(runtime_execution_bases)"
            ).fetchall()
        }
        if "governance_revision_id" not in execution_basis_columns:
            self.connection.execute(
                "ALTER TABLE runtime_execution_bases "
                "ADD COLUMN governance_revision_id TEXT"
            )

    def create_run(
        self,
        *,
        skill_name: str,
        skill_version: str,
        run_id: str | None = None,
        execution_basis: dict[str, Any] | None = None,
    ) -> str:
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
            if execution_basis is not None:
                cur.execute(
                    """INSERT INTO runtime_execution_bases(
                           run_id, skill_id, governance_revision_id,
                           skill_source_digest, contract_digest,
                           input_digest, preflight_digest, execution_digest,
                           dry_run, created_at
                       ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        rid,
                        execution_basis["skill_id"],
                        execution_basis["governance_revision_id"],
                        execution_basis["skill_source_digest"],
                        execution_basis["contract_digest"],
                        execution_basis["input_digest"],
                        execution_basis["preflight_digest"],
                        execution_basis["execution_digest"],
                        int(bool(execution_basis["dry_run"])),
                        event.occurred_at,
                    ),
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
        self._create_event_hitl_item(cur, event)
        return stored

    def _create_event_hitl_item(
        self, cur: sqlite3.Cursor, event: RuntimeEvent
    ) -> None:
        kind = event.payload.get("hitl_kind")
        if kind not in {"action_approval", "recovery_confirmation"}:
            return
        if event.event_type not in {
            RuntimeEventType.APPROVAL_REQUIRED,
            RuntimeEventType.RUN_SUSPENDED,
        }:
            raise ValueError("HITL marker is invalid for this runtime event")
        basis = cur.execute(
            """SELECT skill_id, execution_digest
               FROM runtime_execution_bases WHERE run_id=?""",
            (event.run_id,),
        ).fetchone()
        # Direct low-level executor tests and legacy runs may not have an
        # orchestrator-created basis. They remain non-resumable by design.
        if basis is None:
            return
        action_id = event.action_id or "run_recovery"
        request_summary = event.payload.get("hitl_request_summary", {})
        if not isinstance(request_summary, dict):
            raise ValueError("HITL request summary must be an object")
        cur.execute(
            """INSERT OR IGNORE INTO runtime_hitl_items(
                   item_id, run_id, skill_id, action_id, kind, status,
                   basis_digest, request_summary_json, created_at, updated_at
               ) VALUES (?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?)""",
            (
                str(uuid4()),
                event.run_id,
                basis["skill_id"],
                action_id,
                kind,
                basis["execution_digest"],
                json.dumps(request_summary, ensure_ascii=False, sort_keys=True),
                event.occurred_at,
                event.occurred_at,
            ),
        )

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

    def get_execution_basis(self, run_id: str) -> dict[str, Any]:
        row = self.connection.execute(
            "SELECT * FROM runtime_execution_bases WHERE run_id=?", (run_id,)
        ).fetchone()
        if row is None:
            raise KeyError(run_id)
        return dict(row)

    @staticmethod
    def _decode_hitl_item(row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        item["request_summary"] = json.loads(item.pop("request_summary_json"))
        return item

    def create_hitl_item(
        self,
        *,
        run_id: str,
        skill_id: str,
        action_id: str,
        kind: str,
        basis_digest: str,
        request_summary: dict[str, Any],
    ) -> dict[str, Any]:
        if kind not in {"action_approval", "recovery_confirmation"}:
            raise ValueError("unsupported HITL item kind")
        now = datetime.now(timezone.utc).isoformat()
        cur = self.connection.cursor()
        try:
            cur.execute("BEGIN IMMEDIATE")
            run = cur.execute(
                "SELECT * FROM runtime_runs WHERE run_id=?", (run_id,)
            ).fetchone()
            if run is None:
                raise KeyError(run_id)
            expected_status = (
                RunStatus.AWAITING_APPROVAL.value
                if kind == "action_approval"
                else RunStatus.HITL_REQUIRED.value
            )
            if run["status"] != expected_status:
                raise ValueError("runtime run is not in the required HITL state")
            basis = cur.execute(
                """SELECT skill_id, execution_digest
                   FROM runtime_execution_bases WHERE run_id=?""",
                (run_id,),
            ).fetchone()
            if (
                basis is None
                or basis["skill_id"] != skill_id
                or basis["execution_digest"] != basis_digest
            ):
                raise ValueError("HITL item execution basis does not match run")
            required_event = (
                RuntimeEventType.APPROVAL_REQUIRED.value
                if kind == "action_approval"
                else RuntimeEventType.RUN_SUSPENDED.value
            )
            source = cur.execute(
                """SELECT action_id FROM runtime_events
                   WHERE run_id=? AND event_type=?
                   ORDER BY sequence DESC LIMIT 1""",
                (run_id, required_event),
            ).fetchone()
            if source is None or (source["action_id"] or "run_recovery") != action_id:
                raise ValueError("HITL item does not match the current runtime boundary")
            existing = cur.execute(
                """SELECT * FROM runtime_hitl_items
                   WHERE run_id=? AND action_id=? AND kind=? AND status='pending'""",
                (run_id, action_id, kind),
            ).fetchone()
            if existing is not None:
                cur.execute("COMMIT")
                return self._decode_hitl_item(existing)
            item_id = str(uuid4())
            cur.execute(
                """INSERT INTO runtime_hitl_items(
                       item_id, run_id, skill_id, action_id, kind, status,
                       basis_digest, request_summary_json,
                       created_at, updated_at
                   ) VALUES (?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?)""",
                (
                    item_id,
                    run_id,
                    skill_id,
                    action_id,
                    kind,
                    basis_digest,
                    json.dumps(request_summary, ensure_ascii=False, sort_keys=True),
                    now,
                    now,
                ),
            )
            row = cur.execute(
                "SELECT * FROM runtime_hitl_items WHERE item_id=?", (item_id,)
            ).fetchone()
            cur.execute("COMMIT")
            return self._decode_hitl_item(row)
        except Exception:
            if self.connection.in_transaction:
                cur.execute("ROLLBACK")
            raise

    def get_hitl_item(self, item_id: str) -> dict[str, Any]:
        row = self.connection.execute(
            "SELECT * FROM runtime_hitl_items WHERE item_id=?", (item_id,)
        ).fetchone()
        if row is None:
            raise KeyError(item_id)
        return self._decode_hitl_item(row)

    def list_hitl_items(
        self,
        *,
        status: str | None = None,
        run_id: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if status is not None:
            clauses.append("status=?")
            params.append(status)
        if run_id is not None:
            clauses.append("run_id=?")
            params.append(run_id)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        limit_sql = ""
        if limit is not None:
            if limit < 1:
                raise ValueError("HITL item limit must be positive")
            limit_sql = " LIMIT ?"
            params.append(limit)
        rows = self.connection.execute(
            f"SELECT * FROM runtime_hitl_items{where} ORDER BY created_at, item_id{limit_sql}",
            params,
        ).fetchall()
        return [self._decode_hitl_item(row) for row in rows]

    def list_hitl_decisions(self, item_id: str) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT * FROM runtime_hitl_decisions WHERE item_id=? ORDER BY decided_at, decision_id",
            (item_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def claim_hitl_resume(
        self,
        *,
        item_id: str,
        run_id: str,
        basis_digest: str,
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        cur = self.connection.cursor()
        try:
            cur.execute("BEGIN IMMEDIATE")
            item = cur.execute(
                "SELECT * FROM runtime_hitl_items WHERE item_id=?", (item_id,)
            ).fetchone()
            if item is None:
                raise KeyError(item_id)
            if (
                item["run_id"] != run_id
                or item["kind"] != "action_approval"
                or item["status"] != "approved"
                or item["basis_digest"] != basis_digest
            ):
                raise ValueError("HITL item is not valid for this runtime resume")
            run = cur.execute(
                "SELECT * FROM runtime_runs WHERE run_id=?", (run_id,)
            ).fetchone()
            if run is None:
                raise KeyError(run_id)
            if run["status"] != RunStatus.READY.value:
                raise ValueError("runtime run is not ready to resume")
            try:
                cur.execute(
                    """INSERT INTO runtime_resume_claims(
                           item_id, run_id, action_id, basis_digest, claimed_at
                       ) VALUES (?, ?, ?, ?, ?)""",
                    (
                        item_id,
                        run_id,
                        item["action_id"],
                        basis_digest,
                        now,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ValueError("HITL resume item has already been claimed") from exc
            self._append_event_in_transaction(
                cur,
                RuntimeEvent(
                    run_id=run_id,
                    event_type=RuntimeEventType.RUN_RESUME_STARTED,
                    skill_name=run["skill_name"],
                    skill_version=run["skill_version"],
                    action_id=item["action_id"],
                    payload={"hitl_item_id": item_id},
                ),
            )
            cur.execute("COMMIT")
            return self._decode_hitl_item(item)
        except Exception:
            if self.connection.in_transaction:
                cur.execute("ROLLBACK")
            raise

    def decide_hitl_item(
        self,
        *,
        item_id: str,
        decision: str,
        actor: str,
        reason_code: str,
    ) -> dict[str, Any]:
        if not isinstance(actor, str) or not (1 <= len(actor) <= 200):
            raise ValueError("HITL decision actor is invalid")
        if re.fullmatch(r"[A-Z][A-Z0-9_]{1,63}", reason_code) is None:
            raise ValueError("HITL decision reason code is invalid")
        now = datetime.now(timezone.utc).isoformat()
        cur = self.connection.cursor()
        try:
            cur.execute("BEGIN IMMEDIATE")
            item = cur.execute(
                "SELECT * FROM runtime_hitl_items WHERE item_id=?", (item_id,)
            ).fetchone()
            if item is None:
                raise KeyError(item_id)
            if item["status"] != "pending":
                raise ValueError("HITL item is no longer pending")
            allowed = (
                {"approve", "reject"}
                if item["kind"] == "action_approval"
                else {"confirm_recovered", "reject"}
            )
            if decision not in allowed:
                raise ValueError("decision is not valid for this HITL item")
            resulting_status = {
                "approve": "approved",
                "reject": "rejected",
                "confirm_recovered": "confirmed",
            }[decision]
            cur.execute(
                """INSERT INTO runtime_hitl_decisions(
                       decision_id, item_id, decision, actor, reason_code, decided_at
                   ) VALUES (?, ?, ?, ?, ?, ?)""",
                (str(uuid4()), item_id, decision, actor, reason_code, now),
            )
            cur.execute(
                "UPDATE runtime_hitl_items SET status=?, updated_at=? WHERE item_id=?",
                (resulting_status, now, item_id),
            )
            run = cur.execute(
                "SELECT * FROM runtime_runs WHERE run_id=?", (item["run_id"],)
            ).fetchone()
            expected_status = (
                RunStatus.AWAITING_APPROVAL.value
                if item["kind"] == "action_approval"
                else RunStatus.HITL_REQUIRED.value
            )
            if run["status"] != expected_status:
                raise ValueError("runtime run is no longer awaiting this decision")
            basis = cur.execute(
                "SELECT execution_digest FROM runtime_execution_bases WHERE run_id=?",
                (item["run_id"],),
            ).fetchone()
            if basis is None or basis["execution_digest"] != item["basis_digest"]:
                raise ValueError("HITL decision execution basis does not match run")
            event_type = {
                "approve": RuntimeEventType.APPROVAL_GRANTED,
                "reject": RuntimeEventType.APPROVAL_REJECTED,
                "confirm_recovered": RuntimeEventType.MANUAL_RECOVERY_CONFIRMED,
            }[decision]
            self._append_event_in_transaction(
                cur,
                RuntimeEvent(
                    run_id=item["run_id"],
                    event_type=event_type,
                    skill_name=run["skill_name"],
                    skill_version=run["skill_version"],
                    action_id=item["action_id"],
                    payload={
                        "hitl_item_id": item_id,
                        "decision": decision,
                        "actor": actor,
                        "reason_code": reason_code,
                    },
                ),
            )
            updated = cur.execute(
                "SELECT * FROM runtime_hitl_items WHERE item_id=?", (item_id,)
            ).fetchone()
            cur.execute("COMMIT")
            return self._decode_hitl_item(updated)
        except Exception:
            if self.connection.in_transaction:
                cur.execute("ROLLBACK")
            raise

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
        manually_confirmed_actions = {
            event.action_id
            for event in events
            if event.event_type == RuntimeEventType.MANUAL_RECOVERY_CONFIRMED
            and event.action_id is not None
        }
        for event in reversed(events):
            if event.event_type != RuntimeEventType.ACTION_SUCCEEDED:
                continue
            strategy = event.payload.get("compensation", {}).get("strategy")
            if strategy not in {"auto_rollback", "manual_approval", "human_intervention"}:
                continue
            if event.action_id in manually_confirmed_actions:
                continue
            if strategy == "auto_rollback":
                key = event.payload.get("resolved_compensation_idempotency_key")
                if key and key in compensated_keys:
                    continue
            yield event

    def get_unfinished_resume(self, run_id: str) -> RuntimeEvent | None:
        events = self.list_events(run_id)
        latest_index: int | None = None
        for index, event in enumerate(events):
            if event.event_type == RuntimeEventType.RUN_RESUME_STARTED:
                latest_index = index
        if latest_index is None:
            return None
        closure_events = {
            RuntimeEventType.APPROVAL_REQUIRED,
            RuntimeEventType.POLICY_DENIED,
            RuntimeEventType.RECONCILIATION_REQUIRED,
            RuntimeEventType.RUN_SUCCEEDED,
            RuntimeEventType.RUN_FAILED,
            RuntimeEventType.RUN_SUSPENDED,
            RuntimeEventType.RUN_CANCELLED,
        }
        if any(
            event.event_type in closure_events
            for event in events[latest_index + 1 :]
        ):
            return None
        return events[latest_index]

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
