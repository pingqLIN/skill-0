from __future__ import annotations

import hmac
from typing import Any, Protocol

from .ledger import RuntimeLedger
from .models import ActionResult, RunResult, RunStatus, RuntimeEvent, RuntimeEventType
from .policy import DefaultPolicyEngine, PolicyEngine
from .rules import RuleEvaluationError, RuleEvaluator
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
        preflight: dict[str, Any] | None = None,
        rule_evaluator: RuleEvaluator | None = None,
        rule_bindings: dict[str, str] | None = None,
        existing_run_id: str | None = None,
        execution_basis_digest: str | None = None,
        resume_item_id: str | None = None,
    ) -> RunResult:
        context = dict(context or {})
        skill = contract["skill_ref"]
        resuming = False
        if existing_run_id is None:
            run_id = self.ledger.create_run(
                skill_name=skill["name"], skill_version=skill["version"]
            )
        else:
            existing = self.ledger.get_run(existing_run_id)
            if existing["status"] not in {
                RunStatus.CREATED.value,
                RunStatus.READY.value,
            }:
                raise ValueError("runtime run is not ready to resume")
            if (
                existing["skill_name"] != skill["name"]
                or existing["skill_version"] != skill["version"]
            ):
                raise ValueError("runtime resume skill identity mismatch")
            run_id = existing_run_id
            resuming = existing["status"] == RunStatus.READY.value
            basis = self.ledger.get_execution_basis(run_id)
            # Orchestrator-created runs never trust approval hints supplied in
            # a caller context. Only durable HITL decisions can grant actions.
            context.pop("approved_action_ids", None)
            if resuming:
                if execution_basis_digest is None or not hmac.compare_digest(
                    basis["execution_digest"], execution_basis_digest
                ):
                    raise ValueError("runtime resume execution basis is not attested")
                if resume_item_id is None:
                    raise ValueError("runtime resume item is required")
                self.ledger.claim_hitl_resume(
                    item_id=resume_item_id,
                    run_id=run_id,
                    basis_digest=execution_basis_digest,
                )
                approved_items = [
                    item
                    for item in self.ledger.list_hitl_items(
                        status="approved", run_id=run_id
                    )
                    if item["kind"] == "action_approval"
                ]
                if not approved_items or any(
                    item["basis_digest"] != basis["execution_digest"]
                    for item in approved_items
                ):
                    raise ValueError("runtime resume lacks a bound approval")
                context["approved_action_ids"] = sorted(
                    {item["action_id"] for item in approved_items}
                )
        primary_bindings = [
            binding for binding in contract["action_bindings"] if binding.get("role", "primary") == "primary"
        ]
        if not resuming:
            self._event(
                run_id,
                skill,
                RuntimeEventType.PLAN_CREATED,
                payload={"dry_run": dry_run, "action_count": len(primary_bindings)},
            )
        required_attestations = {
            "schema_validated",
            "skill_schema_validated",
            "cross_references_validated",
            "skill_identity_validated",
        }
        if preflight is None or not all(preflight.get(name) is True for name in required_attestations):
            reason = "runtime preflight was not truthfully attested"
            self._event(run_id, skill, RuntimeEventType.POLICY_DENIED, payload={"reason": reason})
            return RunResult(run_id, RunStatus.DENIED, reason=reason)
        if not resuming:
            self._event(
                run_id,
                skill,
                RuntimeEventType.PREFLIGHT_PASSED,
                payload={"contract_schema_version": contract["schema_version"], **preflight},
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
        validated_postconditions: list[str] = []
        rule_bindings = dict(rule_bindings or {})
        completed_action_ids = {
            event.action_id
            for event in self.ledger.list_events(run_id)
            if event.event_type == RuntimeEventType.ACTION_SUCCEEDED
            and event.action_id is not None
        }
        for binding in primary_bindings:
            action_id = binding["action_id"]
            if action_id in completed_action_ids:
                continue
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
                    payload={
                        "reason": decision.reason,
                        **decision.metadata,
                        "hitl_kind": "action_approval",
                        "hitl_request_summary": {
                            "effect_classification": binding["effect"]["classification"],
                            "resource_kind": binding["effect"]["resource_kind"],
                            "operation": binding["effect"]["operation"],
                            "risk_level": binding["risk"]["level"],
                            "approval_required": binding["risk"].get(
                                "approval_required", False
                            ),
                            "compensation_strategy": binding["compensation"]["strategy"],
                        },
                    },
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
                    resolved_comp_parameters = self._encode_recovery_parameters(
                        resolved_comp_parameters,
                        external_resource_id=external_resource_id,
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
            outputs[action_id] = result.outputs

            postcondition_ids = binding.get("validation", {}).get("postcondition_rule_ids", [])
            for rule_id in postcondition_ids:
                evaluator_name = rule_bindings.get(rule_id)
                if rule_evaluator is None or evaluator_name is None:
                    reason = f"postcondition Rule {rule_id} has no executable evaluator"
                    self._event(
                        run_id,
                        skill,
                        RuntimeEventType.VALIDATION_FAILED,
                        action_id=action_id,
                        payload={"rule_id": rule_id, "reason": reason},
                    )
                    self._event(
                        run_id,
                        skill,
                        RuntimeEventType.RUN_FAILED,
                        payload={"failed_action_id": action_id, "reason": reason},
                    )
                    recovery_pending = self._queue_compensation(
                        run_id,
                        skill,
                        source_action_id=action_id,
                        compensation=compensation,
                        idempotency_key=resolved_comp_key,
                        external_resource_id=external_resource_id,
                        dry_run=dry_run,
                    )
                    status = RunStatus.RECOVERY_PENDING if recovery_pending else RunStatus.FAILED
                    return RunResult(run_id, status, outputs=outputs, reason=reason)
                try:
                    passed = rule_evaluator.evaluate(
                        rule_id,
                        evaluator_name,
                        phase="postcondition",
                        parameters=parameters,
                        outputs=outputs,
                        context=context,
                    )
                except RuleEvaluationError as exc:
                    passed = False
                    reason = str(exc)
                else:
                    reason = f"postcondition Rule {rule_id} failed"
                if not passed:
                    self._event(
                        run_id,
                        skill,
                        RuntimeEventType.VALIDATION_FAILED,
                        action_id=action_id,
                        payload={"rule_id": rule_id, "reason": reason},
                    )
                    self._event(
                        run_id,
                        skill,
                        RuntimeEventType.RUN_FAILED,
                        payload={"failed_action_id": action_id, "reason": reason},
                    )
                    recovery_pending = self._queue_compensation(
                        run_id,
                        skill,
                        source_action_id=action_id,
                        compensation=compensation,
                        idempotency_key=resolved_comp_key,
                        external_resource_id=external_resource_id,
                        dry_run=dry_run,
                    )
                    status = RunStatus.RECOVERY_PENDING if recovery_pending else RunStatus.FAILED
                    return RunResult(run_id, status, outputs=outputs, reason=reason)
                validated_postconditions.append(rule_id)

            self._queue_compensation(
                run_id,
                skill,
                source_action_id=action_id,
                compensation=compensation,
                idempotency_key=resolved_comp_key,
                external_resource_id=external_resource_id,
                dry_run=dry_run,
            )

        if validated_postconditions:
            self._event(
                run_id,
                skill,
                RuntimeEventType.VALIDATION_SUCCEEDED,
                payload={"validated_rule_ids": sorted(set(validated_postconditions))},
            )
        self._event(run_id, skill, RuntimeEventType.RUN_SUCCEEDED, payload={"dry_run": dry_run})
        return RunResult(run_id, RunStatus.SUCCEEDED, outputs=outputs)

    @staticmethod
    def _encode_recovery_parameters(
        parameters: dict[str, Any],
        *,
        external_resource_id: str | None,
    ) -> dict[str, dict[str, str]]:
        encoded: dict[str, dict[str, str]] = {}
        for name, value in parameters.items():
            if external_resource_id is None or value != external_resource_id:
                raise ValueError(
                    "recovery parameters may persist only external_resource_id references"
                )
            encoded[name] = {"$runtime_ref": "external_resource_id"}
        return encoded

    def _queue_compensation(
        self,
        run_id: str,
        skill: dict[str, str],
        *,
        source_action_id: str,
        compensation: dict[str, Any],
        idempotency_key: str | None,
        external_resource_id: str | None,
        dry_run: bool,
    ) -> bool:
        if compensation.get("strategy") != "auto_rollback":
            return False
        self._event(
            run_id,
            skill,
            RuntimeEventType.COMPENSATION_QUEUED,
            action_id=compensation["action_id"],
            idempotency_key=idempotency_key,
            external_resource_id=external_resource_id,
            payload={"source_action_id": source_action_id, "dry_run": dry_run},
        )
        return True

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
