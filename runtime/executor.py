from __future__ import annotations

from typing import Any, Protocol

from .ledger import RuntimeLedger
from .models import ActionResult, RunResult, RunStatus, RuntimeEvent, RuntimeEventType
from .policy import DefaultPolicyEngine, PolicyEngine
from .template import render_key_template, resolve_json_pointer, resolve_parameter_mapping


class ActionAdapter(Protocol):
    supports_dry_run: bool

    def execute(self, action_id: str, parameters: dict[str, Any], *, dry_run: bool) -> ActionResult: ...


class RuntimeExecutor:
    """Audit-first reference executor.

    The P0 implementation is deliberately small: policy, idempotency claim,
    adapter boundary, minimal event recording, and declared recovery material.
    It is not a production sandbox or distributed transaction coordinator.
    """

    def __init__(self, ledger: RuntimeLedger, adapter: ActionAdapter, policy: PolicyEngine | None = None) -> None:
        self.ledger = ledger
        self.adapter = adapter
        self.policy = policy or DefaultPolicyEngine()

    def run(
        self,
        contract: dict[str, Any],
        *,
        parameters: dict[str, Any],
        context: dict[str, Any] | None = None,
        dry_run: bool = True,
    ) -> RunResult:
        context = dict(context or {})
        skill = contract["skill_ref"]
        run_id = self.ledger.create_run(skill_name=skill["name"], skill_version=skill["version"])
        primary_bindings = [
            binding for binding in contract["action_bindings"] if binding.get("role", "primary") == "primary"
        ]
        self._event(
            run_id,
            skill,
            RuntimeEventType.PLAN_CREATED,
            payload={"dry_run": dry_run, "action_count": len(primary_bindings)},
        )
        self._event(
            run_id,
            skill,
            RuntimeEventType.PREFLIGHT_PASSED,
            payload={"contract_schema_version": contract["schema_version"]},
        )

        if not primary_bindings:
            reason = "runtime contract contains no primary actions"
            self._event(run_id, skill, RuntimeEventType.POLICY_DENIED, payload={"reason": reason})
            return RunResult(run_id, RunStatus.DENIED, reason=reason)

        if dry_run and not bool(getattr(self.adapter, "supports_dry_run", False)):
            reason = "adapter does not declare dry-run support"
            self._event(run_id, skill, RuntimeEventType.POLICY_DENIED, payload={"reason": reason})
            return RunResult(run_id, RunStatus.DENIED, reason=reason)

        if not dry_run and not contract.get("feature_flags", {}).get("real_execution", False):
            reason = "real execution is disabled by the runtime contract feature flag"
            self._event(run_id, skill, RuntimeEventType.POLICY_DENIED, payload={"reason": reason})
            return RunResult(run_id, RunStatus.DENIED, reason=reason)

        outputs: dict[str, Any] = {}
        for binding in primary_bindings:
            action_id = binding["action_id"]
            decision = self.policy.evaluate(binding, context)
            if decision.outcome == "deny":
                self._event(
                    run_id,
                    skill,
                    RuntimeEventType.POLICY_DENIED,
                    action_id=action_id,
                    payload={"reason": decision.reason},
                )
                return RunResult(run_id, RunStatus.DENIED, reason=decision.reason)
            if decision.approval_required:
                self._event(
                    run_id,
                    skill,
                    RuntimeEventType.APPROVAL_REQUIRED,
                    action_id=action_id,
                    payload={"reason": decision.reason, **decision.metadata},
                )
                return RunResult(run_id, RunStatus.AWAITING_APPROVAL, reason=decision.reason)

            self._event(
                run_id,
                skill,
                RuntimeEventType.POLICY_ALLOWED,
                action_id=action_id,
                payload={"reason": decision.reason, **decision.metadata},
            )
            effect = binding["effect"]
            primary_key: str | None = None
            template = effect.get("primary_idempotency_key_template")
            try:
                if template:
                    primary_key = render_key_template(template, run_id=run_id, inputs=parameters)
            except (KeyError, ValueError) as exc:
                reason = f"primary idempotency template error: {type(exc).__name__}"
                self._event(
                    run_id,
                    skill,
                    RuntimeEventType.RUN_FAILED,
                    action_id=action_id,
                    payload={"reason": reason},
                )
                return RunResult(run_id, RunStatus.FAILED, reason=reason)

            prepared = RuntimeEvent(
                run_id=run_id,
                event_type=RuntimeEventType.ACTION_PREPARED,
                skill_name=skill["name"],
                skill_version=skill["version"],
                action_id=action_id,
                idempotency_key=primary_key,
                payload={
                    "dry_run": dry_run,
                    "effect_classification": effect["classification"],
                    "resource_kind": effect["resource_kind"],
                    "operation": effect["operation"],
                },
            )
            if primary_key:
                if self.ledger.append_claimed_event(prepared, purpose="primary") is None:
                    reason = "duplicate primary idempotency key"
                    self._event(
                        run_id,
                        skill,
                        RuntimeEventType.RUN_FAILED,
                        action_id=action_id,
                        payload={"reason": reason},
                    )
                    return RunResult(run_id, RunStatus.FAILED, reason=reason)
            else:
                self.ledger.append_event(prepared)

            self._event(
                run_id,
                skill,
                RuntimeEventType.ACTION_STARTED,
                action_id=action_id,
                idempotency_key=primary_key,
                payload={"dry_run": dry_run},
            )

            try:
                result = self.adapter.execute(action_id, parameters, dry_run=dry_run)
            except Exception as exc:  # Adapter boundary: write outcome may be unknowable.
                if effect["classification"] != "read_only":
                    self._event(
                        run_id,
                        skill,
                        RuntimeEventType.ACTION_OUTCOME_UNKNOWN,
                        action_id=action_id,
                        idempotency_key=primary_key,
                        payload={"error_code": "ADAPTER_EXCEPTION", "exception_type": type(exc).__name__},
                    )
                    self._event(
                        run_id,
                        skill,
                        RuntimeEventType.RECONCILIATION_REQUIRED,
                        action_id=action_id,
                        idempotency_key=primary_key,
                        payload={"reason": "adapter raised after a write-capable action started"},
                    )
                    return RunResult(
                        run_id,
                        RunStatus.RECONCILIATION_REQUIRED,
                        reason="external action outcome is unknown; reconcile before retry or compensation",
                    )
                self._event(
                    run_id,
                    skill,
                    RuntimeEventType.ACTION_FAILED,
                    action_id=action_id,
                    idempotency_key=primary_key,
                    payload={"error_code": "ADAPTER_EXCEPTION", "exception_type": type(exc).__name__},
                )
                self._event(
                    run_id,
                    skill,
                    RuntimeEventType.RUN_FAILED,
                    payload={"failed_action_id": action_id, "reason": "adapter exception"},
                )
                return RunResult(run_id, RunStatus.FAILED, reason=str(exc))

            if not result.success:
                self._event(
                    run_id,
                    skill,
                    RuntimeEventType.ACTION_FAILED,
                    action_id=action_id,
                    idempotency_key=primary_key,
                    payload={"error_code": result.error_code, "error_message_present": bool(result.error_message)},
                )
                self._event(
                    run_id,
                    skill,
                    RuntimeEventType.RUN_FAILED,
                    payload={"failed_action_id": action_id, "reason": result.error_code or "action failed"},
                )
                return RunResult(run_id, RunStatus.FAILED, reason=result.error_message or result.error_code)

            compensation = binding["compensation"]
            external_resource_id = result.external_resource_id
            envelope: dict[str, Any] = {
                "inputs": parameters,
                "outputs": result.outputs,
                "external_resource_id": external_resource_id,
            }
            external_pointer = effect.get("external_id_pointer")
            try:
                if external_resource_id is None and external_pointer:
                    external_resource_id = str(resolve_json_pointer(envelope, external_pointer))
                    envelope["external_resource_id"] = external_resource_id

                resolved_comp_key: str | None = None
                resolved_comp_parameters: dict[str, Any] = {}
                if compensation.get("strategy") == "auto_rollback":
                    resolved_comp_key = render_key_template(
                        compensation["idempotency_key_template"],
                        run_id=run_id,
                        inputs=parameters,
                        external_resource_id=external_resource_id,
                    )
                    resolved_comp_parameters = resolve_parameter_mapping(
                        compensation["parameters_mapping"], envelope
                    )
            except (KeyError, IndexError, TypeError, ValueError) as exc:
                # The external action reported success but recovery metadata could
                # not be derived. Persist the known effect before escalating.
                self._event(
                    run_id,
                    skill,
                    RuntimeEventType.ACTION_SUCCEEDED,
                    action_id=action_id,
                    idempotency_key=primary_key,
                    external_resource_id=external_resource_id,
                    payload={
                        "dry_run": dry_run,
                        "output_keys": sorted(result.outputs),
                        "compensation": compensation,
                        "recovery_metadata_error": type(exc).__name__,
                    },
                )
                self._event(
                    run_id,
                    skill,
                    RuntimeEventType.RECONCILIATION_REQUIRED,
                    action_id=action_id,
                    idempotency_key=primary_key,
                    external_resource_id=external_resource_id,
                    payload={"reason": "committed effect lacks resolvable recovery metadata"},
                )
                self._event(
                    run_id,
                    skill,
                    RuntimeEventType.RUN_SUSPENDED,
                    action_id=action_id,
                    payload={"reason": "human review required for incomplete recovery metadata"},
                )
                return RunResult(
                    run_id,
                    RunStatus.HITL_REQUIRED,
                    reason="committed effect requires human reconciliation",
                )

            # Persist only minimum recovery material. Raw adapter outputs are
            # returned to the caller but not copied wholesale into the ledger.
            payload = {
                "dry_run": dry_run,
                "output_keys": sorted(result.outputs),
                "compensation": compensation,
                "resolved_compensation_idempotency_key": resolved_comp_key,
                "resolved_compensation_parameters": resolved_comp_parameters,
            }
            self._event(
                run_id,
                skill,
                RuntimeEventType.ACTION_SUCCEEDED,
                action_id=action_id,
                idempotency_key=primary_key,
                external_resource_id=external_resource_id,
                payload=payload,
            )
            if compensation.get("strategy") == "auto_rollback":
                self._event(
                    run_id,
                    skill,
                    RuntimeEventType.COMPENSATION_QUEUED,
                    action_id=compensation["action_id"],
                    idempotency_key=resolved_comp_key,
                    external_resource_id=external_resource_id,
                    payload={"source_action_id": action_id, "dry_run": dry_run},
                )
            outputs[action_id] = result.outputs

        self._event(run_id, skill, RuntimeEventType.VALIDATION_SUCCEEDED, payload={"validated": True})
        self._event(run_id, skill, RuntimeEventType.RUN_SUCCEEDED, payload={"dry_run": dry_run})
        return RunResult(run_id, RunStatus.SUCCEEDED, outputs=outputs)

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
