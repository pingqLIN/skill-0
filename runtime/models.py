from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4


class RunStatus(StrEnum):
    CREATED = "created"
    PLANNED = "planned"
    PREFLIGHT = "preflight"
    AWAITING_APPROVAL = "awaiting_approval"
    READY = "ready"
    RUNNING = "running"
    VALIDATING = "validating"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RECOVERY_PENDING = "recovery_pending"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"
    RECOVERY_FAILED = "recovery_failed"
    RECONCILIATION_REQUIRED = "reconciliation_required"
    HITL_REQUIRED = "hitl_required"
    DENIED = "denied"
    CANCELLED = "cancelled"


class RuntimeEventType(StrEnum):
    RUN_CREATED = "run_created"
    PLAN_CREATED = "plan_created"
    PREFLIGHT_PASSED = "preflight_passed"
    POLICY_ALLOWED = "policy_allowed"
    POLICY_DENIED = "policy_denied"
    APPROVAL_REQUIRED = "approval_required"
    APPROVAL_GRANTED = "approval_granted"
    APPROVAL_REJECTED = "approval_rejected"
    RUN_RESUME_STARTED = "run_resume_started"
    ACTION_PREPARED = "action_prepared"
    ACTION_STARTED = "action_started"
    ACTION_SUCCEEDED = "action_succeeded"
    ACTION_FAILED = "action_failed"
    ACTION_OUTCOME_UNKNOWN = "action_outcome_unknown"
    VALIDATION_SUCCEEDED = "validation_succeeded"
    VALIDATION_FAILED = "validation_failed"
    COMPENSATION_QUEUED = "compensation_queued"
    COMPENSATION_STARTED = "compensation_started"
    COMPENSATION_RETRY_SCHEDULED = "compensation_retry_scheduled"
    COMPENSATION_SUCCEEDED = "compensation_succeeded"
    COMPENSATION_FAILED = "compensation_failed"
    RECONCILIATION_REQUIRED = "reconciliation_required"
    RUN_SUCCEEDED = "run_succeeded"
    RUN_FAILED = "run_failed"
    RUN_COMPENSATED = "run_compensated"
    RUN_RECOVERY_FAILED = "run_recovery_failed"
    RUN_SUSPENDED = "run_suspended"
    MANUAL_RECOVERY_CONFIRMED = "manual_recovery_confirmed"
    RUN_CANCELLED = "run_cancelled"


@dataclass(frozen=True, slots=True)
class RuntimeEvent:
    run_id: str
    event_type: RuntimeEventType
    skill_name: str
    skill_version: str
    payload: dict[str, Any] = field(default_factory=dict)
    action_id: str | None = None
    idempotency_key: str | None = None
    external_resource_id: str | None = None
    event_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    sequence: int = 0
    schema_version: str = "4.0.0"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["event_type"] = self.event_type.value
        return data


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    outcome: str
    reason: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def allowed(self) -> bool:
        return self.outcome == "allow"

    @property
    def approval_required(self) -> bool:
        return self.outcome == "require_approval"


@dataclass(frozen=True, slots=True)
class ActionResult:
    success: bool
    outputs: dict[str, Any] = field(default_factory=dict)
    external_resource_id: str | None = None
    # Non-authoritative adapter hint retained only for compatibility.
    # The executor resolves recovery parameters from the contract mapping.
    compensation_parameters: dict[str, Any] = field(default_factory=dict)
    error_code: str | None = None
    error_message: str | None = None


@dataclass(frozen=True, slots=True)
class RunResult:
    run_id: str
    status: RunStatus
    outputs: dict[str, Any] = field(default_factory=dict)
    reason: str | None = None
