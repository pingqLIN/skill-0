from __future__ import annotations

import copy

from runtime.policy import DefaultPolicyEngine


def test_unknown_effect_fails_closed(read_json):
    binding = read_json("examples/runtime-contract.read-only.json")["action_bindings"][0]
    binding["effect"]["classification"] = "mystery"
    assert DefaultPolicyEngine().evaluate(binding, {}).outcome == "deny"


def test_manual_recovery_requires_approval(read_json):
    binding = read_json("examples/runtime-contract.manual-approval.json")["action_bindings"][0]
    decision = DefaultPolicyEngine().evaluate(binding, {})
    assert decision.outcome == "require_approval"


def test_approved_high_risk_action_is_allowed(read_json):
    binding = read_json("examples/runtime-contract.manual-approval.json")["action_bindings"][0]
    decision = DefaultPolicyEngine().evaluate(
        binding, {"approved_action_ids": [binding["action_id"]]}
    )
    assert decision.outcome == "allow"


def test_incomplete_auto_rollback_is_denied(read_json):
    binding = copy.deepcopy(
        read_json("examples/runtime-contract.auto-rollback.json")["action_bindings"][0]
    )
    del binding["compensation"]["idempotency_key_template"]
    assert DefaultPolicyEngine().evaluate(binding, {}).outcome == "deny"


def test_write_without_resource_lock_is_denied(read_json):
    binding = copy.deepcopy(
        read_json("examples/runtime-contract.auto-rollback.json")["action_bindings"][0]
    )
    del binding["effect"]["resource_lock_key_template"]
    assert DefaultPolicyEngine().evaluate(binding, {}).outcome == "deny"


def test_read_only_with_compensation_metadata_is_denied(read_json):
    binding = copy.deepcopy(
        read_json("examples/runtime-contract.read-only.json")["action_bindings"][0]
    )
    binding["compensation"] = {
        "strategy": "human_intervention",
        "escalation_queue": "review",
        "operator_instructions": "review",
    }
    assert DefaultPolicyEngine().evaluate(binding, {}).outcome == "deny"
