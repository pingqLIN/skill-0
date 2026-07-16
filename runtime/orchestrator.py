from __future__ import annotations

import hmac
from pathlib import Path
from typing import Any

from .certification import ProductionAdapterApprovalGate
from .executor import ActionAdapter, RuntimeExecutor
from .digest import canonical_digest, keyed_digest
from .governance import RuntimeGovernanceGate
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
        binding_key: str,
        governance_gate: RuntimeGovernanceGate,
        policy: PolicyEngine | None = None,
        production_approval_gate: ProductionAdapterApprovalGate | None = None,
        schema_path: str | Path = DEFAULT_RUNTIME_SCHEMA_PATH,
        skill_schema_path: str | Path = DEFAULT_SKILL_SCHEMA_PATH,
    ) -> None:
        self.ledger = ledger
        self.adapter = adapter
        self.rule_evaluator = rule_evaluator
        if len(binding_key) < 32:
            raise ValueError("runtime binding key must contain at least 32 characters")
        self.binding_key = binding_key
        self.governance_gate = governance_gate
        self.policy = policy
        self.production_approval_gate = production_approval_gate
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
        existing_run_id: str | None = None,
        resume_item_id: str | None = None,
    ) -> RunResult:
        validate_schema(contract, load_json(self.schema_path))
        validate_schema(skill_document, load_json(self.skill_schema_path))
        validate_cross_references(skill_document, contract)
        _validate_skill_identity(skill_document, contract)
        governance_attestation = self.governance_gate.evaluate(
            skill_document, contract
        )

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

        preflight = {
            "schema_validated": True,
            "skill_schema_validated": True,
            "cross_references_validated": True,
            "skill_identity_validated": True,
            "governance_validated": True,
            "governance_attestation": governance_attestation,
            "precondition_rule_ids": sorted(set(precondition_ids)),
        }
        if not dry_run:
            if self.production_approval_gate is None:
                raise RuntimeContractValidationError(
                    "production adapter approval gate is unavailable"
                )
            decision = self.production_approval_gate.evaluate(
                self.adapter, contract["action_bindings"]
            )
            if not decision.allowed:
                raise RuntimeContractValidationError(decision.reason)
            preflight["adapter_production_approval"] = decision.attestation
        basis = {
            "skill_id": str(skill_document["meta"]["skill_id"]),
            "governance_revision_id": str(
                governance_attestation["revision_id"]
            ),
            "skill_source_digest": canonical_digest(skill_document),
            "contract_digest": canonical_digest(contract),
            "input_digest": keyed_digest(parameters, key=self.binding_key),
            "preflight_digest": canonical_digest(preflight),
            "dry_run": dry_run,
        }
        basis["execution_digest"] = keyed_digest(
            {
                **basis,
                "action_ids": [
                    binding["action_id"] for binding in contract["action_bindings"]
                ],
            },
            key=self.binding_key,
        )
        if existing_run_id is None:
            existing_run_id = self.ledger.create_run(
                skill_name=contract["skill_ref"]["name"],
                skill_version=contract["skill_ref"]["version"],
                execution_basis=basis,
            )
        else:
            stored_basis = self.ledger.get_execution_basis(existing_run_id)
            if not hmac.compare_digest(
                stored_basis["execution_digest"], basis["execution_digest"]
            ):
                raise RuntimeContractValidationError(
                    "runtime resume execution basis does not match"
                )

        executor = RuntimeExecutor(
            self.ledger,
            self.adapter,
            policy=self.policy,
            production_approval_gate=self.production_approval_gate,
        )
        return executor.run(
            contract,
            parameters=parameters,
            context=context,
            dry_run=dry_run,
            preflight=preflight,
            rule_evaluator=self.rule_evaluator,
            rule_bindings=bindings,
            existing_run_id=existing_run_id,
            execution_basis_digest=str(basis["execution_digest"]),
            resume_item_id=resume_item_id,
        )
