from __future__ import annotations

import copy

from runtime.executor import RuntimeExecutor
from runtime.ledger import RuntimeLedger
from runtime.models import ActionResult, RunStatus, RuntimeEvent, RuntimeEventType
from runtime.recovery import RecoveryCoordinator


class RecoveryAdapter:
    supports_dry_run = True

    def __init__(self, compensation_results=None):
        self.execute_calls: list[str] = []
        self.compensation_calls: list[str] = []
        self.compensation_dry_runs: list[bool] = []
        self._results = list(compensation_results or [])

    def execute(self, action_id, parameters, *, dry_run):
        self.execute_calls.append(action_id)
        resource_id = f"{action_id}-resource"
        return ActionResult(
            True,
            outputs={"id": resource_id},
            external_resource_id=resource_id,
        )

    def compensate(self, action_id, parameters, *, idempotency_key, dry_run):
        self.compensation_calls.append(action_id)
        self.compensation_dry_runs.append(dry_run)
        if self._results:
            result = self._results.pop(0)
            if isinstance(result, Exception):
                raise result
            return result
        return ActionResult(True, outputs={"compensated": True})


class NoDryRunRecoveryAdapter(RecoveryAdapter):
    supports_dry_run = False


def two_action_contract(read_json):
    contract = copy.deepcopy(read_json("examples/runtime-contract.auto-rollback.json"))
    first, first_compensation = contract["action_bindings"]

    second = copy.deepcopy(first)
    second["action_id"] = "a_003"
    second["adapter"]["target"] = "create_contact_2"
    second["effect"]["primary_idempotency_key_template"] = (
        "contact-create-2:{input.customer_id}:{run_id}"
    )
    second["effect"]["resource_lock_key_template"] = "contact-2:{input.customer_id}"
    second["compensation"]["action_id"] = "a_004"
    second["compensation"]["idempotency_key_template"] = (
        "contact-delete-2:{external_resource_id}"
    )

    second_compensation = copy.deepcopy(first_compensation)
    second_compensation["action_id"] = "a_004"
    second_compensation["adapter"]["target"] = "delete_contact_2"
    second_compensation["effect"]["primary_idempotency_key_template"] = (
        "contact-delete-2:{input.contact_id}"
    )
    second_compensation["effect"]["resource_lock_key_template"] = (
        "contact-2:{input.contact_id}"
    )
    contract["action_bindings"] = [first, first_compensation, second, second_compensation]
    return contract


def source_compensation_event(ledger, run_id):
    return next(
        event
        for event in ledger.list_events(run_id)
        if event.event_type == RuntimeEventType.ACTION_SUCCEEDED
        and event.payload.get("compensation", {}).get("strategy") == "auto_rollback"
    )


def test_recovery_is_idempotent_after_success_and_reopen(tmp_path, read_json):
    adapter = RecoveryAdapter()
    database = tmp_path / "ledger.db"
    with RuntimeLedger(database) as ledger:
        run = RuntimeExecutor(ledger, adapter).run(
            read_json("examples/runtime-contract.auto-rollback.json"),
            parameters={"customer_id": "42"},
        )
        assert RecoveryCoordinator(ledger, adapter).recover(run.run_id) == RunStatus.COMPENSATED
        assert adapter.compensation_calls == ["a_002"]
        assert ledger.get_run(run.run_id)["status"] == "compensated"
    with RuntimeLedger(database) as reopened:
        assert RecoveryCoordinator(reopened, adapter).recover(run.run_id) == RunStatus.COMPENSATED
        assert adapter.compensation_calls == ["a_002"]
        assert reopened.count_events(run.run_id, RuntimeEventType.RUN_COMPENSATED) == 1


def test_recovery_uses_strict_lifo_order(tmp_path, read_json):
    adapter = RecoveryAdapter()
    with RuntimeLedger(tmp_path / "ledger.db") as ledger:
        run = RuntimeExecutor(ledger, adapter).run(
            two_action_contract(read_json), parameters={"customer_id": "42"}
        )
        assert run.status == RunStatus.SUCCEEDED
        assert RecoveryCoordinator(ledger, adapter).recover(run.run_id) == RunStatus.COMPENSATED
        assert adapter.compensation_calls == ["a_004", "a_002"]


def test_acceptable_terminal_error_counts_as_compensated(tmp_path, read_json):
    adapter = RecoveryAdapter(
        [ActionResult(False, error_code="HTTP_404", error_message="already absent")]
    )
    with RuntimeLedger(tmp_path / "ledger.db") as ledger:
        run = RuntimeExecutor(ledger, adapter).run(
            read_json("examples/runtime-contract.auto-rollback.json"),
            parameters={"customer_id": "42"},
        )
        assert RecoveryCoordinator(ledger, adapter).recover(run.run_id) == RunStatus.COMPENSATED
        success = [
            event
            for event in ledger.list_events(run.run_id)
            if event.event_type == RuntimeEventType.COMPENSATION_SUCCEEDED
        ]
        assert success[0].payload["acceptable_error"] == "HTTP_404"


def test_transient_failure_retries_with_same_idempotency_claim(tmp_path, read_json):
    adapter = RecoveryAdapter(
        [
            ActionResult(False, error_code="HTTP_503", error_message="temporary"),
            ActionResult(True, outputs={"compensated": True}),
        ]
    )
    with RuntimeLedger(tmp_path / "ledger.db") as ledger:
        run = RuntimeExecutor(ledger, adapter).run(
            read_json("examples/runtime-contract.auto-rollback.json"),
            parameters={"customer_id": "42"},
        )
        assert RecoveryCoordinator(ledger, adapter).recover(run.run_id) == RunStatus.COMPENSATED
        assert adapter.compensation_calls == ["a_002", "a_002"]
        assert ledger.count_events(run.run_id, RuntimeEventType.COMPENSATION_RETRY_SCHEDULED) == 1
        source = source_compensation_event(ledger, run.run_id)
        key = source.payload["resolved_compensation_idempotency_key"]
        assert ledger.get_idempotency_claim(key)["action_id"] == "a_002"


def test_retry_exhaustion_moves_run_to_hitl(tmp_path, read_json):
    contract = read_json("examples/runtime-contract.auto-rollback.json")
    contract["action_bindings"][0]["compensation"]["max_retries"] = 1
    adapter = RecoveryAdapter(
        [
            ActionResult(False, error_code="HTTP_500", error_message="failure 1"),
            ActionResult(False, error_code="HTTP_500", error_message="failure 2"),
        ]
    )
    with RuntimeLedger(tmp_path / "ledger.db") as ledger:
        run = RuntimeExecutor(ledger, adapter).run(contract, parameters={"customer_id": "42"})
        assert RecoveryCoordinator(ledger, adapter).recover(run.run_id) == RunStatus.HITL_REQUIRED
        assert len(adapter.compensation_calls) == 2
        assert ledger.get_run(run.run_id)["status"] == "hitl_required"
        assert ledger.count_events(run.run_id, RuntimeEventType.RUN_RECOVERY_FAILED) == 1


def test_restart_after_inflight_compensation_reuses_owned_claim(tmp_path, read_json):
    database = tmp_path / "ledger.db"
    adapter = RecoveryAdapter()
    with RuntimeLedger(database) as ledger:
        run = RuntimeExecutor(ledger, adapter).run(
            read_json("examples/runtime-contract.auto-rollback.json"),
            parameters={"customer_id": "42"},
        )
        source = source_compensation_event(ledger, run.run_id)
        key = source.payload["resolved_compensation_idempotency_key"]
        assert ledger.ensure_idempotency_claim(
            key=key,
            run_id=run.run_id,
            action_id="a_002",
            purpose="compensation",
            claimed_at="2026-01-01T00:00:00+00:00",
        ) == "created"
        ledger.append_event(
            RuntimeEvent(
                run_id=run.run_id,
                event_type=RuntimeEventType.COMPENSATION_STARTED,
                skill_name="Contact Sync",
                skill_version="2.4.0",
                action_id="a_002",
                idempotency_key=key,
                external_resource_id=source.external_resource_id,
                payload={"attempt": 1, "max_attempts": 4, "dry_run": True},
            )
        )
    with RuntimeLedger(database) as reopened:
        assert RecoveryCoordinator(reopened, adapter).recover(run.run_id) == RunStatus.COMPENSATED
        assert adapter.compensation_calls == ["a_002"]
        starts = reopened.count_events(
            run.run_id,
            RuntimeEventType.COMPENSATION_STARTED,
            idempotency_key=key,
        )
        assert starts == 2


def test_manual_recovery_boundary_escalates(tmp_path, read_json):
    adapter = RecoveryAdapter()
    with RuntimeLedger(tmp_path / "ledger.db") as ledger:
        run = RuntimeExecutor(ledger, adapter).run(
            read_json("examples/runtime-contract.manual-approval.json"),
            parameters={"branch": "old"},
            context={"approved_action_ids": ["a_010"]},
        )
        assert run.status == RunStatus.SUCCEEDED
        assert RecoveryCoordinator(ledger, adapter).recover(run.run_id) == RunStatus.HITL_REQUIRED
        assert adapter.compensation_calls == []
        suspended = [
            event
            for event in ledger.list_events(run.run_id)
            if event.event_type == RuntimeEventType.RUN_SUSPENDED
        ]
        assert suspended[0].payload["strategy"] == "manual_approval"


def test_ambiguous_started_action_requires_reconciliation(tmp_path):
    adapter = RecoveryAdapter()
    with RuntimeLedger(tmp_path / "ledger.db") as ledger:
        run_id = ledger.create_run(skill_name="demo", skill_version="1")
        ledger.append_event(
            RuntimeEvent(
                run_id=run_id,
                event_type=RuntimeEventType.ACTION_STARTED,
                skill_name="demo",
                skill_version="1",
                action_id="a_001",
                idempotency_key="ambiguous-key",
                payload={"dry_run": True},
            )
        )
        assert RecoveryCoordinator(ledger, adapter).recover(run_id) == RunStatus.RECONCILIATION_REQUIRED
        assert ledger.get_run(run_id)["status"] == "reconciliation_required"


def test_recovery_dry_run_requires_adapter_attestation(tmp_path, read_json):
    execute_adapter = RecoveryAdapter()
    with RuntimeLedger(tmp_path / "ledger.db") as ledger:
        run = RuntimeExecutor(ledger, execute_adapter).run(
            read_json("examples/runtime-contract.auto-rollback.json"),
            parameters={"customer_id": "42"},
        )
        status = RecoveryCoordinator(ledger, NoDryRunRecoveryAdapter()).recover(run.run_id)
        assert status == RunStatus.HITL_REQUIRED
        assert ledger.get_run(run.run_id)["status"] == "hitl_required"
