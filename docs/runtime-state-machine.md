# Runtime State Machine

```text
CREATED -> PLANNED -> PREFLIGHT
  -> AWAITING_APPROVAL | READY | DENIED
AWAITING_APPROVAL -> READY (approved) | DENIED (rejected)
READY -> ACTION_PREPARED -> ACTION_STARTED
ACTION_STARTED -> ACTION_SUCCEEDED | ACTION_FAILED | ACTION_OUTCOME_UNKNOWN
ACTION_OUTCOME_UNKNOWN -> RECONCILIATION_REQUIRED
ACTION_SUCCEEDED -> next action | VALIDATING -> SUCCEEDED
known failure with prior effects -> RECOVERY_PENDING -> COMPENSATING
COMPENSATING -> COMPENSATED | HITL_REQUIRED
HITL_REQUIRED -> RECOVERY_PENDING (action recovery confirmed) | DENIED (rejected)
```

## Crash semantics

- `ACTION_PREPARED` records idempotency ownership before adapter invocation.
- `ACTION_STARTED` without a terminal action event is an ambiguous external outcome.
- Ambiguous outcomes require reconciliation; they must not be blindly retried or compensated.
- `ACTION_SUCCEEDED` persists external resource ID and minimal recovery parameters before the next side-effecting step.
- `RUN_COMPENSATED` is the only terminal proof that all pending automatic compensations completed.

Every transition is represented by an append-only event. `runtime_runs.status` is only a query projection of the latest relevant event.

## Human-in-the-loop invariants

- An `APPROVAL_REQUIRED` event and its pending queue item are committed in the same SQLite transaction.
- A decision requires the authenticated JWT subject to be present in the server-side decision-actor allowlist, then records that subject, an allowlisted decision, and a fixed reason code. Request bodies cannot provide the actor or approved action IDs.
- Approval changes the original run to `READY`; it does not invoke an adapter.
- Resume keeps the original `run_id`, atomically commits the one-time item claim with `RUN_RESUME_STARTED`, recomputes the keyed execution basis, and skips actions already recorded as succeeded. An attempt without a later durable outcome is routed to reconciliation.
- A changed canonical skill, contract, input, preflight basis, or action order cannot reuse an approval.
- Manual recovery creates a confirmation item only when the recovery coordinator marks that boundary as confirmable. Confirmation closes only that action; the coordinator must process every remaining candidate before emitting `RUN_COMPENSATED`. Unknown external outcomes remain in `RECONCILIATION_REQUIRED` and cannot use approval as reconciliation.
- HITL decisions and execution bases are append-only/immutable. The queue item status is a mutable query projection.
