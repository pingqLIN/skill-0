from __future__ import annotations

import copy

from runtime.executor import RuntimeExecutor
from runtime.ledger import RuntimeLedger
from runtime.models import ActionResult, RunStatus, RuntimeEventType
from runtime.rules import ContextRuleEvaluator


PREFLIGHT = {
    "schema_validated": True,
    "skill_schema_validated": True,
    "cross_references_validated": True,
    "skill_identity_validated": True,
    "precondition_rule_ids": [],
}


def _run(executor, contract, *, parameters, context=None, dry_run=True):
    context = dict(context or {})
    rule_bindings = {
        item["rule_id"]: item["evaluator"]
        for item in contract.get("governance", {}).get("rule_policy_bindings", [])
    }
    context.setdefault("rule_results", {rule_id: True for rule_id in rule_bindings})
    return executor.run(
        contract,
        parameters=parameters,
        context=context,
        dry_run=dry_run,
        preflight=PREFLIGHT,
        rule_evaluator=ContextRuleEvaluator(),
        rule_bindings=rule_bindings,
    )


class FakeAdapter:
    supports_dry_run = True

    def __init__(self, *, raise_error: bool = False):
        self.raise_error = raise_error
        self.calls: list[tuple[str, bool]] = []

    def execute(self, action_id, parameters, *, dry_run):
        self.calls.append((action_id, dry_run))
        if self.raise_error:
            raise RuntimeError("simulated adapter failure")
        return ActionResult(
            True,
            outputs={"id": "resource-1", "dry_run": dry_run, "action_id": action_id},
            external_resource_id="resource-1",
            compensation_parameters={"hidden": "not-authoritative"},
        )


class NoDryRunAdapter(FakeAdapter):
    supports_dry_run = False


def test_read_only_dry_run_succeeds(tmp_path, read_json):
    adapter = FakeAdapter()
    with RuntimeLedger(tmp_path / "ledger.db") as ledger:
        result = _run(
            RuntimeExecutor(ledger, adapter),
            read_json("examples/runtime-contract.read-only.json"),
            parameters={},
        )
        assert result.status == RunStatus.SUCCEEDED
        assert adapter.calls == [("a_001", True)]
        event_types = [event.event_type for event in ledger.list_events(result.run_id)]
        assert RuntimeEventType.RUN_SUCCEEDED in event_types


def test_dry_run_requires_adapter_attestation(tmp_path, read_json):
    adapter = NoDryRunAdapter()
    with RuntimeLedger(tmp_path / "ledger.db") as ledger:
        result = _run(
            RuntimeExecutor(ledger, adapter),
            read_json("examples/runtime-contract.read-only.json"),
            parameters={},
        )
        assert result.status == RunStatus.DENIED
        assert adapter.calls == []


def test_destructive_write_waits_for_action_scoped_approval(tmp_path, read_json):
    adapter = FakeAdapter()
    with RuntimeLedger(tmp_path / "ledger.db") as ledger:
        result = _run(
            RuntimeExecutor(ledger, adapter),
            read_json("examples/runtime-contract.manual-approval.json"),
            parameters={"branch": "old"},
        )
        assert result.status == RunStatus.AWAITING_APPROVAL
        assert adapter.calls == []


def test_approved_destructive_dry_run_executes(tmp_path, read_json):
    adapter = FakeAdapter()
    contract = read_json("examples/runtime-contract.manual-approval.json")
    with RuntimeLedger(tmp_path / "ledger.db") as ledger:
        result = _run(
            RuntimeExecutor(ledger, adapter),
            contract,
            parameters={"branch": "old"},
            context={"approved_action_ids": ["a_010"]},
        )
        assert result.status == RunStatus.SUCCEEDED
        assert adapter.calls == [("a_010", True)]


def test_real_execution_requires_explicit_feature_flag(tmp_path, read_json):
    adapter = FakeAdapter()
    contract = read_json("examples/runtime-contract.read-only.json")
    with RuntimeLedger(tmp_path / "ledger.db") as ledger:
        result = _run(RuntimeExecutor(ledger, adapter), contract, parameters={}, dry_run=False)
        assert result.status == RunStatus.DENIED
        assert adapter.calls == []


def test_bounded_write_records_declared_compensation_mapping(tmp_path, read_json):
    with RuntimeLedger(tmp_path / "ledger.db") as ledger:
        result = _run(
            RuntimeExecutor(ledger, FakeAdapter()),
            read_json("examples/runtime-contract.auto-rollback.json"),
            parameters={"customer_id": "42"},
        )
        assert result.status == RunStatus.SUCCEEDED
        succeeded = [
            event
            for event in ledger.list_events(result.run_id)
            if event.event_type == RuntimeEventType.ACTION_SUCCEEDED
        ]
        assert succeeded[0].payload["resolved_compensation_idempotency_key"] == "contact-delete:resource-1"
        assert succeeded[0].payload["resolved_compensation_parameters"] == {
            "contact_id": {"$runtime_ref": "external_resource_id"}
        }
        assert "hidden" not in succeeded[0].payload["resolved_compensation_parameters"]


def test_read_adapter_exception_is_durably_recorded(tmp_path, read_json):
    with RuntimeLedger(tmp_path / "ledger.db") as ledger:
        result = _run(
            RuntimeExecutor(ledger, FakeAdapter(raise_error=True)),
            read_json("examples/runtime-contract.read-only.json"),
            parameters={},
        )
        assert result.status == RunStatus.FAILED
        failures = [
            event
            for event in ledger.list_events(result.run_id)
            if event.event_type == RuntimeEventType.ACTION_FAILED
        ]
        assert failures[0].payload["error_code"] == "ADAPTER_EXCEPTION"


def test_write_adapter_exception_requires_reconciliation(tmp_path, read_json):
    with RuntimeLedger(tmp_path / "ledger.db") as ledger:
        result = _run(
            RuntimeExecutor(ledger, FakeAdapter(raise_error=True)),
            read_json("examples/runtime-contract.auto-rollback.json"),
            parameters={"customer_id": "42"},
        )
        assert result.status == RunStatus.RECONCILIATION_REQUIRED
        assert ledger.get_run(result.run_id)["status"] == "reconciliation_required"
        assert ledger.count_events(result.run_id, RuntimeEventType.ACTION_OUTCOME_UNKNOWN) == 1


def test_duplicate_primary_idempotency_key_is_rejected_across_runs(tmp_path, read_json):
    contract = read_json("examples/runtime-contract.auto-rollback.json")
    contract["action_bindings"][0]["effect"]["primary_idempotency_key_template"] = "static-primary-key"
    with RuntimeLedger(tmp_path / "ledger.db") as ledger:
        first = _run(RuntimeExecutor(ledger, FakeAdapter()), contract, parameters={"customer_id": "42"})
        second = _run(RuntimeExecutor(ledger, FakeAdapter()), contract, parameters={"customer_id": "42"})
        assert first.status == RunStatus.SUCCEEDED
        assert second.status == RunStatus.FAILED
        assert second.reason == "duplicate primary idempotency key"


def test_missing_compensation_pointer_escalates_after_committed_effect(tmp_path, read_json):
    contract = copy.deepcopy(read_json("examples/runtime-contract.auto-rollback.json"))
    contract["action_bindings"][0]["compensation"]["parameters_mapping"] = {
        "contact_id": "/outputs/missing"
    }
    with RuntimeLedger(tmp_path / "ledger.db") as ledger:
        result = _run(RuntimeExecutor(ledger, FakeAdapter()), contract, parameters={"customer_id": "42"})
        assert result.status == RunStatus.HITL_REQUIRED
        assert ledger.get_run(result.run_id)["status"] == "hitl_required"
        assert ledger.count_events(result.run_id, RuntimeEventType.ACTION_SUCCEEDED) == 1
        assert ledger.count_events(result.run_id, RuntimeEventType.RECONCILIATION_REQUIRED) == 1


def test_missing_primary_template_input_fails_before_adapter_call(tmp_path, read_json):
    adapter = FakeAdapter()
    contract = read_json("examples/runtime-contract.auto-rollback.json")
    with RuntimeLedger(tmp_path / "ledger.db") as ledger:
        result = _run(RuntimeExecutor(ledger, adapter), contract, parameters={})
        assert result.status == RunStatus.FAILED
        assert adapter.calls == []
        assert result.reason == "primary idempotency template error: KeyError"


def test_executor_without_preflight_attestation_denies_without_pass_event(tmp_path, read_json):
    adapter = FakeAdapter()
    with RuntimeLedger(tmp_path / "ledger.db") as ledger:
        result = RuntimeExecutor(ledger, adapter).run(
            read_json("examples/runtime-contract.read-only.json"), parameters={}
        )
        assert result.status == RunStatus.DENIED
        assert adapter.calls == []
        assert ledger.count_events(result.run_id, RuntimeEventType.PREFLIGHT_PASSED) == 0


def test_failed_postcondition_is_recorded_truthfully(tmp_path, read_json):
    contract = read_json("examples/runtime-contract.auto-rollback.json")
    with RuntimeLedger(tmp_path / "ledger.db") as ledger:
        result = _run(
            RuntimeExecutor(ledger, FakeAdapter()),
            contract,
            parameters={"customer_id": "42"},
            context={"rule_results": {"r_001": True, "r_002": False}},
        )
        assert result.status == RunStatus.RECOVERY_PENDING
        assert ledger.count_events(result.run_id, RuntimeEventType.VALIDATION_FAILED) == 1
        assert ledger.get_run(result.run_id)["status"] == "recovery_pending"
        assert ledger.count_events(result.run_id, RuntimeEventType.VALIDATION_SUCCEEDED) == 0
        assert ledger.count_events(result.run_id, RuntimeEventType.RUN_SUCCEEDED) == 0
