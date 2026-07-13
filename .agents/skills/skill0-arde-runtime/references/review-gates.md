# Review gates

## Compatibility

- Existing Skill fixtures still validate and parse.
- Search/index/dashboard behavior is unchanged when no runtime contract exists.
- Cross-document references reject orphans and duplicate bindings.

## Runtime integrity

- Every external write declares resource, operation, primary idempotency key, logical lock key, risk, and recovery strategy.
- Successful effects are durably recorded before a later effect begins.
- Runtime events and idempotency claims cannot be updated or deleted.
- Reopening the database preserves ordering and recovery work.

## Recovery

- Recovery order is strict LIFO across automatic and human recovery boundaries.
- Retries honor a persisted attempt budget.
- Acceptable terminal errors are recorded explicitly.
- Exhausted or ambiguous recovery enters HITL; it never masquerades as success.

## Security

- Unknown effects and risks fail closed.
- Real execution remains feature-flagged off until the security milestone.
- No shell, `eval`, inline Python, or dynamic import is sourced from a Skill document.
- Sensitive payloads are redacted before logs, traces, and review queues.

## Evidence

- Evidence includes an event watermark and sample size.
- Evidence can be rebuilt from immutable facts.
- Evolution produces a reviewed suggestion and version bump, not silent mutation.
