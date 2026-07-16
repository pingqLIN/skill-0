from __future__ import annotations

from pathlib import Path
from typing import Any

from .executor import ActionAdapter, RuntimeExecutor
from .ledger import RuntimeLedger
from .models import RunResult
from .policy import PolicyEngine
from .rules import RuleEvaluationError, RuleEvaluator
from .validators import RuntimeContractValidationError, load_json, validate_cross_references, validate_schema


DEFAULT_RUNTIME_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schema" / "skill-runtime-contract.schema.json"
DEFAULT_SKILL_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schema" / "skill-decomposition.schema.json"


def _rule_bindings(contract: dict[str, Any]) -> dict[str, str]:
    return {
        binding["rule_id"]: binding["evaluator"]
        for binding in contract.get("governance", {}).get("rule_policy_bindings", [])
    }


def _validate_skill_identity(skill_document: dict[str, Any], contract: dict[str, Any]) -> None:
    meta = skill_document.get("meta", {})
    skill_ref = contract["skill_ref"]
    problems: list[str] = []
    if meta.get("name") and meta["name"] != skill_ref["name"]:
        problems.append("runtime skill_ref.name does not match skill meta.name")
    if meta.get("version") and str(meta["version"]) != str(skill_ref["version"]):
        problems.append("runtime skill_ref.version does not match skill meta.version")
    expected_digest = skill_ref.get("source_digest")
    actual_digest = meta.get("source_digest")
    if expected_digest and actual_digest != expected_digest:
        problems.append("runtime skill_ref.source_digest does not match skill meta.source_digest")
    if problems:
        raise RuntimeContractValidationError("\n".join(problems))


class RuntimeOrchestrator:
    """Validate and preflight a runtime contract before invoking the executor."""

    def __init__(
        self,
        ledger: RuntimeLedger,
        adapter: ActionAdapter,
        rule_evaluator: RuleEvaluator,
        *,
        policy: PolicyEngine | None = None,
        schema_path: str | Path = DEFAULT_RUNTIME_SCHEMA_PATH,
        skill_schema_path: str | Path = DEFAULT_SKILL_SCHEMA_PATH,
    ) -> None:
        self.ledger = ledger
        self.adapter = adapter
        self.rule_evaluator = rule_evaluator
        self.policy = policy
        self.schema_path = Path(schema_path)
        self.skill_schema_path = Path(skill_schema_path)

    def run(
        self,
        contract: dict[str, Any],
        skill_document: dict[str, Any],
        *,
        parameters: dict[str, Any],
        context: dict[str, Any] | None = None,
        dry_run: bool = True,
    ) -> RunResult:
        validate_schema(contract, load_json(self.schema_path))
        validate_schema(skill_document, load_json(self.skill_schema_path))
        validate_cross_references(skill_document, contract)
        _validate_skill_identity(skill_document, contract)

        context = dict(context or {})
        bindings = _rule_bindings(contract)
        validation_rule_ids = {
            rule_id
            for action in contract["action_bindings"]
            for phase in ("precondition_rule_ids", "postcondition_rule_ids")
            for rule_id in action.get("validation", {}).get(phase, [])
        }
        missing_bindings = sorted(validation_rule_ids - set(bindings))
        if missing_bindings:
            raise RuntimeContractValidationError(
                f"validation Rules have no governance evaluator bindings: {missing_bindings}"
            )
        precondition_ids = [
            rule_id
            for action in contract["action_bindings"]
            if action.get("role", "primary") == "primary"
            for rule_id in action.get("validation", {}).get("precondition_rule_ids", [])
        ]
        for rule_id in precondition_ids:
            evaluator = bindings.get(rule_id)
            if evaluator is None:
                raise RuntimeContractValidationError(
                    f"precondition Rule {rule_id} has no governance evaluator binding"
                )
            try:
                passed = self.rule_evaluator.evaluate(
                    rule_id,
                    evaluator,
                    phase="precondition",
                    parameters=parameters,
                    outputs={},
                    context=context,
                )
            except RuleEvaluationError as exc:
                raise RuntimeContractValidationError(str(exc)) from exc
            if not passed:
                raise RuntimeContractValidationError(f"precondition Rule {rule_id} failed")

        executor = RuntimeExecutor(self.ledger, self.adapter, policy=self.policy)
        return executor.run(
            contract,
            parameters=parameters,
            context=context,
            dry_run=dry_run,
            preflight={
                "schema_validated": True,
                "skill_schema_validated": True,
                "cross_references_validated": True,
                "skill_identity_validated": True,
                "precondition_rule_ids": sorted(set(precondition_ids)),
            },
            rule_evaluator=self.rule_evaluator,
            rule_bindings=bindings,
        )
