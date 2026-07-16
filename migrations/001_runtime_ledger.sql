PRAGMA foreign_keys = ON;

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
