import json
from pathlib import Path

import pytest

from tools.governance_db import GovernanceDB, GovernanceTargetError


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = (
    ROOT / "docs" / "contracts" / "governance-authority-lifecycle-v1.json"
)


def _contract():
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_governance_lifecycle_has_one_exact_authoritative_state():
    contract = _contract()

    assert contract["lifecycle_version"] == "1.2.0"
    assert contract["status"] == "stable-foundation"
    authoritative = [
        state
        for state, definition in contract["states"].items()
        if definition["authoritative"]
    ]
    assert authoritative == ["approved-current"]
    assert contract["states"]["drifted"] == {
        "authoritative": False,
        "stored": False,
    }


def test_governance_lifecycle_freezes_authority_tuple_and_non_authority_sources():
    contract = _contract()

    assert contract["authority_unit"] == [
        "governance_skill_id",
        "current_revision_id",
        "is_current",
        "revision_status_approved",
        "canonical_asset_id",
        "artifact_digest",
        "skill_version",
        "approved_by",
        "approved_at",
    ]
    assert set(contract["non_authority_sources"]) == {
        "skills.status",
        "asset-index",
        "dashboard",
        "knowledge-plane",
        "agent-evaluation",
        "runtime-contract",
        "prior-run-result",
    }


def test_governance_lifecycle_requires_revalidation_and_preserves_history():
    contract = _contract()

    assert contract["runtime"] == {
        "create_revalidates": True,
        "resume_revalidates": True,
        "resume_checks_before_claim": True,
        "historical_events_are_rewritten": False,
        "runtime_hitl_can_grant_governance_authority": False,
    }
    assert contract["implemented_gaps"] == {
        "approval_expiry": False,
        "dedicated_revocation_event": False,
        "approval_quorum": False,
        "cryptographic_audit_chain": False,
        "identical_binding_requires_pending_status": False,
        "reapproval_requires_fresh_evidence": True,
        "reject_target_currentness_enforced": True,
        "scan_target_currentness_enforced": True,
    }
    assert contract["noncurrent_target_effects"] == {
        "reject": {
            "current_authority_changes": False,
            "skills_status_projection_may_change": False,
        },
        "scan-block": {
            "current_authority_changes": False,
            "skills_status_projection_may_change": False,
        },
    }
    assert contract["revision_targeted_writes"] == {
        "approve_currentness_enforced": True,
        "reject_currentness_enforced": True,
        "scan_currentness_enforced": True,
        "equivalence_currentness_enforced": True,
        "stale_job_error_code": "STALE_TARGET_REVISION",
        "stale_job_retriable": False,
        "stale_write_creates_evidence": False,
    }
    assert contract["fresh_reapproval"] == {
        "policy": "governance.fresh-reapproval.v1",
        "direct_rejected_revision_approval": False,
        "new_revision_required": True,
        "exact_binding_required_before_qualifying_evidence": True,
        "mandatory_artifacts": ["scan", "equivalence-test", "review", "decision"],
        "scan_and_test_ids_are_server_derived": True,
        "freshness_sensitive_projection_is_reset": True,
        "generic_state_update_can_approve": False,
        "blocked_to_pending_requires_post_reset_evidence": True,
        "application_history_is_append_only": True,
        "database_tamper_resistance": False,
    }


def test_governance_lifecycle_transition_set_is_explicit():
    contract = _contract()
    transitions = {transition["event"]: transition for transition in contract["transitions"]}

    assert set(transitions) == {
        "register",
        "bind-runtime-artifact",
        "bind-runtime-artifact-identical",
        "approve",
        "reject",
        "block",
        "register-new-revision",
        "admission-mismatch",
    }
    assert transitions["approve"] == {
        "event": "approve",
        "from": ["pending-bound", "approved-current"],
        "to": "approved-current",
        "rejected_current_requires_new_revision": True,
    }
    assert transitions["register-new-revision"]["previous_current_becomes"] == "superseded"
    assert transitions["admission-mismatch"]["to"] == "drifted"
    assert transitions["bind-runtime-artifact-identical"] == {
        "event": "bind-runtime-artifact-identical",
        "from": [
            "pending-bound",
            "approved-current",
            "rejected-current",
            "blocked-current",
        ],
        "to": "same-state",
    }


def test_gate_designs_record_current_target_and_fresh_reapproval_boundaries():
    design = (ROOT / "docs" / "governance-authority-gate-a-design.md").read_text(
        encoding="utf-8"
    )

    assert "A1 implemented" in design
    assert "STALE_TARGET_REVISION" in design
    assert "It requires no schema or data migration" in design
    assert "Gate A does not fully specify or authorize fresh reapproval" in design
    assert "FTS5" in design
    assert "Dashboard redesign" in design
    gate_b = (ROOT / "docs" / "governance-authority-gate-b-design.md").read_text(
        encoding="utf-8"
    )
    assert "Gate B implemented" in gate_b
    assert "governance.fresh-reapproval.v1" in gate_b
    assert "no schema or data migration" in gate_b
    assert "database-level tamper resistance" in gate_b


def _approved_governance_skill(tmp_path):
    db = GovernanceDB(db_path=tmp_path / "governance.db")
    canonical_skill_id = "claude__skill__lifecycle_test"
    digest = "sha256:" + "1" * 64
    skill_id = db.create_skill(name="lifecycle-test", version="1.0.0")
    binding = db.bind_runtime_artifact(
        skill_id,
        canonical_skill_id=canonical_skill_id,
        artifact_digest=digest,
        bound_by="binder",
    )
    assert binding is not None
    assert db.approve_skill(skill_id, approved_by="reviewer", reason="reviewed")
    return db, skill_id, canonical_skill_id, digest, binding["revision_id"]


def test_lifecycle_enforces_new_revision_for_reapproval(tmp_path):
    db, skill_id, _canonical_skill_id, _digest, _revision_id = (
        _approved_governance_skill(tmp_path)
    )

    assert db.reject_skill(skill_id, rejected_by="reviewer", reason="rejected")
    assert db.get_current_revision(skill_id).status == "rejected"
    assert not db.approve_skill(skill_id, approved_by="reviewer-2", reason="reapproved")
    assert db.get_current_revision(skill_id).status == "rejected"


def test_lifecycle_documents_identical_approved_binding_is_idempotent(tmp_path):
    db, skill_id, canonical_skill_id, digest, revision_id = _approved_governance_skill(
        tmp_path
    )

    binding = db.bind_runtime_artifact(
        skill_id,
        canonical_skill_id=canonical_skill_id,
        artifact_digest=digest,
        bound_by="second-binder",
    )

    assert binding == {
        "skill_id": skill_id,
        "canonical_skill_id": canonical_skill_id,
        "revision_id": revision_id,
        "artifact_digest": digest,
    }
    assert db.get_current_revision(skill_id).status == "approved"


def test_lifecycle_enforces_current_target_for_reject(tmp_path):
    db, skill_id, canonical_skill_id, _digest, historical_revision_id = (
        _approved_governance_skill(tmp_path)
    )
    current_digest = "sha256:" + "2" * 64
    current_revision_id = db.register_revision(skill_id, version="2.0.0")
    db.bind_runtime_artifact(
        skill_id,
        canonical_skill_id=canonical_skill_id,
        artifact_digest=current_digest,
        bound_by="binder",
    )
    assert db.approve_skill(skill_id, approved_by="reviewer", reason="reviewed")

    before_audit_count = len(db.get_audit_log(skill_id=skill_id, limit=100))
    assert not db.reject_skill(
        skill_id,
        rejected_by="reviewer",
        reason="historical target",
        revision_id=historical_revision_id,
    )

    assert db.get_current_revision(skill_id).revision_id == current_revision_id
    assert db.get_current_revision(skill_id).status == "approved"
    assert db.get_runtime_approval(
        canonical_skill_id=canonical_skill_id,
        artifact_digest=current_digest,
    ) is not None
    with db.connection() as connection:
        projection_status = connection.execute(
            "SELECT status FROM skills WHERE skill_id=?", (skill_id,)
        ).fetchone()[0]
    assert projection_status == "approved"
    assert len(db.get_audit_log(skill_id=skill_id, limit=100)) == before_audit_count


def test_lifecycle_enforces_current_target_for_blocked_scan(tmp_path):
    db, skill_id, canonical_skill_id, _digest, historical_revision_id = (
        _approved_governance_skill(tmp_path)
    )
    current_digest = "sha256:" + "3" * 64
    db.register_revision(skill_id, version="2.0.0")
    db.bind_runtime_artifact(
        skill_id,
        canonical_skill_id=canonical_skill_id,
        artifact_digest=current_digest,
        bound_by="binder",
    )
    assert db.approve_skill(skill_id, approved_by="reviewer", reason="reviewed")

    before_audit_count = len(db.get_audit_log(skill_id=skill_id, limit=100))
    with pytest.raises(GovernanceTargetError) as error:
        db.record_security_scan(
            skill_id,
            {"blocked": True, "risk_level": "critical", "risk_score": 10},
            revision_id=historical_revision_id,
        )

    assert error.value.code == "STALE_TARGET_REVISION"
    assert db.get_current_revision(skill_id).status == "approved"
    assert db.get_runtime_approval(
        canonical_skill_id=canonical_skill_id,
        artifact_digest=current_digest,
    ) is not None
    with db.connection() as connection:
        projection_status = connection.execute(
            "SELECT status FROM skills WHERE skill_id=?", (skill_id,)
        ).fetchone()[0]
    assert projection_status == "approved"
    assert db.get_scan_history(skill_id, limit=10) == []
    assert len(db.get_audit_log(skill_id=skill_id, limit=100)) == before_audit_count
