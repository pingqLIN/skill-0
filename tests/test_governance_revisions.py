import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.governance_db import GovernanceDB


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
    db.approve_skill(skill_id, approved_by="reviewer", reason="ok")

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


def test_update_current_revision_state_updates_status_without_new_revision(tmp_path):
    db = GovernanceDB(db_path=tmp_path / "governance.db")
    skill_id = db.create_skill(
        name="status-update",
        source_type="local",
        source_path="/tmp/source/v1/SKILL.md",
        author_name="tester",
        license_spdx="MIT",
    )
    before = db.get_current_revision(skill_id)

    success = db.update_current_revision_state(skill_id, status="approved")

    after = db.get_current_revision(skill_id)
    skill = db.get_skill(skill_id=skill_id)
    audit = db.get_audit_log(skill_id=skill_id, limit=10)

    assert success is True
    assert before is not None
    assert after is not None
    assert skill is not None
    assert after.revision_id == before.revision_id
    assert after.status == "approved"
    assert skill.status == "approved"
    assert len(db.list_revisions(skill_id)) == 1
    assert any(event["event_type"] == "revision_state_update" for event in audit)
