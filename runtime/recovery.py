from __future__ import annotations

from typing import Any, Protocol

from .ledger import RuntimeLedger
from .models import ActionResult, RunStatus, RuntimeEvent, RuntimeEventType


class CompensationAdapter(Protocol):
    supports_dry_run: bool

    def compensate(
        self,
        action_id: str,
        parameters: dict[str, Any],
        *,
        idempotency_key: str,
        dry_run: bool,
    ) -> ActionResult: ...


class RecoveryCoordinator:
    """Replay-safe, event-ledger-driven compensation coordinator.

    Automatic compensations run in strict LIFO order. Manual or human
    strategies form an explicit HITL boundary; they are never silently
    converted into tool calls.
    """

    def __init__(self, ledger: RuntimeLedger, adapter: CompensationAdapter) -> None:
        self.ledger = ledger
        self.adapter = adapter

    def recover(self, run_id: str) -> RunStatus:
        run = self.ledger.get_run(run_id)
        current = RunStatus(run["status"])
        if current in {RunStatus.COMPENSATED, RunStatus.HITL_REQUIRED}:
            return current
        if current == RunStatus.RECONCILIATION_REQUIRED:
            return current

        skill = {"name": run["skill_name"], "version": run["skill_version"]}
        ambiguous = list(self.ledger.iter_ambiguous_actions(run_id))
        if ambiguous:
            if not self.ledger.has_event(run_id, RuntimeEventType.RECONCILIATION_REQUIRED):
                event = ambiguous[0]
                self._event(
                    run_id,
                    skill,
                    RuntimeEventType.RECONCILIATION_REQUIRED,
                    action_id=event.action_id,
                    idempotency_key=event.idempotency_key,
                    payload={"reason": "action started without a recorded terminal outcome"},
                )
            return RunStatus.RECONCILIATION_REQUIRED

        unfinished_resume = self.ledger.get_unfinished_resume(run_id)
        if unfinished_resume is not None:
            self._event(
                run_id,
                skill,
                RuntimeEventType.RECONCILIATION_REQUIRED,
                action_id=unfinished_resume.action_id,
                payload={
                    "reason": "resume attempt ended without a durable runtime outcome",
                    "reason_code": "RESUME_ATTEMPT_INCOMPLETE",
                    "hitl_item_id": unfinished_resume.payload.get("hitl_item_id"),
                },
            )
            return RunStatus.RECONCILIATION_REQUIRED

        candidates = list(self.ledger.iter_recovery_candidates(run_id))
        if not candidates:
            # All automatic compensations and action-scoped manual recoveries
            # may already be closed.
            has_recovery_effect = any(
                event.event_type == RuntimeEventType.ACTION_SUCCEEDED
                and event.payload.get("compensation", {}).get("strategy")
                in {"auto_rollback", "manual_approval", "human_intervention"}
                for event in self.ledger.list_events(run_id)
            )
            if has_recovery_effect:
                if not self.ledger.has_event(run_id, RuntimeEventType.RUN_COMPENSATED):
                    self._event(run_id, skill, RuntimeEventType.RUN_COMPENSATED, payload={"already_complete": True})
                return RunStatus.COMPENSATED
            return RunStatus(self.ledger.get_run(run_id)["status"])

        for source_event in candidates:
            comp = source_event.payload.get("compensation", {})
            strategy = comp.get("strategy")
            dry_run = bool(source_event.payload.get("dry_run", True))

            if strategy in {"manual_approval", "human_intervention"}:
                reason = (
                    "manual recovery approval required"
                    if strategy == "manual_approval"
                    else "human recovery intervention required"
                )
                self._event(
                    run_id,
                    skill,
                    RuntimeEventType.RUN_SUSPENDED,
                    action_id=source_event.action_id,
                    external_resource_id=source_event.external_resource_id,
                    payload={
                        "reason": reason,
                        "strategy": strategy,
                        "approval_policy": comp.get("approval_policy"),
                        "escalation_queue": comp.get("escalation_queue"),
                        "hitl_kind": "recovery_confirmation",
                        "hitl_request_summary": {
                            "strategy": strategy,
                            "reason_code": "MANUAL_RECOVERY_CONFIRMATION_REQUIRED",
                        },
                    },
                )
                return RunStatus.HITL_REQUIRED

            if strategy != "auto_rollback":
                continue

            action_id = comp.get("action_id")
            key = source_event.payload.get("resolved_compensation_idempotency_key")
            if not action_id or not key:
                self._event(
                    run_id,
                    skill,
                    RuntimeEventType.RUN_SUSPENDED,
                    action_id=source_event.action_id,
                    payload={"reason": "automatic compensation lacks resolved action or idempotency key"},
                )
                return RunStatus.HITL_REQUIRED

            if dry_run and not bool(getattr(self.adapter, "supports_dry_run", False)):
                self._event(
                    run_id,
                    skill,
                    RuntimeEventType.RUN_SUSPENDED,
                    action_id=action_id,
                    idempotency_key=key,
                    payload={"reason": "compensation adapter does not declare dry-run support"},
                )
                return RunStatus.HITL_REQUIRED

            max_attempts = 1 + int(comp.get("max_retries", 3))
            previous_starts = self.ledger.count_events(
                run_id, RuntimeEventType.COMPENSATION_STARTED, idempotency_key=key
            )
            if previous_starts >= max_attempts:
                self._fail_recovery(
                    run_id,
                    skill,
                    action_id=action_id,
                    key=key,
                    max_attempts=max_attempts,
                )
                return RunStatus.HITL_REQUIRED

            succeeded = False
            for attempt in range(previous_starts + 1, max_attempts + 1):
                start = RuntimeEvent(
                    run_id=run_id,
                    event_type=RuntimeEventType.COMPENSATION_STARTED,
                    skill_name=skill["name"],
                    skill_version=skill["version"],
                    action_id=action_id,
                    idempotency_key=key,
                    external_resource_id=source_event.external_resource_id,
                    payload={
                        "source_action_id": source_event.action_id,
                        "attempt": attempt,
                        "max_attempts": max_attempts,
                        "dry_run": dry_run,
                    },
                )
                if self.ledger.append_claimed_event(start, purpose="compensation") is None:
                    self._event(
                        run_id,
                        skill,
                        RuntimeEventType.RUN_SUSPENDED,
                        action_id=action_id,
                        idempotency_key=key,
                        payload={"reason": "compensation idempotency key is owned by another operation"},
                    )
                    return RunStatus.HITL_REQUIRED

                try:
                    encoded_parameters = source_event.payload.get(
                        "resolved_compensation_parameters", {}
                    )
                    compensation_parameters: dict[str, Any] = {}
                    for name, value in encoded_parameters.items():
                        if value != {"$runtime_ref": "external_resource_id"}:
                            raise ValueError("unsupported persisted recovery parameter")
                        if source_event.external_resource_id is None:
                            raise ValueError("external resource ID is unavailable")
                        compensation_parameters[name] = source_event.external_resource_id
                    result = self.adapter.compensate(
                        action_id,
                        compensation_parameters,
                        idempotency_key=key,
                        dry_run=dry_run,
                    )
                except Exception as exc:
                    result = ActionResult(
                        False,
                        error_code="ADAPTER_EXCEPTION",
                        error_message=type(exc).__name__,
                    )

                acceptable = set(comp.get("acceptable_errors", []))
                if result.success or (result.error_code and result.error_code in acceptable):
                    self._event(
                        run_id,
                        skill,
                        RuntimeEventType.COMPENSATION_SUCCEEDED,
                        action_id=action_id,
                        idempotency_key=key,
                        external_resource_id=source_event.external_resource_id,
                        payload={
                            "attempt": attempt,
                            "acceptable_error": result.error_code if not result.success else None,
                            "dry_run": dry_run,
                        },
                    )
                    succeeded = True
                    break

                self._event(
                    run_id,
                    skill,
                    RuntimeEventType.COMPENSATION_FAILED,
                    action_id=action_id,
                    idempotency_key=key,
                    external_resource_id=source_event.external_resource_id,
                    payload={
                        "attempt": attempt,
                        "error_code": result.error_code,
                        "error_message_present": bool(result.error_message),
                        "dry_run": dry_run,
                    },
                )
                if attempt < max_attempts:
                    self._event(
                        run_id,
                        skill,
                        RuntimeEventType.COMPENSATION_RETRY_SCHEDULED,
                        action_id=action_id,
                        idempotency_key=key,
                        payload={"completed_attempt": attempt, "next_attempt": attempt + 1},
                    )

            if not succeeded:
                self._fail_recovery(
                    run_id,
                    skill,
                    action_id=action_id,
                    key=key,
                    max_attempts=max_attempts,
                )
                return RunStatus.HITL_REQUIRED

        if not self.ledger.has_event(run_id, RuntimeEventType.RUN_COMPENSATED):
            self._event(run_id, skill, RuntimeEventType.RUN_COMPENSATED, payload={"recovered": True})
        return RunStatus.COMPENSATED

    def _fail_recovery(
        self,
        run_id: str,
        skill: dict[str, str],
        *,
        action_id: str,
        key: str,
        max_attempts: int,
    ) -> None:
        if not self.ledger.has_event(
            run_id, RuntimeEventType.RUN_RECOVERY_FAILED, idempotency_key=key
        ):
            self._event(
                run_id,
                skill,
                RuntimeEventType.RUN_RECOVERY_FAILED,
                action_id=action_id,
                idempotency_key=key,
                payload={"reason": "compensation retry budget exhausted", "max_attempts": max_attempts},
            )
        self._event(
            run_id,
            skill,
            RuntimeEventType.RUN_SUSPENDED,
            action_id=action_id,
            idempotency_key=key,
            payload={"reason": "compensation retry budget exhausted", "max_attempts": max_attempts},
        )

    def _event(
        self,
        run_id: str,
        skill: dict[str, str],
        event_type: RuntimeEventType,
        *,
        payload: dict[str, Any],
        action_id: str | None = None,
        idempotency_key: str | None = None,
        external_resource_id: str | None = None,
    ) -> RuntimeEvent:
        return self.ledger.append_event(
            RuntimeEvent(
                run_id=run_id,
                event_type=event_type,
                skill_name=skill["name"],
                skill_version=skill["version"],
                action_id=action_id,
                idempotency_key=idempotency_key,
                external_resource_id=external_resource_id,
                payload=payload,
            )
        )
