from __future__ import annotations

import pytest

from runtime.executor import ActionResult
from runtime.ledger import RuntimeLedger
from runtime.models import RunStatus, RuntimeEventType
from runtime.orchestrator import RuntimeOrchestrator
from runtime.rules import ContextRuleEvaluator
from runtime.validators import RuntimeContractValidationError


class DryRunAdapter:
    supports_dry_run = True

    def execute(self, action_id, parameters, *, dry_run):
        assert dry_run is True
        return ActionResult(True, outputs={"id": f"resource-{action_id}"})


def skill_document_for(contract):
    return {
        "meta": {
            "skill_id": "claude__skill__runtime_fixture",
            "name": contract["skill_ref"]["name"],
            "skill_layer": "claude_skill",
            "title": contract["skill_ref"]["name"],
            "description": "Runtime contract test fixture",
            "schema_version": "2.4.0",
            "parse_timestamp": "2026-07-16T00:00:00Z",
            "version": contract["skill_ref"]["version"],
        },
        "decomposition": {
            "actions": [
                {
                    "id": binding["action_id"],
                    "name": binding["action_id"],
                    "action_type": "transform",
                    "description": "Runtime action fixture",
                    "deterministic": True,
                    "immutable_elements": [],
                    "mutable_elements": [],
                    "side_effects": [],
                }
                for binding in contract["action_bindings"]
            ],
            "rules": [
                {
                    "id": binding["rule_id"],
                    "name": binding["rule_id"],
                    "condition_type": "validation",
                    "condition_expression": "fixture",
                    "returns": "boolean",
                    "description": "Runtime rule fixture",
                }
                for binding in contract["governance"]["rule_policy_bindings"]
            ],
            "directives": [
                {
                    "id": directive_id,
                    "name": directive_id,
                    "directive_type": "completion",
                    "description": "Runtime directive fixture",
                    "decomposable": False,
                }
                for directive_id in contract["directive_manifest"]["include"]
            ],
        },
    }


def test_orchestrator_records_attested_preflight(tmp_path, read_json):
    contract = read_json("examples/runtime-contract.read-only.json")
    with RuntimeLedger(tmp_path / "runtime.db") as ledger:
        result = RuntimeOrchestrator(
            ledger, DryRunAdapter(), ContextRuleEvaluator()
        ).run(
            contract,
            skill_document_for(contract),
            parameters={},
            context={"rule_results": {"r_001": True}},
        )
        assert result.status == RunStatus.SUCCEEDED
        event = next(
            event
            for event in ledger.list_events(result.run_id)
            if event.event_type == RuntimeEventType.PREFLIGHT_PASSED
        )
        assert event.payload["schema_validated"] is True
        assert event.payload["skill_schema_validated"] is True
        assert event.payload["cross_references_validated"] is True
        assert event.payload["precondition_rule_ids"] == ["r_001"]


def test_orchestrator_fails_closed_when_rule_result_is_missing(tmp_path, read_json):
    contract = read_json("examples/runtime-contract.read-only.json")
    with RuntimeLedger(tmp_path / "runtime.db") as ledger:
        with pytest.raises(RuntimeContractValidationError, match="no boolean dry-run result"):
            RuntimeOrchestrator(
                ledger, DryRunAdapter(), ContextRuleEvaluator()
            ).run(contract, skill_document_for(contract), parameters={}, context={})
        count = ledger.connection.execute("SELECT COUNT(*) FROM runtime_runs").fetchone()[0]
        assert count == 0


def test_orchestrator_rejects_cross_reference_drift(tmp_path, read_json):
    contract = read_json("examples/runtime-contract.read-only.json")
    skill = skill_document_for(contract)
    skill["decomposition"]["actions"] = []
    with RuntimeLedger(tmp_path / "runtime.db") as ledger:
        with pytest.raises(RuntimeContractValidationError, match="Unknown Action reference"):
            RuntimeOrchestrator(
                ledger, DryRunAdapter(), ContextRuleEvaluator()
            ).run(
                contract,
                skill,
                parameters={},
                context={"rule_results": {"r_001": True}},
            )


def test_orchestrator_rejects_skill_identity_mismatch(tmp_path, read_json):
    contract = read_json("examples/runtime-contract.read-only.json")
    skill = skill_document_for(contract)
    skill["meta"]["name"] = "Different Skill"
    with RuntimeLedger(tmp_path / "runtime.db") as ledger:
        with pytest.raises(RuntimeContractValidationError, match="skill_ref.name"):
            RuntimeOrchestrator(
                ledger, DryRunAdapter(), ContextRuleEvaluator()
            ).run(
                contract,
                skill,
                parameters={},
                context={"rule_results": {"r_001": True}},
            )
