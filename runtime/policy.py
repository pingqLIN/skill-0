from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Protocol

from .models import PolicyDecision


class PolicyEngine(Protocol):
    def evaluate(
        self, action_binding: dict[str, Any], context: dict[str, Any]
    ) -> PolicyDecision: ...


def _approved_action_ids(context: dict[str, Any]) -> set[str]:
    value = context.get("approved_action_ids", [])
    if isinstance(value, str):
        return {value}
    if isinstance(value, Iterable):
        return {str(item) for item in value}
    return set()


class DefaultPolicyEngine:
    """Fail-closed policy for the reference dry-run implementation."""

    def evaluate(
        self, action_binding: dict[str, Any], context: dict[str, Any]
    ) -> PolicyDecision:
        action_id = str(action_binding.get("action_id", ""))
        effect = action_binding.get("effect", {})
        risk = action_binding.get("risk", {})
        compensation = action_binding.get("compensation", {})
        classification = effect.get("classification")
        strategy = compensation.get("strategy")
        approved = action_id in _approved_action_ids(context)

        if classification not in {"read_only", "bounded_write", "destructive_write"}:
            return PolicyDecision("deny", f"unknown effect classification: {classification!r}")

        if classification == "read_only":
            if strategy != "none":
                return PolicyDecision("deny", "read-only action must use compensation strategy none")
            return PolicyDecision("allow", "read-only action")

        required_effect = [
            "resource_name",
            "primary_idempotency_key_template",
            "resource_lock_key_template",
        ]
        missing_effect = [name for name in required_effect if not effect.get(name)]
        if effect.get("resource_kind") in {None, "none"} or missing_effect:
            return PolicyDecision(
                "deny",
                f"write action lacks durable effect identity: {missing_effect or ['resource_kind']}",
            )

        if strategy == "auto_rollback":
            required_compensation = [
                "action_id",
                "idempotency_key_template",
                "parameters_mapping",
            ]
            missing_compensation = [
                name for name in required_compensation if name not in compensation
            ]
            if missing_compensation or compensation.get("idempotent") is not True:
                return PolicyDecision(
                    "deny",
                    "auto rollback metadata is incomplete or not explicitly idempotent",
                )
        elif strategy == "manual_approval":
            if not compensation.get("approval_policy") or "review_payload_schema" not in compensation:
                return PolicyDecision("deny", "manual approval metadata is incomplete")
        elif strategy == "human_intervention":
            if not compensation.get("escalation_queue") or not compensation.get(
                "operator_instructions"
            ):
                return PolicyDecision("deny", "human intervention metadata is incomplete")
        else:
            return PolicyDecision("deny", "write action has no admissible recovery strategy")

        requires_approval = (
            classification == "destructive_write"
            or bool(risk.get("approval_required"))
            or strategy in {"manual_approval", "human_intervention"}
        )
        if requires_approval and not approved:
            return PolicyDecision(
                "require_approval",
                "action-scoped approval is required",
                {"action_id": action_id},
            )
        return PolicyDecision("allow", "write contract passed fail-closed policy checks")
