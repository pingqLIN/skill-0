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
