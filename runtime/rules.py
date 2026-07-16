from __future__ import annotations

from typing import Any, Protocol


class RuleEvaluationError(ValueError):
    """Raised when a declared runtime rule cannot be evaluated truthfully."""


class RuleEvaluator(Protocol):
    def evaluate(
        self,
        rule_id: str,
        evaluator: str,
        *,
        phase: str,
        parameters: dict[str, Any],
        outputs: dict[str, Any],
        context: dict[str, Any],
    ) -> bool: ...


class ContextRuleEvaluator:
    """Trusted test evaluator for deterministic in-process simulations.

    The host supplies explicit boolean results keyed by ARD Rule ID. This must
    not be exposed as an untrusted API assertion path.
    """

    def evaluate(
        self,
        rule_id: str,
        evaluator: str,
        *,
        phase: str,
        parameters: dict[str, Any],
        outputs: dict[str, Any],
        context: dict[str, Any],
    ) -> bool:
        del evaluator, phase, parameters, outputs
        rule_results = context.get("rule_results", {})
        result = rule_results.get(rule_id) if isinstance(rule_results, dict) else None
        if not isinstance(result, bool):
            raise RuleEvaluationError(f"no boolean dry-run result supplied for Rule {rule_id}")
        return result


class UnavailableRuleEvaluator:
    """Fail closed until a server-owned evaluator registry is available."""

    def evaluate(
        self,
        rule_id: str,
        evaluator: str,
        *,
        phase: str,
        parameters: dict[str, Any],
        outputs: dict[str, Any],
        context: dict[str, Any],
    ) -> bool:
        del evaluator, phase, parameters, outputs, context
        raise RuleEvaluationError(
            f"server-side evaluator is unavailable for Rule {rule_id}"
        )
