from __future__ import annotations

import copy
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import sqlite3
from threading import Barrier

import pytest

import runtime.ledger as runtime_ledger_module
from runtime.ledger import RuntimeLedger
from runtime.models import ActionResult, RunStatus, RuntimeEvent, RuntimeEventType
from runtime.orchestrator import RuntimeOrchestrator
from runtime.recovery import RecoveryCoordinator
from runtime.rules import ContextRuleEvaluator


TEST_BINDING_KEY = "skill0-test-runtime-binding-key-0123456789"


class ApprovedGovernanceGate:
    def evaluate(self, skill_document, contract):
        return {
            "policy": "governance.current_revision.approved",
            "canonical_skill_id": skill_document["meta"]["skill_id"],
            "governance_skill_id": "governance-runtime-hitl-test",
            "revision_id": "rev-runtime-hitl-test",
            "revision_number": 1,
            "artifact_digest": "sha256:" + "b" * 64,
            "approved_by": "reviewer",
            "approved_at": "2026-07-16T00:00:00+00:00",
        }


GOVERNANCE_GATE = ApprovedGovernanceGate()


class RecordingAdapter:
    supports_dry_run = True

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.compensation_calls: list[str] = []

    def execute(self, action_id, parameters, *, dry_run):
        assert dry_run is True
        self.calls.append(action_id)
        resource_id = f"resource-{action_id}"
        return ActionResult(
            True,
            outputs={"id": resource_id},
            external_resource_id=resource_id,
        )

    def compensate(
        self, action_id, parameters, *, idempotency_key, dry_run
    ):
        del parameters, idempotency_key
        assert dry_run is True
        self.compensation_calls.append(action_id)
        return ActionResult(True, outputs={"compensated": True})


def skill_document_for(contract):
    return {
        "meta": {
            "skill_id": "claude__skill__runtime_hitl_fixture",
            "name": contract["skill_ref"]["name"],
            "skill_layer": "claude_skill",
            "title": contract["skill_ref"]["name"],
            "description": "Runtime HITL ledger fixture",
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
                    "description": "Runtime HITL action fixture",
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
                    "description": "Runtime HITL rule fixture",
                }
                for binding in contract["governance"]["rule_policy_bindings"]
            ],
            "directives": [
                {
                    "id": directive_id,
                    "name": directive_id,
                    "directive_type": "completion",
                    "description": "Runtime HITL directive fixture",
                    "decomposable": False,
                }
                for directive_id in contract["directive_manifest"]["include"]
            ],
        },
    }


def run_until_approval(ledger, adapter, contract, *, parameters):
    rule_results = {
        binding["rule_id"]: True
        for binding in contract["governance"]["rule_policy_bindings"]
    }
    return RuntimeOrchestrator(
        ledger,
        adapter,
        ContextRuleEvaluator(),
        binding_key=TEST_BINDING_KEY,
        governance_gate=GOVERNANCE_GATE,
    ).run(
        contract,
        skill_document_for(contract),
        parameters=parameters,
        context={"rule_results": rule_results},
    )


def execution_basis(tag: str) -> dict[str, object]:
    return {
        "skill_id": "claude__skill__runtime_hitl_fixture",
        "governance_revision_id": f"revision-{tag}",
        "skill_source_digest": f"skill-{tag}",
        "contract_digest": f"contract-{tag}",
        "input_digest": f"input-{tag}",
        "preflight_digest": f"preflight-{tag}",
        "execution_digest": f"execution-{tag}",
        "dry_run": True,
    }


def test_orchestrator_automatically_binds_action_approval_item_to_execution_basis(
    tmp_path, read_json
):
    contract = read_json("examples/runtime-contract.manual-approval.json")
    adapter = RecordingAdapter()

    with RuntimeLedger(tmp_path / "runtime.db") as ledger:
        result = run_until_approval(
            ledger,
            adapter,
            contract,
            parameters={"branch": "old"},
        )

        assert result.status == RunStatus.AWAITING_APPROVAL
        assert adapter.calls == []
        [item] = ledger.list_hitl_items(status="pending", run_id=result.run_id)
        basis = ledger.get_execution_basis(result.run_id)
        assert item["kind"] == "action_approval"
        assert item["action_id"] == "a_010"
        assert item["basis_digest"] == basis["execution_digest"]
        assert item["skill_id"] == "claude__skill__runtime_hitl_fixture"
        assert item["request_summary"] == {
            "approval_required": True,
            "compensation_strategy": "manual_approval",
            "effect_classification": "destructive_write",
            "operation": "delete_branch",
            "resource_kind": "git",
            "risk_level": "high",
        }


def test_orchestrator_ignores_caller_supplied_approval_hints(tmp_path, read_json):
    contract = read_json("examples/runtime-contract.manual-approval.json")
    adapter = RecordingAdapter()
    with RuntimeLedger(tmp_path / "runtime.db") as ledger:
        result = RuntimeOrchestrator(
            ledger,
            adapter,
            ContextRuleEvaluator(),
            binding_key=TEST_BINDING_KEY,
            governance_gate=GOVERNANCE_GATE,
        ).run(
            contract,
            skill_document_for(contract),
            parameters={"branch": "old"},
            context={
                "approved_action_ids": ["a_010"],
                "rule_results": {"r_010": True},
            },
        )
        assert result.status == RunStatus.AWAITING_APPROVAL
        assert adapter.calls == []


def test_action_decision_is_single_immutable_and_replay_is_rejected(
    tmp_path, read_json
):
    contract = read_json("examples/runtime-contract.manual-approval.json")

    with RuntimeLedger(tmp_path / "runtime.db") as ledger:
        result = run_until_approval(
            ledger,
            RecordingAdapter(),
            contract,
            parameters={"branch": "old"},
        )
        [item] = ledger.list_hitl_items(status="pending", run_id=result.run_id)

        decided = ledger.decide_hitl_item(
            item_id=item["item_id"],
            decision="approve",
            actor="reviewer-1",
            reason_code="REVIEWED",
        )

        assert decided["status"] == "approved"
        assert ledger.get_run(result.run_id)["status"] == RunStatus.READY.value
        [decision] = ledger.list_hitl_decisions(item["item_id"])
        assert decision["decision"] == "approve"
        assert decision["actor"] == "reviewer-1"
        assert decision["reason_code"] == "REVIEWED"
        assert ledger.count_events(
            result.run_id, RuntimeEventType.APPROVAL_GRANTED
        ) == 1

        with pytest.raises(ValueError, match="no longer pending"):
            ledger.decide_hitl_item(
                item_id=item["item_id"],
                decision="reject",
                actor="reviewer-2",
                reason_code="CONFLICTING_REPLAY",
            )
        assert len(ledger.list_hitl_decisions(item["item_id"])) == 1
        assert ledger.count_events(
            result.run_id, RuntimeEventType.APPROVAL_GRANTED
        ) == 1
        assert ledger.count_events(
            result.run_id, RuntimeEventType.APPROVAL_REJECTED
        ) == 0

        with pytest.raises(sqlite3.DatabaseError, match="immutable"):
            ledger.connection.execute(
                "UPDATE runtime_hitl_decisions SET reason_code='ALTERED' "
                "WHERE item_id=?",
                (item["item_id"],),
            )
        with pytest.raises(sqlite3.DatabaseError, match="projection update"):
            ledger.connection.execute(
                "UPDATE runtime_hitl_items SET status='rejected' WHERE item_id=?",
                (item["item_id"],),
            )
        with pytest.raises(sqlite3.DatabaseError, match="immutable"):
            ledger.connection.execute(
                "DELETE FROM runtime_hitl_decisions WHERE item_id=?",
                (item["item_id"],),
            )


def test_pending_hitl_item_expires_and_cannot_be_decided(
    tmp_path, read_json, monkeypatch
):
    contract = read_json("examples/runtime-contract.manual-approval.json")
    with RuntimeLedger(tmp_path / "runtime.db", hitl_ttl_seconds=300) as ledger:
        result = run_until_approval(
            ledger,
            RecordingAdapter(),
            contract,
            parameters={"branch": "old"},
        )
        [item] = ledger.list_hitl_items(status="pending", run_id=result.run_id)
        expiry = datetime.fromisoformat(item["expires_at"])

        class FrozenDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                instant = expiry + timedelta(seconds=1)
                return instant if tz is None else instant.astimezone(tz)

        monkeypatch.setattr(runtime_ledger_module, "datetime", FrozenDateTime)

        assert ledger.get_hitl_item(item["item_id"])["status"] == "expired"
        assert ledger.list_hitl_items(status="pending", run_id=result.run_id) == []
        [expired] = ledger.list_hitl_items(status="expired", run_id=result.run_id)
        assert expired["item_id"] == item["item_id"]
        with pytest.raises(ValueError, match="expired"):
            ledger.decide_hitl_item(
                item_id=item["item_id"],
                decision="approve",
                actor="reviewer-1",
                reason_code="REVIEWED",
            )
        assert ledger.list_hitl_decisions(item["item_id"]) == []


def test_approved_hitl_item_expires_before_resume_claim(
    tmp_path, read_json, monkeypatch
):
    contract = read_json("examples/runtime-contract.manual-approval.json")
    with RuntimeLedger(tmp_path / "runtime.db", hitl_ttl_seconds=300) as ledger:
        result = run_until_approval(
            ledger,
            RecordingAdapter(),
            contract,
            parameters={"branch": "old"},
        )
        [item] = ledger.list_hitl_items(status="pending", run_id=result.run_id)
        approved = ledger.decide_hitl_item(
            item_id=item["item_id"],
            decision="approve",
            actor="reviewer-1",
            reason_code="REVIEWED",
        )
        expiry = datetime.fromisoformat(approved["expires_at"])

        class FrozenDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                instant = expiry + timedelta(seconds=1)
                return instant if tz is None else instant.astimezone(tz)

        monkeypatch.setattr(runtime_ledger_module, "datetime", FrozenDateTime)

        assert ledger.get_hitl_item(item["item_id"])["status"] == "expired"
        with pytest.raises(ValueError, match="expired"):
            ledger.claim_hitl_resume(
                item_id=item["item_id"],
                run_id=result.run_id,
                basis_digest=item["basis_digest"],
            )
        assert ledger.connection.execute(
            "SELECT COUNT(*) FROM runtime_resume_claims"
        ).fetchone()[0] == 0

def test_reject_and_confirm_project_terminal_ledger_states(tmp_path, read_json):
    contract = read_json("examples/runtime-contract.manual-approval.json")

    with RuntimeLedger(tmp_path / "runtime.db") as ledger:
        rejected_run = run_until_approval(
            ledger,
            RecordingAdapter(),
            contract,
            parameters={"branch": "old"},
        )
        [action_item] = ledger.list_hitl_items(
            status="pending", run_id=rejected_run.run_id
        )
        rejected = ledger.decide_hitl_item(
            item_id=action_item["item_id"],
            decision="reject",
            actor="reviewer-1",
            reason_code="RISK_REJECTED",
        )
        assert rejected["status"] == "rejected"
        assert ledger.get_run(rejected_run.run_id)["status"] == RunStatus.DENIED.value
        assert ledger.count_events(
            rejected_run.run_id, RuntimeEventType.APPROVAL_REJECTED
        ) == 1

        basis = execution_basis("recovery")
        recovery_run_id = ledger.create_run(
            skill_name="Recovery Fixture",
            skill_version="1",
            execution_basis=basis,
        )
        ledger.append_event(
            RuntimeEvent(
                run_id=recovery_run_id,
                event_type=RuntimeEventType.RUN_SUSPENDED,
                skill_name="Recovery Fixture",
                skill_version="1",
                action_id="a_099",
                payload={"reason": "manual recovery confirmation required"},
            )
        )
        recovery_item = ledger.create_hitl_item(
            run_id=recovery_run_id,
            skill_id=str(basis["skill_id"]),
            action_id="a_099",
            kind="recovery_confirmation",
            basis_digest=str(basis["execution_digest"]),
            request_summary={"strategy": "manual_approval"},
        )
        confirmed = ledger.decide_hitl_item(
            item_id=recovery_item["item_id"],
            decision="confirm_recovered",
            actor="operator-1",
            reason_code="RECOVERY_VERIFIED",
        )
        assert confirmed["status"] == "confirmed"
        assert ledger.get_run(recovery_run_id)["status"] == RunStatus.RECOVERY_PENDING.value
        assert ledger.count_events(
            recovery_run_id, RuntimeEventType.MANUAL_RECOVERY_CONFIRMED
        ) == 1


def test_same_run_resume_skips_action_that_succeeded_before_approval(
    tmp_path, read_json
):
    contract = copy.deepcopy(read_json("examples/runtime-contract.auto-rollback.json"))
    approval_contract = read_json("examples/runtime-contract.manual-approval.json")
    contract["action_bindings"].append(approval_contract["action_bindings"][0])
    contract["governance"]["rule_policy_bindings"].append(
        approval_contract["governance"]["rule_policy_bindings"][0]
    )
    contract["directive_manifest"]["include"].extend(
        approval_contract["directive_manifest"]["include"]
    )
    parameters = {"customer_id": "42", "branch": "old"}
    context = {"rule_results": {"r_001": True, "r_002": True, "r_010": True}}
    skill = skill_document_for(contract)
    adapter = RecordingAdapter()

    with RuntimeLedger(tmp_path / "runtime.db") as ledger:
        orchestrator = RuntimeOrchestrator(
            ledger,
            adapter,
            ContextRuleEvaluator(),
            binding_key=TEST_BINDING_KEY,
            governance_gate=GOVERNANCE_GATE,
        )
        waiting = orchestrator.run(
            contract,
            skill,
            parameters=parameters,
            context=context,
        )
        assert waiting.status == RunStatus.AWAITING_APPROVAL
        assert adapter.calls == ["a_001"]
        [item] = ledger.list_hitl_items(status="pending", run_id=waiting.run_id)
        assert item["action_id"] == "a_010"

        ledger.decide_hitl_item(
            item_id=item["item_id"],
            decision="approve",
            actor="reviewer-1",
            reason_code="REVIEWED",
        )
        completed = orchestrator.run(
            contract,
            skill,
            parameters=parameters,
            context=context,
            existing_run_id=waiting.run_id,
            resume_item_id=item["item_id"],
        )

        assert completed.run_id == waiting.run_id
        assert completed.status == RunStatus.SUCCEEDED
        assert adapter.calls == ["a_001", "a_010"]
        assert ledger.count_events(
            waiting.run_id, RuntimeEventType.ACTION_SUCCEEDED
        ) == 2
        assert ledger.count_events(waiting.run_id, RuntimeEventType.PLAN_CREATED) == 1
        assert ledger.count_events(
            waiting.run_id, RuntimeEventType.PREFLIGHT_PASSED
        ) == 1


def test_concurrent_hitl_decisions_have_exactly_one_winner(tmp_path, read_json):
    database = tmp_path / "runtime.db"
    contract = read_json("examples/runtime-contract.manual-approval.json")
    with RuntimeLedger(database) as ledger:
        result = run_until_approval(
            ledger,
            RecordingAdapter(),
            contract,
            parameters={"branch": "old"},
        )
        [item] = ledger.list_hitl_items(status="pending", run_id=result.run_id)

    barrier = Barrier(2)

    def decide(decision):
        with RuntimeLedger(database) as competing:
            barrier.wait(timeout=5)
            try:
                competing.decide_hitl_item(
                    item_id=item["item_id"],
                    decision=decision,
                    actor=f"reviewer-{decision}",
                    reason_code="CONCURRENT_REVIEW",
                )
            except ValueError:
                return "conflict"
            return "committed"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(decide, ["approve", "reject"]))
    assert sorted(outcomes) == ["committed", "conflict"]

    with RuntimeLedger(database) as ledger:
        assert len(ledger.list_hitl_decisions(item["item_id"])) == 1
        assert sum(
            ledger.count_events(result.run_id, event_type)
            for event_type in (
                RuntimeEventType.APPROVAL_GRANTED,
                RuntimeEventType.APPROVAL_REJECTED,
            )
        ) == 1


def test_hitl_decision_rolls_back_when_event_append_fails(
    tmp_path, read_json, monkeypatch
):
    contract = read_json("examples/runtime-contract.manual-approval.json")
    with RuntimeLedger(tmp_path / "runtime.db") as ledger:
        result = run_until_approval(
            ledger,
            RecordingAdapter(),
            contract,
            parameters={"branch": "old"},
        )
        [item] = ledger.list_hitl_items(status="pending", run_id=result.run_id)

        def fail_event_append(*args, **kwargs):
            del args, kwargs
            raise RuntimeError("injected event failure")

        monkeypatch.setattr(ledger, "_append_event_in_transaction", fail_event_append)
        with pytest.raises(RuntimeError, match="injected event failure"):
            ledger.decide_hitl_item(
                item_id=item["item_id"],
                decision="approve",
                actor="reviewer-1",
                reason_code="REVIEWED",
            )

        assert ledger.get_hitl_item(item["item_id"])["status"] == "pending"
        assert ledger.list_hitl_decisions(item["item_id"]) == []
        assert ledger.get_run(result.run_id)["status"] == RunStatus.AWAITING_APPROVAL.value


def test_concurrent_resume_claims_have_exactly_one_winner(tmp_path, read_json):
    database = tmp_path / "runtime.db"
    contract = read_json("examples/runtime-contract.manual-approval.json")
    with RuntimeLedger(database) as ledger:
        result = run_until_approval(
            ledger,
            RecordingAdapter(),
            contract,
            parameters={"branch": "old"},
        )
        [item] = ledger.list_hitl_items(status="pending", run_id=result.run_id)
        ledger.decide_hitl_item(
            item_id=item["item_id"],
            decision="approve",
            actor="reviewer-1",
            reason_code="REVIEWED",
        )
        basis_digest = ledger.get_execution_basis(result.run_id)["execution_digest"]

    barrier = Barrier(2)

    def claim():
        with RuntimeLedger(database) as competing:
            barrier.wait(timeout=5)
            try:
                competing.claim_hitl_resume(
                    item_id=item["item_id"],
                    run_id=result.run_id,
                    basis_digest=basis_digest,
                )
            except ValueError:
                return "conflict"
            return "claimed"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _: claim(), range(2)))
    assert sorted(outcomes) == ["claimed", "conflict"]

    with RuntimeLedger(database) as ledger:
        [claim_row] = ledger.connection.execute(
            "SELECT * FROM runtime_resume_claims WHERE item_id=?",
            (item["item_id"],),
        ).fetchall()
        assert claim_row["run_id"] == result.run_id
        with pytest.raises(sqlite3.DatabaseError, match="immutable"):
            ledger.connection.execute(
                "DELETE FROM runtime_resume_claims WHERE item_id=?",
                (item["item_id"],),
            )


def test_resume_claim_crash_gap_becomes_reconciliation_required(
    tmp_path, read_json
):
    contract = read_json("examples/runtime-contract.manual-approval.json")
    adapter = RecordingAdapter()
    with RuntimeLedger(tmp_path / "runtime.db") as ledger:
        waiting = run_until_approval(
            ledger, adapter, contract, parameters={"branch": "old"}
        )
        [item] = ledger.list_hitl_items(status="pending", run_id=waiting.run_id)
        ledger.decide_hitl_item(
            item_id=item["item_id"],
            decision="approve",
            actor="reviewer-1",
            reason_code="REVIEWED",
        )
        basis = ledger.get_execution_basis(waiting.run_id)
        ledger.claim_hitl_resume(
            item_id=item["item_id"],
            run_id=waiting.run_id,
            basis_digest=basis["execution_digest"],
        )
        assert ledger.get_run(waiting.run_id)["status"] == RunStatus.RUNNING.value
        assert ledger.count_events(
            waiting.run_id, RuntimeEventType.RUN_RESUME_STARTED
        ) == 1

        recovered = RecoveryCoordinator(ledger, adapter).recover(waiting.run_id)
        assert recovered == RunStatus.RECONCILIATION_REQUIRED
        assert adapter.calls == []
        assert ledger.get_run(waiting.run_id)["status"] == (
            RunStatus.RECONCILIATION_REQUIRED.value
        )


def test_resume_claim_and_attempt_event_are_atomic(tmp_path, read_json, monkeypatch):
    contract = read_json("examples/runtime-contract.manual-approval.json")
    with RuntimeLedger(tmp_path / "runtime.db") as ledger:
        waiting = run_until_approval(
            ledger, RecordingAdapter(), contract, parameters={"branch": "old"}
        )
        [item] = ledger.list_hitl_items(status="pending", run_id=waiting.run_id)
        ledger.decide_hitl_item(
            item_id=item["item_id"],
            decision="approve",
            actor="reviewer-1",
            reason_code="REVIEWED",
        )
        basis = ledger.get_execution_basis(waiting.run_id)

        def fail_event_append(*args, **kwargs):
            del args, kwargs
            raise RuntimeError("injected resume event failure")

        monkeypatch.setattr(ledger, "_append_event_in_transaction", fail_event_append)
        with pytest.raises(RuntimeError, match="injected resume event failure"):
            ledger.claim_hitl_resume(
                item_id=item["item_id"],
                run_id=waiting.run_id,
                basis_digest=basis["execution_digest"],
            )
        assert ledger.connection.execute(
            "SELECT COUNT(*) FROM runtime_resume_claims WHERE item_id=?",
            (item["item_id"],),
        ).fetchone()[0] == 0
        assert ledger.get_run(waiting.run_id)["status"] == RunStatus.READY.value


def test_manual_recovery_confirmation_closes_only_its_action(
    tmp_path, read_json
):
    contract = copy.deepcopy(read_json("examples/runtime-contract.auto-rollback.json"))
    manual = read_json("examples/runtime-contract.manual-approval.json")
    contract["action_bindings"].append(manual["action_bindings"][0])
    contract["governance"]["rule_policy_bindings"].append(
        manual["governance"]["rule_policy_bindings"][0]
    )
    contract["directive_manifest"]["include"].extend(
        manual["directive_manifest"]["include"]
    )
    parameters = {"customer_id": "42", "branch": "old"}
    context = {"rule_results": {"r_001": True, "r_002": True, "r_010": True}}
    skill = skill_document_for(contract)
    adapter = RecordingAdapter()

    with RuntimeLedger(tmp_path / "runtime.db") as ledger:
        orchestrator = RuntimeOrchestrator(
            ledger,
            adapter,
            ContextRuleEvaluator(),
            binding_key=TEST_BINDING_KEY,
            governance_gate=GOVERNANCE_GATE,
        )
        waiting = orchestrator.run(
            contract, skill, parameters=parameters, context=context
        )
        [approval] = ledger.list_hitl_items(
            status="pending", run_id=waiting.run_id
        )
        ledger.decide_hitl_item(
            item_id=approval["item_id"],
            decision="approve",
            actor="reviewer-1",
            reason_code="REVIEWED",
        )
        completed = orchestrator.run(
            contract,
            skill,
            parameters=parameters,
            context=context,
            existing_run_id=waiting.run_id,
            resume_item_id=approval["item_id"],
        )
        assert completed.status == RunStatus.SUCCEEDED

        assert RecoveryCoordinator(ledger, adapter).recover(waiting.run_id) == (
            RunStatus.HITL_REQUIRED
        )
        [recovery_item] = ledger.list_hitl_items(
            status="pending", run_id=waiting.run_id
        )
        ledger.decide_hitl_item(
            item_id=recovery_item["item_id"],
            decision="confirm_recovered",
            actor="reviewer-1",
            reason_code="RECOVERY_VERIFIED",
        )
        assert ledger.get_run(waiting.run_id)["status"] == (
            RunStatus.RECOVERY_PENDING.value
        )
        assert adapter.compensation_calls == []
        remaining = list(ledger.iter_recovery_candidates(waiting.run_id))
        assert [event.action_id for event in remaining] == ["a_001"]

        assert RecoveryCoordinator(ledger, adapter).recover(waiting.run_id) == (
            RunStatus.COMPENSATED
        )
        assert adapter.compensation_calls == ["a_002"]
        assert list(ledger.iter_recovery_candidates(waiting.run_id)) == []
