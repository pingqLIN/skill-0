import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.governance_db import GovernanceDB, GovernanceTargetError
from runtime.digest import canonical_digest
from runtime.governance import RuntimeGovernanceError, SQLiteRuntimeGovernanceGate


def test_create_skill_creates_current_revision(tmp_path):
    db = GovernanceDB(db_path=tmp_path / "governance.db")

    skill_id = db.create_skill(
        name="revision-test",
        source_type="local",
        source_path="/tmp/source/SKILL.md",
        source_url="https://example.com/revision-test",
        author_name="tester",
        license_spdx="MIT",
        source_commit="abc123",
        version="1.2.0",
    )

    skill = db.get_skill(skill_id=skill_id)
    revision = db.get_current_revision(skill_id)

    assert skill is not None
    assert revision is not None
    assert skill.current_revision_id == revision.revision_id
    assert skill.revision_id == revision.revision_id
    assert revision.revision_number == 1
    assert revision.source_path == "/tmp/source/SKILL.md"
    assert revision.source_checksum


def test_register_revision_switches_current_revision(tmp_path):
    db = GovernanceDB(db_path=tmp_path / "governance.db")
    skill_id = db.create_skill(
        name="revision-switch",
        source_type="local",
        source_path="/tmp/source/v1/SKILL.md",
        author_name="tester",
        license_spdx="MIT",
    )

    first_revision = db.get_current_revision(skill_id)
    new_revision_id = db.register_revision(
        skill_id,
        source_path="/tmp/source/v2/SKILL.md",
        source_commit="def456",
        version="2.0.0",
    )

    current = db.get_current_revision(skill_id)
    revisions = db.list_revisions(skill_id)

    assert first_revision is not None
    assert new_revision_id is not None
    assert current is not None
    assert current.revision_id == new_revision_id
    assert current.revision_number == 2
    assert current.source_path == "/tmp/source/v2/SKILL.md"
    assert len(revisions) == 2
    assert revisions[0].is_current is True
    assert revisions[1].is_current is False


def test_register_revision_resets_freshness_sensitive_state(tmp_path):
    db = GovernanceDB(db_path=tmp_path / "governance.db")
    skill_id = db.create_skill(name="freshness-reset", version="1.0.0")
    original = db.get_current_revision(skill_id)
    assert original is not None
    db.record_security_scan(
        skill_id,
        {
            "risk_level": "medium",
            "risk_score": 4,
            "findings": [{"code": "reviewed"}],
            "blocked": False,
        },
    )
    db.record_equivalence_test(
        skill_id,
        {"scores": {"overall": 0.95}, "passed": True},
    )

    new_revision_id = db.register_revision(skill_id, version="2.0.0")
    current = db.get_current_revision(skill_id)
    projection = db.get_skill(skill_id=skill_id)

    assert current is not None
    assert projection is not None
    assert current.revision_id == new_revision_id
    assert current.created_at != original.created_at
    assert current.status == "pending"
    assert current.artifact_digest is None
    assert current.security_scanned_at is None
    assert current.scanner_version is None
    assert current.risk_level == "unknown"
    assert current.risk_score == 0
    assert current.equivalence_tested_at is None
    assert current.equivalence_score is None
    assert current.equivalence_passed is None
    assert current.installed_path is None
    assert current.installed_at is None
    assert projection.security_scanned_at is None
    assert projection.risk_level == "unknown"
    assert projection.equivalence_tested_at is None
    assert projection.equivalence_passed is None


def _runtime_skill_document() -> dict:
    return {
        "meta": {
            "skill_id": "claude__skill__runtime_governed",
            "name": "runtime-governed",
            "version": "1.2.0",
        },
        "original_definition": {"source": "converted-skills/runtime/SKILL.md"},
        "decomposition": {"actions": [], "rules": [], "directives": []},
    }


def test_runtime_approval_requires_exact_current_approved_artifact(tmp_path):
    path = tmp_path / "governance.db"
    db = GovernanceDB(db_path=path)
    document = _runtime_skill_document()
    digest = canonical_digest(document)
    skill_id = db.create_skill(
        name="runtime-governed",
        source_type="local",
        source_path="converted-skills/runtime/SKILL.md",
        version="1.2.0",
    )
    assert not db.approve_skill(
        skill_id,
        approved_by="reviewer",
        reason="artifact binding is required",
    )
    binding = db.bind_runtime_artifact(
        skill_id,
        canonical_skill_id=document["meta"]["skill_id"],
        artifact_digest=digest,
        bound_by="binder",
    )
    assert binding is not None
    assert db.get_runtime_approval(
        canonical_skill_id=document["meta"]["skill_id"],
        artifact_digest=digest,
    ) is None

    assert db.approve_skill(skill_id, approved_by="reviewer", reason="reviewed")
    approval = db.get_runtime_approval(
        canonical_skill_id=document["meta"]["skill_id"],
        artifact_digest=digest,
    )
    assert approval is not None
    assert approval["revision_id"] == binding["revision_id"]
    assert approval["approved_by"] == "reviewer"

    attestation = SQLiteRuntimeGovernanceGate(path).evaluate(
        document,
        {"skill_ref": {"name": "runtime-governed", "version": "1.2.0"}},
    )
    assert attestation["governance_skill_id"] == skill_id
    assert attestation["revision_id"] == binding["revision_id"]
    assert attestation["artifact_digest"] == digest


def test_runtime_governance_uses_resolved_asset_id_without_rewriting_payload(tmp_path):
    path = tmp_path / "governance.db"
    db = GovernanceDB(db_path=path)
    document = _runtime_skill_document()
    legacy_skill_id = document["meta"]["skill_id"]
    canonical_asset_id = "claude__skill__runtime_governed_v2"
    digest = canonical_digest(document)
    skill_id = db.create_skill(name="runtime-governed", version="1.2.0")
    db.bind_runtime_artifact(
        skill_id,
        canonical_skill_id=canonical_asset_id,
        artifact_digest=digest,
        bound_by="binder",
    )
    assert db.approve_skill(skill_id, approved_by="reviewer", reason="reviewed")

    attestation = SQLiteRuntimeGovernanceGate(path).evaluate(
        document,
        {"skill_ref": {"name": "runtime-governed", "version": "1.2.0"}},
        canonical_asset_id=canonical_asset_id,
    )
    assert document["meta"]["skill_id"] == legacy_skill_id
    assert attestation["canonical_skill_id"] == canonical_asset_id
    assert attestation["artifact_digest"] == digest


def test_runtime_approval_ignores_mutable_skill_status_projection(tmp_path):
    path = tmp_path / "governance.db"
    db = GovernanceDB(db_path=path)
    document = _runtime_skill_document()
    digest = canonical_digest(document)
    skill_id = db.create_skill(name="runtime-status", version="1.2.0")
    db.bind_runtime_artifact(
        skill_id,
        canonical_skill_id=document["meta"]["skill_id"],
        artifact_digest=digest,
        bound_by="binder",
    )
    db.approve_skill(skill_id, approved_by="reviewer", reason="reviewed")
    with db.connection() as connection:
        connection.execute(
            "UPDATE skills SET status='rejected' WHERE skill_id=?", (skill_id,)
        )
    assert db.get_runtime_approval(
        canonical_skill_id=document["meta"]["skill_id"],
        artifact_digest=digest,
    ) is not None
    assert SQLiteRuntimeGovernanceGate(path).evaluate(
        document,
        {"skill_ref": {"name": "runtime-governed", "version": "1.2.0"}},
    )["revision_id"]


def test_runtime_approval_rejects_drift_and_new_revision_requires_rebinding(tmp_path):
    path = tmp_path / "governance.db"
    db = GovernanceDB(db_path=path)
    document = _runtime_skill_document()
    digest = canonical_digest(document)
    skill_id = db.create_skill(name="runtime-drift", version="1.2.0")
    db.bind_runtime_artifact(
        skill_id,
        canonical_skill_id=document["meta"]["skill_id"],
        artifact_digest=digest,
        bound_by="binder",
    )
    db.approve_skill(skill_id, approved_by="reviewer", reason="reviewed")

    changed = dict(document)
    changed["meta"] = {**document["meta"], "description": "changed"}
    with pytest.raises(RuntimeGovernanceError, match="ARTIFACT_DIGEST_MISMATCH"):
        SQLiteRuntimeGovernanceGate(path).evaluate(
            changed,
            {"skill_ref": {"name": "runtime-governed", "version": "1.2.0"}},
        )

    new_revision = db.register_revision(skill_id, version="2.0.0")
    assert new_revision is not None
    current = db.get_current_revision(skill_id)
    assert current is not None
    assert current.status == "pending"
    assert current.artifact_digest is None
    assert db.get_runtime_approval(
        canonical_skill_id=document["meta"]["skill_id"],
        artifact_digest=digest,
    ) is None


def test_rejected_current_revision_cannot_be_directly_reapproved(tmp_path):
    db = GovernanceDB(db_path=tmp_path / "governance.db")
    document = _runtime_skill_document()
    digest = canonical_digest(document)
    skill_id = db.create_skill(name="no-direct-reapproval", version="1.0.0")
    db.bind_runtime_artifact(
        skill_id,
        canonical_skill_id=document["meta"]["skill_id"],
        artifact_digest=digest,
        bound_by="binder",
    )
    assert db.approve_skill(skill_id, approved_by="reviewer", reason="initial")
    assert db.reject_skill(skill_id, rejected_by="reviewer", reason="rejected")
    before = _revision_target_snapshot(db, skill_id)

    assert not db.approve_skill(
        skill_id,
        approved_by="reviewer-2",
        reason="direct retry",
    )

    assert _revision_target_snapshot(db, skill_id) == before
    assert db.get_runtime_approval(
        canonical_skill_id=document["meta"]["skill_id"],
        artifact_digest=digest,
    ) is None


def test_fresh_reapproval_requires_new_bound_revision_scan_test_and_review(tmp_path):
    db = GovernanceDB(db_path=tmp_path / "governance.db")
    document = _runtime_skill_document()
    digest = canonical_digest(document)
    canonical_skill_id = document["meta"]["skill_id"]
    skill_id = db.create_skill(name="fresh-reapproval", version="1.0.0")
    first_binding = db.bind_runtime_artifact(
        skill_id,
        canonical_skill_id=canonical_skill_id,
        artifact_digest=digest,
        bound_by="binder",
    )
    assert first_binding is not None
    assert db.approve_skill(skill_id, approved_by="reviewer", reason="initial")
    assert db.reject_skill(skill_id, rejected_by="reviewer", reason="rejected")

    second_revision_id = db.register_revision(skill_id, version="2.0.0")
    assert second_revision_id is not None
    second_binding = db.bind_runtime_artifact(
        skill_id,
        canonical_skill_id=canonical_skill_id,
        artifact_digest=digest,
        bound_by="binder-2",
    )
    assert second_binding is not None
    assert not db.approve_skill(skill_id, approved_by="reviewer-2", reason="missing evidence")

    scan_id = db.record_security_scan(
        skill_id,
        {"risk_level": "low", "risk_score": 1, "blocked": False, "findings": []},
        revision_id=second_revision_id,
    )
    assert not db.approve_skill(skill_id, approved_by="reviewer-2", reason="missing test")
    db.record_equivalence_test(
        skill_id,
        {"scores": {"overall": 0.2}, "passed": False},
        revision_id=second_revision_id,
    )
    assert not db.approve_skill(skill_id, approved_by="reviewer-2", reason="failed test")
    test_id = db.record_equivalence_test(
        skill_id,
        {"scores": {"overall": 0.98}, "passed": True},
        revision_id=second_revision_id,
    )
    assert not db.approve_skill(skill_id, approved_by="", reason="fresh review")
    assert not db.approve_skill(skill_id, approved_by="reviewer-2", reason="")
    assert db.approve_skill(
        skill_id,
        approved_by="reviewer-2",
        reason="fresh revision evidence reviewed",
    )

    revisions = {revision.revision_id: revision for revision in db.list_revisions(skill_id)}
    assert revisions[first_binding["revision_id"]].status == "rejected"
    assert revisions[first_binding["revision_id"]].is_current is False
    assert revisions[second_revision_id].status == "approved"
    approval = db.get_runtime_approval(
        canonical_skill_id=canonical_skill_id,
        artifact_digest=digest,
    )
    assert approval is not None
    assert approval["revision_id"] == second_revision_id

    audit = db.get_audit_log(skill_id=skill_id, limit=100)
    review = next(event for event in audit if event["event_type"] == "review")
    decision = next(
        event
        for event in audit
        if event["event_type"] == "approve"
        and event["revision_id"] == second_revision_id
    )
    packet = decision["details"]["fresh_reapproval"]
    assert packet == {
        "policy": "governance.fresh-reapproval.v1",
        "revision_id": second_revision_id,
        "canonical_skill_id": canonical_skill_id,
        "artifact_digest": digest,
        "binding_event_id": packet["binding_event_id"],
        "scan_id": scan_id,
        "test_id": test_id,
        "review_event_id": review["event_id"],
    }
    assert review["details"]["scan_id"] == scan_id
    assert review["details"]["test_id"] == test_id
    assert review["actor"] == "reviewer-2"


def test_reapproval_ignores_scan_and_test_recorded_before_new_binding(tmp_path):
    db = GovernanceDB(db_path=tmp_path / "governance.db")
    document = _runtime_skill_document()
    digest = canonical_digest(document)
    canonical_skill_id = document["meta"]["skill_id"]
    skill_id = db.create_skill(name="ordered-reapproval", version="1.0.0")
    db.bind_runtime_artifact(
        skill_id,
        canonical_skill_id=canonical_skill_id,
        artifact_digest=digest,
        bound_by="binder",
    )
    assert db.approve_skill(skill_id, approved_by="reviewer", reason="initial")
    assert db.reject_skill(skill_id, rejected_by="reviewer", reason="rejected")

    revision_id = db.register_revision(skill_id, version="2.0.0")
    db.record_security_scan(
        skill_id,
        {"risk_level": "low", "risk_score": 1, "blocked": False, "findings": []},
        revision_id=revision_id,
    )
    db.record_equivalence_test(
        skill_id,
        {"scores": {"overall": 1.0}, "passed": True},
        revision_id=revision_id,
    )
    db.bind_runtime_artifact(
        skill_id,
        canonical_skill_id=canonical_skill_id,
        artifact_digest=digest,
        bound_by="binder-2",
    )

    assert not db.approve_skill(
        skill_id,
        approved_by="reviewer-2",
        reason="pre-binding evidence is stale",
    )
    db.record_security_scan(
        skill_id,
        {"risk_level": "low", "risk_score": 1, "blocked": False, "findings": []},
        revision_id=revision_id,
    )
    db.record_equivalence_test(
        skill_id,
        {"scores": {"overall": 1.0}, "passed": True},
        revision_id=revision_id,
    )
    assert db.approve_skill(
        skill_id,
        approved_by="reviewer-2",
        reason="post-binding evidence reviewed",
    )


def test_fresh_reapproval_uses_latest_test_without_success_fallback(tmp_path):
    db = GovernanceDB(db_path=tmp_path / "governance.db")
    document = _runtime_skill_document()
    digest = canonical_digest(document)
    canonical_skill_id = document["meta"]["skill_id"]
    skill_id = db.create_skill(name="latest-evidence", version="1.0.0")
    db.bind_runtime_artifact(
        skill_id,
        canonical_skill_id=canonical_skill_id,
        artifact_digest=digest,
        bound_by="binder",
    )
    assert db.approve_skill(skill_id, approved_by="reviewer", reason="initial")
    assert db.reject_skill(skill_id, rejected_by="reviewer", reason="rejected")
    revision_id = db.register_revision(skill_id, version="2.0.0")
    db.bind_runtime_artifact(
        skill_id,
        canonical_skill_id=canonical_skill_id,
        artifact_digest=digest,
        bound_by="binder-2",
    )
    db.record_security_scan(
        skill_id,
        {"risk_level": "low", "risk_score": 1, "blocked": False},
        revision_id=revision_id,
    )
    db.record_equivalence_test(
        skill_id,
        {"scores": {"overall": 1.0}, "passed": True},
        revision_id=revision_id,
    )
    db.record_equivalence_test(
        skill_id,
        {"scores": {"overall": 0.0}, "passed": False},
        revision_id=revision_id,
    )
    before = _revision_target_snapshot(db, skill_id)

    assert not db.approve_skill(
        skill_id,
        approved_by="reviewer-2",
        reason="latest failing test must deny",
    )
    assert _revision_target_snapshot(db, skill_id) == before
    assert db.get_runtime_approval(
        canonical_skill_id=canonical_skill_id,
        artifact_digest=digest,
    ) is None

    db.record_equivalence_test(
        skill_id,
        {"scores": {"overall": 1.0}, "passed": True},
        revision_id=revision_id,
    )
    assert db.approve_skill(
        skill_id,
        approved_by="reviewer-2",
        reason="latest passing test reviewed",
    )


def test_runtime_binding_rejects_identity_reuse_or_approved_revision_mutation(tmp_path):
    db = GovernanceDB(db_path=tmp_path / "governance.db")
    document = _runtime_skill_document()
    digest = canonical_digest(document)
    first = db.create_skill(name="runtime-one", version="1.2.0")
    second = db.create_skill(name="runtime-two", version="1.2.0")
    db.bind_runtime_artifact(
        first,
        canonical_skill_id=document["meta"]["skill_id"],
        artifact_digest=digest,
        bound_by="binder",
    )
    with pytest.raises(ValueError, match="already bound"):
        db.bind_runtime_artifact(
            second,
            canonical_skill_id=document["meta"]["skill_id"],
            artifact_digest=digest,
            bound_by="binder",
        )
    db.approve_skill(first, approved_by="reviewer", reason="reviewed")
    with pytest.raises(ValueError, match="pending current revision"):
        db.bind_runtime_artifact(
            first,
            canonical_skill_id=document["meta"]["skill_id"],
            artifact_digest="sha256:" + "f" * 64,
            bound_by="binder",
        )


def test_approval_rejects_non_current_revision_id(tmp_path):
    db = GovernanceDB(db_path=tmp_path / "governance.db")
    skill_id = db.create_skill(name="runtime-current-only", version="1.0.0")
    previous = db.get_current_revision(skill_id)
    assert previous is not None

    db.register_revision(skill_id, version="1.2.0")
    current = db.get_current_revision(skill_id)
    assert current is not None
    document = _runtime_skill_document()
    db.bind_runtime_artifact(
        skill_id,
        canonical_skill_id=document["meta"]["skill_id"],
        artifact_digest=canonical_digest(document),
        bound_by="binder",
    )

    assert not db.approve_skill(
        skill_id,
        approved_by="reviewer",
        reason="stale revision",
        revision_id=previous.revision_id,
    )
    assert db.approve_skill(
        skill_id,
        approved_by="reviewer",
        reason="current revision",
        revision_id=current.revision_id,
    )


def _revision_target_snapshot(db: GovernanceDB, skill_id: str) -> dict:
    with db.connection() as connection:
        return {
            "skill": dict(
                connection.execute(
                    "SELECT * FROM skills WHERE skill_id = ?", (skill_id,)
                ).fetchone()
            ),
            "revisions": [
                dict(row)
                for row in connection.execute(
                    "SELECT * FROM skill_revisions WHERE skill_id = ? ORDER BY revision_number",
                    (skill_id,),
                ).fetchall()
            ],
            "scan_count": connection.execute(
                "SELECT COUNT(*) FROM security_scans WHERE skill_id = ?", (skill_id,)
            ).fetchone()[0],
            "test_count": connection.execute(
                "SELECT COUNT(*) FROM equivalence_tests WHERE skill_id = ?", (skill_id,)
            ).fetchone()[0],
            "audit_count": connection.execute(
                "SELECT COUNT(*) FROM audit_log WHERE skill_id = ?", (skill_id,)
            ).fetchone()[0],
        }


def test_stale_revision_writes_fail_without_side_effects(tmp_path):
    db = GovernanceDB(db_path=tmp_path / "governance.db")
    skill_id = db.create_skill(name="stale-target", version="1.0.0")
    historical = db.get_current_revision(skill_id)
    assert historical is not None
    current_revision_id = db.register_revision(skill_id, version="2.0.0")
    assert current_revision_id is not None
    before = _revision_target_snapshot(db, skill_id)

    assert not db.reject_skill(
        skill_id,
        rejected_by="reviewer",
        reason="stale target",
        revision_id=historical.revision_id,
    )
    with pytest.raises(GovernanceTargetError) as scan_error:
        db.record_security_scan(
            skill_id,
            {
                "risk_level": "critical",
                "risk_score": 10,
                "blocked": True,
                "findings": [],
            },
            revision_id=historical.revision_id,
        )
    with pytest.raises(GovernanceTargetError) as test_error:
        db.record_equivalence_test(
            skill_id,
            {"scores": {"overall": 1.0}, "passed": True},
            revision_id=historical.revision_id,
        )

    assert scan_error.value.code == "STALE_TARGET_REVISION"
    assert scan_error.value.target_revision_id == historical.revision_id
    assert scan_error.value.current_revision_id == current_revision_id
    assert test_error.value.code == "STALE_TARGET_REVISION"
    assert _revision_target_snapshot(db, skill_id) == before


def test_evidence_writes_resolve_omitted_or_explicit_current_revision(tmp_path):
    db = GovernanceDB(db_path=tmp_path / "governance.db")
    skill_id = db.create_skill(name="current-target", version="1.0.0")
    current = db.get_current_revision(skill_id)
    assert current is not None

    scan_id = db.record_security_scan(
        skill_id,
        {"risk_level": "low", "risk_score": 1, "blocked": False, "findings": []},
    )
    test_id = db.record_equivalence_test(
        skill_id,
        {"scores": {"overall": 0.9}, "passed": True},
        revision_id=current.revision_id,
    )

    scan = db.get_scan_history(skill_id, limit=1)[0]
    equivalence = db.get_test_history(skill_id, limit=1)[0]
    assert (scan["scan_id"], scan["revision_id"]) == (
        scan_id,
        current.revision_id,
    )
    assert (equivalence["test_id"], equivalence["revision_id"]) == (
        test_id,
        current.revision_id,
    )


def test_scan_and_approval_are_bound_to_current_revision(tmp_path):
    db = GovernanceDB(db_path=tmp_path / "governance.db")
    skill_id = db.create_skill(
        name="revision-governance",
        source_type="local",
        source_path="/tmp/source/v1/SKILL.md",
        author_name="tester",
        license_spdx="MIT",
    )
    db.register_revision(
        skill_id,
        source_path="/tmp/source/v2/SKILL.md",
        source_commit="rev-2",
    )
    current = db.get_current_revision(skill_id)
    assert current is not None

    db.record_security_scan(
        skill_id,
        {
            "scanned_at": "2026-03-27T12:00:00",
            "scanner_version": "scanner-v1",
            "risk_level": "low",
            "risk_score": 5,
            "findings_count": 0,
            "findings": [],
            "blocked": False,
        },
    )
    document = _runtime_skill_document()
    db.bind_runtime_artifact(
        skill_id,
        canonical_skill_id=document["meta"]["skill_id"],
        artifact_digest=canonical_digest(document),
        bound_by="binder",
    )
    assert db.approve_skill(skill_id, approved_by="reviewer", reason="ok")

    scan = db.get_scan_history(skill_id, limit=1)[0]
    audit = db.get_audit_log(skill_id=skill_id, limit=10)
    refreshed = db.get_current_revision(skill_id)

    assert refreshed is not None
    assert scan["revision_id"] == current.revision_id
    assert refreshed.approved_by == "reviewer"
    assert any(event.get("revision_id") == current.revision_id for event in audit if event["event_type"] in {"scan", "approve"})


def test_update_skill_rejects_artifact_field_mutation(tmp_path):
    db = GovernanceDB(db_path=tmp_path / "governance.db")
    skill_id = db.create_skill(
        name="immutable-artifact",
        source_type="local",
        source_path="/tmp/source/v1/SKILL.md",
        author_name="tester",
        license_spdx="MIT",
    )
    before = db.get_current_revision(skill_id)

    with pytest.raises(ValueError, match="register_revision"):
        db.update_skill(skill_id, source_path="/tmp/source/v2/SKILL.md")

    after = db.get_current_revision(skill_id)
    assert before is not None
    assert after is not None
    assert after.revision_id == before.revision_id
    assert after.source_path == "/tmp/source/v1/SKILL.md"
    assert len(db.list_revisions(skill_id)) == 1


def test_update_current_revision_state_only_allows_blocked_to_pending(tmp_path):
    db = GovernanceDB(db_path=tmp_path / "governance.db")
    skill_id = db.create_skill(
        name="status-update",
        source_type="local",
        source_path="/tmp/source/v1/SKILL.md",
        author_name="tester",
        license_spdx="MIT",
    )
    db.record_security_scan(
        skill_id,
        {
            "risk_level": "critical",
            "risk_score": 10,
            "blocked": True,
            "findings": [],
        },
    )
    before = db.get_current_revision(skill_id)

    success = db.update_current_revision_state(skill_id, status="pending")

    after = db.get_current_revision(skill_id)
    skill = db.get_skill(skill_id=skill_id)
    audit = db.get_audit_log(skill_id=skill_id, limit=10)

    assert success is True
    assert before is not None
    assert after is not None
    assert skill is not None
    assert after.revision_id == before.revision_id
    assert before.status == "blocked"
    assert after.status == "pending"
    assert skill.status == "pending"
    assert len(db.list_revisions(skill_id)) == 1
    assert any(event["event_type"] == "revision_state_update" for event in audit)


def test_generic_state_update_cannot_restore_governance_authority(tmp_path):
    db = GovernanceDB(db_path=tmp_path / "governance.db")
    document = _runtime_skill_document()
    digest = canonical_digest(document)
    canonical_skill_id = document["meta"]["skill_id"]
    skill_id = db.create_skill(name="state-bypass", version="1.0.0")
    db.bind_runtime_artifact(
        skill_id,
        canonical_skill_id=canonical_skill_id,
        artifact_digest=digest,
        bound_by="binder",
    )
    assert db.approve_skill(skill_id, approved_by="reviewer", reason="initial")
    assert db.reject_skill(skill_id, rejected_by="reviewer", reason="rejected")
    before = _revision_target_snapshot(db, skill_id)

    with pytest.raises(ValueError, match="approval requires approve_skill"):
        db.update_current_revision_state(skill_id, status="approved")
    with pytest.raises(ValueError, match="rejection requires a new revision"):
        db.update_current_revision_state(skill_id, status="pending")

    assert _revision_target_snapshot(db, skill_id) == before
    assert db.get_runtime_approval(
        canonical_skill_id=canonical_skill_id,
        artifact_digest=digest,
    ) is None


def test_blocked_remediation_requires_post_reset_scan_and_test(tmp_path):
    db = GovernanceDB(db_path=tmp_path / "governance.db")
    document = _runtime_skill_document()
    digest = canonical_digest(document)
    canonical_skill_id = document["meta"]["skill_id"]
    skill_id = db.create_skill(name="blocked-remediation", version="1.0.0")
    db.bind_runtime_artifact(
        skill_id,
        canonical_skill_id=canonical_skill_id,
        artifact_digest=digest,
        bound_by="binder",
    )
    db.record_equivalence_test(
        skill_id,
        {"scores": {"overall": 1.0}, "passed": True},
    )
    db.record_security_scan(
        skill_id,
        {"risk_level": "critical", "risk_score": 10, "blocked": True},
    )
    assert db.update_current_revision_state(skill_id, status="pending")

    assert not db.approve_skill(
        skill_id,
        approved_by="reviewer",
        reason="pre-reset evidence must not qualify",
    )
    db.record_security_scan(
        skill_id,
        {"risk_level": "low", "risk_score": 1, "blocked": False},
    )
    assert not db.approve_skill(
        skill_id,
        approved_by="reviewer",
        reason="post-reset test is still missing",
    )
    db.record_equivalence_test(
        skill_id,
        {"scores": {"overall": 1.0}, "passed": True},
    )
    assert db.approve_skill(
        skill_id,
        approved_by="reviewer",
        reason="blocked state remediated with fresh evidence",
    )


def test_new_revision_after_remediated_block_requires_fresh_evidence(tmp_path):
    db = GovernanceDB(db_path=tmp_path / "governance.db")
    document = _runtime_skill_document()
    digest = canonical_digest(document)
    canonical_skill_id = document["meta"]["skill_id"]
    skill_id = db.create_skill(name="blocked-new-revision", version="1.0.0")
    db.bind_runtime_artifact(
        skill_id,
        canonical_skill_id=canonical_skill_id,
        artifact_digest=digest,
        bound_by="binder",
    )
    db.record_security_scan(
        skill_id,
        {"risk_level": "critical", "risk_score": 10, "blocked": True},
    )
    assert db.update_current_revision_state(skill_id, status="pending")

    revision_id = db.register_revision(skill_id, version="2.0.0")
    db.bind_runtime_artifact(
        skill_id,
        canonical_skill_id=canonical_skill_id,
        artifact_digest=digest,
        bound_by="binder-2",
    )
    before = _revision_target_snapshot(db, skill_id)
    assert not db.approve_skill(
        skill_id,
        approved_by="reviewer",
        reason="a new revision still needs fresh evidence",
    )
    assert _revision_target_snapshot(db, skill_id) == before
    assert db.get_runtime_approval(
        canonical_skill_id=canonical_skill_id,
        artifact_digest=digest,
    ) is None
    db.record_security_scan(
        skill_id,
        {"risk_level": "low", "risk_score": 1, "blocked": False},
        revision_id=revision_id,
    )
    db.record_equivalence_test(
        skill_id,
        {"scores": {"overall": 1.0}, "passed": True},
        revision_id=revision_id,
    )
    assert db.approve_skill(
        skill_id,
        approved_by="reviewer",
        reason="new revision evidence reviewed",
    )


def test_legacy_blocked_scan_row_requires_fresh_evidence_without_audit_flag(tmp_path):
    db = GovernanceDB(db_path=tmp_path / "governance.db")
    document = _runtime_skill_document()
    digest = canonical_digest(document)
    canonical_skill_id = document["meta"]["skill_id"]
    skill_id = db.create_skill(name="legacy-blocked-scan", version="1.0.0")
    first_binding = db.bind_runtime_artifact(
        skill_id,
        canonical_skill_id=canonical_skill_id,
        artifact_digest=digest,
        bound_by="binder",
    )
    scan_id = db.record_security_scan(
        skill_id,
        {"risk_level": "critical", "risk_score": 10, "blocked": True},
    )
    with db.connection() as connection:
        connection.execute(
            """UPDATE audit_log SET details_json=?
               WHERE skill_id=? AND revision_id=? AND event_type='scan'""",
            (
                json.dumps(
                    {
                        "scan_id": scan_id,
                        "revision_id": first_binding["revision_id"],
                        "risk_level": "critical",
                        "risk_score": 10,
                    }
                ),
                skill_id,
                first_binding["revision_id"],
            ),
        )
    assert db.update_current_revision_state(skill_id, status="pending")

    revision_id = db.register_revision(skill_id, version="2.0.0")
    db.bind_runtime_artifact(
        skill_id,
        canonical_skill_id=canonical_skill_id,
        artifact_digest=digest,
        bound_by="binder-2",
    )
    before = _revision_target_snapshot(db, skill_id)

    assert not db.approve_skill(
        skill_id,
        approved_by="reviewer",
        reason="legacy blocked evidence requires fresh review",
    )
    assert _revision_target_snapshot(db, skill_id) == before
    assert db.get_runtime_approval(
        canonical_skill_id=canonical_skill_id,
        artifact_digest=digest,
    ) is None

    db.record_security_scan(
        skill_id,
        {"risk_level": "low", "risk_score": 1, "blocked": False},
        revision_id=revision_id,
    )
    db.record_equivalence_test(
        skill_id,
        {"scores": {"overall": 1.0}, "passed": True},
        revision_id=revision_id,
    )
    assert db.approve_skill(
        skill_id,
        approved_by="reviewer",
        reason="new revision evidence reviewed",
    )
