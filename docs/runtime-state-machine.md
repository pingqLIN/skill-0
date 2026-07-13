# Runtime State Machine

```text
CREATED -> PLANNED -> PREFLIGHT
  -> AWAITING_APPROVAL | READY | DENIED
READY -> ACTION_PREPARED -> ACTION_STARTED
ACTION_STARTED -> ACTION_SUCCEEDED | ACTION_FAILED | ACTION_OUTCOME_UNKNOWN
ACTION_OUTCOME_UNKNOWN -> RECONCILIATION_REQUIRED
ACTION_SUCCEEDED -> next action | VALIDATING -> SUCCEEDED
known failure with prior effects -> RECOVERY_PENDING -> COMPENSATING
COMPENSATING -> COMPENSATED | HITL_REQUIRED
```

## Crash semantics

- `ACTION_PREPARED` records idempotency ownership before adapter invocation.
- `ACTION_STARTED` without a terminal action event is an ambiguous external outcome.
- Ambiguous outcomes require reconciliation; they must not be blindly retried or compensated.
- `ACTION_SUCCEEDED` persists external resource ID and minimal recovery parameters before the next side-effecting step.
- `RUN_COMPENSATED` is the only terminal proof that all pending automatic compensations completed.

Every transition is represented by an append-only event. `runtime_runs.status` is only a query projection of the latest relevant event.
