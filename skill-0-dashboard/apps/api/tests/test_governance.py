"""Tests for the Governance Dashboard API — service and router"""

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.dependencies import get_governance_service
from runtime.digest import canonical_digest


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_mock_service():
    """Return a MagicMock that fulfils the GovernanceService contract."""
    svc = MagicMock()

    # Defaults — individual tests override as needed
    svc.get_action_readiness.return_value = {
        "skill_id": "skill_001",
        "can_scan": True,
        "can_test": True,
        "source_path_exists": True,
        "installed_path_exists": True,
        "reasons": [],
    }
    svc.run_scan.return_value = {
        "status": "success",
        "skill_id": "skill_001",
        "processed": 1,
        "results": [{"skill_id": "skill_001", "status": "success", "risk_score": 0}],
        "error_code": None,
        "error_message": None,
        "hint": None,
    }
    svc.run_test.return_value = {
        "status": "success",
        "skill_id": "skill_001",
        "processed": 1,
        "results": [{"skill_id": "skill_001", "status": "success", "fidelity_score": 0.95, "overall_score": 0.95}],
        "error_code": None,
        "error_message": None,
        "hint": None,
    }
    svc.run_scan_batch.return_value = {
        "status": "noop",
        "processed": 0,
        "results": [],
        "error_code": None,
        "error_message": None,
        "hint": None,
    }
    svc.run_test_batch.return_value = {
        "status": "noop",
        "processed": 0,
        "results": [],
        "error_code": None,
        "error_message": None,
        "hint": None,
    }
    return svc


@pytest.fixture
def mock_service():
    return _make_mock_service()


@pytest.fixture
def client(mock_service):
    """TestClient with the mock GovernanceService injected."""
    app.dependency_overrides[get_governance_service] = lambda: mock_service
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Action Readiness
# ---------------------------------------------------------------------------


class TestActionReadiness:
    def test_readiness_all_ok(self, client, mock_service, auth_header):
        resp = client.get(
            "/api/skills/skill_001/action-readiness",
            headers=auth_header,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["can_scan"] is True
        assert data["can_test"] is True
        assert data["reasons"] == []

    def test_readiness_source_missing(self, client, mock_service, auth_header):
        mock_service.get_action_readiness.return_value = {
            "skill_id": "skill_001",
            "can_scan": False,
            "can_test": True,
            "source_path_exists": False,
            "installed_path_exists": True,
            "reasons": ["source_path does not exist: /missing/file.md"],
        }
        resp = client.get(
            "/api/skills/skill_001/action-readiness",
            headers=auth_header,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["can_scan"] is False
        assert len(data["reasons"]) == 1
        assert "source_path" in data["reasons"][0]

    def test_readiness_installed_missing(self, client, mock_service, auth_header):
        mock_service.get_action_readiness.return_value = {
            "skill_id": "skill_001",
            "can_scan": True,
            "can_test": False,
            "source_path_exists": True,
            "installed_path_exists": False,
            "reasons": ["installed_path is not set"],
        }
        resp = client.get(
            "/api/skills/skill_001/action-readiness",
            headers=auth_header,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["can_test"] is False

    def test_readiness_skill_not_found(self, client, mock_service, auth_header):
        mock_service.get_action_readiness.return_value = None
        resp = client.get(
            "/api/skills/nonexistent/action-readiness",
            headers=auth_header,
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Scan action
# ---------------------------------------------------------------------------


class TestScanAction:
    def test_scan_single_skill_success(self, client, mock_service, auth_header):
        resp = client.post(
            "/api/skills/scan?skill_id=skill_001",
            headers=auth_header,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["processed"] == 1
        mock_service.run_scan.assert_called_once_with("skill_001")

    def test_scan_batch(self, client, mock_service, auth_header):
        resp = client.post("/api/skills/scan", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "noop"
        mock_service.run_scan_batch.assert_called_once()

    def test_scan_failed(self, client, mock_service, auth_header):
        mock_service.run_scan.return_value = {
            "status": "failed",
            "skill_id": "skill_001",
            "processed": 0,
            "results": [],
            "error_code": "SOURCE_PATH_MISSING",
            "error_message": "Source path does not exist",
            "hint": "Ensure the skill's source_path is set.",
        }
        resp = client.post(
            "/api/skills/scan?skill_id=skill_001",
            headers=auth_header,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "failed"
        assert data["error_code"] == "SOURCE_PATH_MISSING"


# ---------------------------------------------------------------------------
# Test action
# ---------------------------------------------------------------------------


class TestTestAction:
    def test_test_single_skill_success(self, client, mock_service, auth_header):
        resp = client.post(
            "/api/skills/test?skill_id=skill_001",
            headers=auth_header,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["processed"] == 1
        mock_service.run_test.assert_called_once_with("skill_001")

    def test_test_batch(self, client, mock_service, auth_header):
        resp = client.post("/api/skills/test", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "noop"
        mock_service.run_test_batch.assert_called_once()

    def test_test_failed_installed_missing(self, client, mock_service, auth_header):
        mock_service.run_test.return_value = {
            "status": "failed",
            "skill_id": "skill_001",
            "processed": 0,
            "results": [],
            "error_code": "INSTALLED_PATH_MISSING",
            "error_message": "Installed path does not exist",
            "hint": "Ensure installed_path is set.",
        }
        resp = client.post(
            "/api/skills/test?skill_id=skill_001",
            headers=auth_header,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "failed"
        assert data["error_code"] == "INSTALLED_PATH_MISSING"


# ---------------------------------------------------------------------------
# GovernanceService unit tests
# ---------------------------------------------------------------------------


def test_bind_runtime_artifact_hashes_exact_unique_canonical_document(
    tmp_path, monkeypatch
):
    from apps.api.services.governance import GovernanceService

    document = {
        "meta": {"skill_id": "claude__skill__runtime_fixture"},
        "decomposition": {"actions": [], "rules": [], "directives": []},
    }
    parsed_dir = tmp_path / "parsed"
    parsed_dir.mkdir()
    (parsed_dir / "runtime.json").write_text(
        json.dumps(document), encoding="utf-8"
    )
    monkeypatch.setenv("SKILL0_PARSED_DIR", str(parsed_dir))
    service = object.__new__(GovernanceService)
    service.db = MagicMock()
    service.db.bind_runtime_artifact.return_value = {"revision_id": "rev-1"}

    result = service.bind_runtime_artifact(
        "governance-skill-1",
        canonical_skill_id="claude__skill__runtime_fixture",
        reviewer="reviewer",
    )
    assert result == {"revision_id": "rev-1"}
    service.db.bind_runtime_artifact.assert_called_once_with(
        "governance-skill-1",
        canonical_skill_id="claude__skill__runtime_fixture",
        artifact_digest=canonical_digest(document),
        bound_by="reviewer",
    )


class TestGovernanceServiceReadiness:
    """Unit tests for get_action_readiness."""

    def _make_skill(self, source_path="", installed_path=""):
        skill = MagicMock()
        skill.skill_id = "skill_001"
        skill.source_path = source_path
        skill.installed_path = installed_path
        return skill

    def _make_service(self, skill):
        """Build a GovernanceService with a patched DB."""
        from apps.api.services.governance import GovernanceService  # noqa

        svc = object.__new__(GovernanceService)
        svc.db = MagicMock()
        svc.db.get_skill.return_value = skill
        return svc

    def test_readiness_with_existing_paths(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SKILL0_ALLOWED_PATH_ROOTS", str(tmp_path))
        src = tmp_path / "source.md"
        src.write_text("skill content")
        inst = tmp_path / "installed.md"
        inst.write_text("installed skill")

        skill = self._make_skill(source_path=str(src), installed_path=str(inst))
        svc = self._make_service(skill)

        result = svc.get_action_readiness("skill_001")
        assert result is not None
        assert result["can_scan"] is True
        assert result["can_test"] is True
        assert result["reasons"] == []

    def test_readiness_source_missing(self, tmp_path):
        inst = tmp_path / "installed.md"
        inst.write_text("installed skill")

        skill = self._make_skill(source_path="/nonexistent/file.md", installed_path=str(inst))
        svc = self._make_service(skill)

        result = svc.get_action_readiness("skill_001")
        assert result["can_scan"] is False
        assert result["can_test"] is False  # requires both source + installed
        assert any("source_path" in r for r in result["reasons"])

    def test_readiness_installed_missing(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SKILL0_ALLOWED_PATH_ROOTS", str(tmp_path))
        src = tmp_path / "source.md"
        src.write_text("skill content")

        skill = self._make_skill(source_path=str(src), installed_path="")
        svc = self._make_service(skill)

        result = svc.get_action_readiness("skill_001")
        assert result["can_test"] is False
        assert any("installed_path" in r for r in result["reasons"])

    def test_readiness_skill_not_found(self):
        from apps.api.services.governance import GovernanceService  # noqa

        svc = object.__new__(GovernanceService)
        svc.db = MagicMock()
        svc.db.get_skill.return_value = None

        result = svc.get_action_readiness("ghost")
        assert result is None

    def test_readiness_rejects_paths_outside_allowed_roots(self, tmp_path, monkeypatch):
        allowed_root = tmp_path / "allowed"
        allowed_root.mkdir()
        monkeypatch.setenv("SKILL0_ALLOWED_PATH_ROOTS", str(allowed_root))

        external_file = tmp_path / "outside.md"
        external_file.write_text("outside")
        skill = self._make_skill(source_path=str(external_file), installed_path=str(external_file))
        svc = self._make_service(skill)

        result = svc.get_action_readiness("skill_001")
        assert result is not None
        assert result["can_scan"] is False
        assert result["can_test"] is False
        assert any("outside allowed roots" in reason for reason in result["reasons"])


class TestGovernanceServiceRunScan:
    """Unit tests for run_scan with a mocked DB and scanner."""

    def _make_service_with_skill(self, source_path=""):
        from apps.api.services.governance import GovernanceService  # noqa

        svc = object.__new__(GovernanceService)
        svc.db = MagicMock()
        skill = MagicMock()
        skill.skill_id = "skill_001"
        skill.source_path = source_path
        skill.installed_path = ""
        svc.db.get_skill.return_value = skill
        return svc

    def test_scan_skill_not_found(self):
        from apps.api.services.governance import GovernanceService  # noqa

        svc = object.__new__(GovernanceService)
        svc.db = MagicMock()
        svc.db.get_skill.return_value = None

        result = svc.run_scan("ghost")
        assert result["status"] == "failed"
        assert result["error_code"] == "PATH_NOT_FOUND"

    def test_scan_source_path_missing(self):
        svc = self._make_service_with_skill(source_path="/nonexistent/file.md")
        result = svc.run_scan("skill_001")
        assert result["status"] == "failed"
        assert result["error_code"] == "SOURCE_PATH_MISSING"

    def test_scan_runtime_error(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SKILL0_ALLOWED_PATH_ROOTS", str(tmp_path))
        src = tmp_path / "source.md"
        src.write_text("skill content")
        svc = self._make_service_with_skill(source_path=str(src))

        mock_module = MagicMock()
        mock_module.AdvancedSkillAnalyzer.side_effect = RuntimeError("scanner crash")
        with patch.dict("sys.modules", {"advanced_skill_analyzer": mock_module}):
            result = svc.run_scan("skill_001")
        assert result["status"] == "failed"
        assert result["error_code"] == "SCAN_RUNTIME_ERROR"

    def test_scan_source_path_not_allowed(self, tmp_path, monkeypatch):
        allowed_root = tmp_path / "allowed"
        allowed_root.mkdir()
        monkeypatch.setenv("SKILL0_ALLOWED_PATH_ROOTS", str(allowed_root))

        external_file = tmp_path / "outside.md"
        external_file.write_text("outside")
        svc = self._make_service_with_skill(source_path=str(external_file))

        result = svc.run_scan("skill_001")
        assert result["status"] == "failed"
        assert result["error_code"] == "SOURCE_PATH_NOT_ALLOWED"


class TestGovernanceServiceRunTest:
    """Unit tests for run_test with a mocked DB."""

    def _make_service(self, source_path="", installed_path=""):
        from apps.api.services.governance import GovernanceService  # noqa

        svc = object.__new__(GovernanceService)
        svc.db = MagicMock()
        skill = MagicMock()
        skill.skill_id = "skill_001"
        skill.source_path = source_path
        skill.installed_path = installed_path
        svc.db.get_skill.return_value = skill
        return svc

    def test_test_skill_not_found(self):
        from apps.api.services.governance import GovernanceService  # noqa

        svc = object.__new__(GovernanceService)
        svc.db = MagicMock()
        svc.db.get_skill.return_value = None

        result = svc.run_test("ghost")
        assert result["status"] == "failed"
        assert result["error_code"] == "PATH_NOT_FOUND"

    def test_test_installed_path_missing(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SKILL0_ALLOWED_PATH_ROOTS", str(tmp_path))
        src = tmp_path / "source.md"
        src.write_text("skill")
        svc = self._make_service(source_path=str(src), installed_path="")
        result = svc.run_test("skill_001")
        assert result["status"] == "failed"
        assert result["error_code"] == "INSTALLED_PATH_MISSING"

    def test_test_installed_path_not_allowed(self, tmp_path, monkeypatch):
        allowed_root = tmp_path / "allowed"
        allowed_root.mkdir()
        monkeypatch.setenv("SKILL0_ALLOWED_PATH_ROOTS", str(allowed_root))

        source = allowed_root / "source.md"
        source.write_text("source")
        external_installed = tmp_path / "outside.md"
        external_installed.write_text("installed")
        svc = self._make_service(source_path=str(source), installed_path=str(external_installed))

        result = svc.run_test("skill_001")
        assert result["status"] == "failed"
        assert result["error_code"] == "INSTALLED_PATH_NOT_ALLOWED"


class TestGovernanceServiceActionJobs:
    def _make_service(self, tmp_path, monkeypatch):
        from apps.api.services.governance import GovernanceService  # noqa

        db_path = tmp_path / "governance.db"
        monkeypatch.setenv("SKILL0_GOVERNANCE_DB_PATH", str(db_path))
        original_recover = GovernanceService._recover_incomplete_action_jobs
        monkeypatch.setattr(GovernanceService, "_recover_incomplete_action_jobs", lambda self: None)
        svc = GovernanceService()
        monkeypatch.setattr(GovernanceService, "_recover_incomplete_action_jobs", original_recover)
        return svc

    def test_enqueue_action_job_creates_queued_job(self, tmp_path, monkeypatch):
        svc = self._make_service(tmp_path, monkeypatch)
        monkeypatch.setattr(svc, "_start_action_job_runner", lambda job_id: None)

        job = svc.enqueue_action_job(
            job_type="scan_batch",
            skill_ids=["skill_001"],
            requested_by="reviewer",
            selection_mode="explicit",
            max_attempts=2,
        )

        assert job["status"] == "queued"
        assert job["job_type"] == "scan_batch"
        assert job["requested_by"] == "reviewer"
        assert job["summary"]["queued"] == 1
        items = svc.get_action_job_items(job["job_id"])
        assert items is not None
        assert len(items) == 1
        assert items[0]["skill_id"] == "skill_001"
        assert items[0]["target_revision_id"] is None
        assert items[0]["attempt_number"] == 1
        assert items[0]["max_attempts"] == 2
        assert items[0]["claimed_by"] is None
        assert items[0]["lease_expires_at"] is None
        assert items[0]["retry_of_item_id"] is None
        assert items[0]["error_code"] is None
        assert items[0]["suggested_next_step"] == "wait_for_worker"

    def test_run_action_job_marks_success_and_failure(self, tmp_path, monkeypatch):
        svc = self._make_service(tmp_path, monkeypatch)
        monkeypatch.setattr(svc, "_start_action_job_runner", lambda job_id: None)

        def fake_run_scan(skill_id):
            if skill_id == "skill_ok":
                return {
                    "status": "success",
                    "skill_id": skill_id,
                    "processed": 1,
                    "results": [{"skill_id": skill_id, "status": "success"}],
                }
            return {
                "status": "failed",
                "skill_id": skill_id,
                "processed": 0,
                "results": [],
                "error_code": "SCAN_RUNTIME_ERROR",
                "error_message": "scanner crash",
            }

        monkeypatch.setattr(svc, "run_scan", fake_run_scan)
        job = svc.enqueue_action_job(
            job_type="scan_batch",
            skill_ids=["skill_ok", "skill_bad"],
            requested_by="reviewer",
            selection_mode="explicit",
            max_attempts=2,
        )

        svc._run_action_job(job["job_id"])

        updated = svc.get_action_job(job["job_id"])
        assert updated is not None
        assert updated["status"] == "completed_with_failures"
        assert updated["summary"]["succeeded"] == 1
        assert updated["summary"]["failed"] == 1

    def test_retry_action_job_item_creates_follow_on_job(self, tmp_path, monkeypatch):
        svc = self._make_service(tmp_path, monkeypatch)
        monkeypatch.setattr(svc, "_start_action_job_runner", lambda job_id: None)
        monkeypatch.setattr(
            svc,
            "run_scan",
            lambda skill_id: {
                "status": "failed",
                "skill_id": skill_id,
                "processed": 0,
                "results": [],
                "error_code": "SCAN_RUNTIME_ERROR",
                "error_message": "scanner crash",
            },
        )

        job = svc.enqueue_action_job(
            job_type="scan_batch",
            skill_ids=["skill_retry"],
            requested_by="reviewer",
            selection_mode="explicit",
            max_attempts=2,
        )
        svc._run_action_job(job["job_id"])
        item = svc.get_action_job_items(job["job_id"])[0]

        retry_job = svc.retry_action_job_item(
            job_id=job["job_id"],
            item_id=item["item_id"],
            requested_by="reviewer",
        )

        retry_items = svc.get_action_job_items(retry_job["job_id"])
        assert retry_job["selection_mode"] == "retry_item"
        assert retry_items[0]["attempt_number"] == 2
        assert retry_items[0]["retry_of_item_id"] == item["item_id"]
        assert retry_items[0]["suggested_next_step"] == "wait_for_worker"

    def test_claim_next_action_job_item_is_atomic(self, tmp_path, monkeypatch):
        svc = self._make_service(tmp_path, monkeypatch)
        monkeypatch.setattr(svc, "_start_action_job_runner", lambda job_id: None)

        job = svc.enqueue_action_job(
            job_type="scan_batch",
            skill_ids=["skill_claim"],
            requested_by="reviewer",
            selection_mode="explicit",
            max_attempts=2,
        )

        claimed = svc.db.claim_next_action_job_item(job["job_id"], "worker-a", lease_seconds=60)
        duplicate_claim = svc.db.claim_next_action_job_item(job["job_id"], "worker-b", lease_seconds=60)

        assert claimed is not None
        assert claimed["skill_id"] == "skill_claim"
        assert claimed["claimed_by"] == "worker-a"
        assert claimed["lease_expires_at"] is not None
        assert duplicate_claim is None
        job_summary = svc.get_action_job(job["job_id"])
        assert job_summary is not None
        assert job_summary["active_workers"] == ["worker-a"]
        assert job_summary["active_lease_expires_at"] is not None
        assert job_summary["last_item_started_at"] is not None

    def test_finalize_action_job_does_not_close_while_items_are_running(self, tmp_path, monkeypatch):
        svc = self._make_service(tmp_path, monkeypatch)
        monkeypatch.setattr(svc, "_start_action_job_runner", lambda job_id: None)

        job = svc.enqueue_action_job(
            job_type="scan_batch",
            skill_ids=["skill_active"],
            requested_by="reviewer",
            selection_mode="explicit",
            max_attempts=2,
        )
        svc.db.update_action_job(job["job_id"], status="running", started_at="2026-04-03T02:00:00Z")
        claimed = svc.db.claim_next_action_job_item(job["job_id"], "worker-a", lease_seconds=60)

        summary = svc._finalize_action_job(job["job_id"])

        assert claimed is not None
        assert summary is not None
        assert summary["status"] == "running"
        assert summary["completed_at"] is None

    def test_cancel_action_job_marks_pending_items_cancelled(self, tmp_path, monkeypatch):
        svc = self._make_service(tmp_path, monkeypatch)
        monkeypatch.setattr(svc, "_start_action_job_runner", lambda job_id: None)

        job = svc.enqueue_action_job(
            job_type="scan_batch",
            skill_ids=["skill_cancel_a", "skill_cancel_b"],
            requested_by="reviewer",
            selection_mode="explicit",
            max_attempts=2,
        )

        cancelled = svc.cancel_action_job(
            job_id=job["job_id"],
            requested_by="reviewer",
        )
        items = svc.get_action_job_items(job["job_id"])

        assert cancelled["status"] == "cancelled"
        assert cancelled["error_code"] == "JOB_CANCELLED"
        assert cancelled["cancelled_by"] == "reviewer"
        assert cancelled["cancelled_at"] is not None
        assert all(item["status"] == "cancelled" for item in items)
        assert all(item["suggested_next_step"] == "review_cancel_trace" for item in items)
        assert svc.db.claim_next_action_job_item(job["job_id"], "worker-a", lease_seconds=60) is None

    def test_cancel_action_job_stops_new_claims_but_preserves_running_item(self, tmp_path, monkeypatch):
        svc = self._make_service(tmp_path, monkeypatch)
        monkeypatch.setattr(svc, "_start_action_job_runner", lambda job_id: None)

        job = svc.enqueue_action_job(
            job_type="scan_batch",
            skill_ids=["skill_running", "skill_waiting"],
            requested_by="reviewer",
            selection_mode="explicit",
            max_attempts=2,
        )
        running_item = svc.db.claim_next_action_job_item(job["job_id"], "worker-a", lease_seconds=60)

        cancelled = svc.cancel_action_job(
            job_id=job["job_id"],
            requested_by="reviewer",
        )
        items_after_cancel = svc.get_action_job_items(job["job_id"])

        assert running_item is not None
        assert cancelled["status"] == "cancelled"
        assert cancelled["cancelled_by"] == "reviewer"
        assert cancelled["cancelled_at"] is not None
        assert svc.db.claim_next_action_job_item(job["job_id"], "worker-b", lease_seconds=60) is None
        assert next(item for item in items_after_cancel if item["skill_id"] == "skill_waiting")["status"] == "cancelled"
        assert next(item for item in items_after_cancel if item["skill_id"] == "skill_running")["status"] == "running"

        svc.db.update_action_job_item(
            running_item["item_id"],
            status="succeeded",
            completed_at="2026-04-03T02:00:05Z",
            result={"status": "success", "skill_id": "skill_running"},
            error_code=None,
            error_message=None,
            claimed_by=None,
            lease_expires_at=None,
        )

        finalized = svc._finalize_action_job(job["job_id"])
        assert finalized is not None
        assert finalized["status"] == "cancelled"
        assert finalized["completed_at"] is not None

    def test_recovers_only_expired_running_jobs_from_database(self, tmp_path, monkeypatch):
        from apps.api.services.governance import GovernanceService  # noqa

        svc = self._make_service(tmp_path, monkeypatch)
        monkeypatch.setattr(svc, "_start_action_job_runner", lambda job_id: None)

        job = svc.enqueue_action_job(
            job_type="scan_batch",
            skill_ids=["skill_recover"],
            requested_by="reviewer",
            selection_mode="explicit",
            max_attempts=2,
        )
        item = svc.get_action_job_items(job["job_id"])[0]
        svc.db.update_action_job(job["job_id"], status="running", started_at="2026-04-03T01:00:00Z")
        svc.db.update_action_job_item(
            item["item_id"],
            status="running",
            started_at="2026-04-03T01:00:01Z",
            completed_at=None,
            error_code="SCAN_RUNTIME_ERROR",
            error_message="stale failure",
            lease_expires_at="2026-04-03T01:00:30Z",
            claimed_by="worker-stale",
        )

        recovered_jobs = []
        monkeypatch.setattr(GovernanceService, "_start_action_job_runner", lambda self, job_id: recovered_jobs.append(job_id))
        recovered_service = GovernanceService()

        assert recovered_jobs == [job["job_id"]]
        recovered_job = recovered_service.get_action_job(job["job_id"])
        recovered_item = recovered_service.get_action_job_items(job["job_id"])[0]
        assert recovered_job is not None
        assert recovered_job["status"] == "queued"
        assert recovered_item["status"] == "queued"
        assert recovered_item["started_at"] is None
        assert recovered_item["completed_at"] is None
        assert recovered_item["error_code"] is None
        assert recovered_item["error_message"] is None
        assert recovered_item["claimed_by"] is None
        assert recovered_item["lease_expires_at"] is None

    def test_keeps_live_running_job_claimed_during_recovery(self, tmp_path, monkeypatch):
        from apps.api.services.governance import GovernanceService  # noqa

        svc = self._make_service(tmp_path, monkeypatch)
        monkeypatch.setattr(svc, "_start_action_job_runner", lambda job_id: None)

        job = svc.enqueue_action_job(
            job_type="scan_batch",
            skill_ids=["skill_live"],
            requested_by="reviewer",
            selection_mode="explicit",
            max_attempts=2,
        )
        item = svc.get_action_job_items(job["job_id"])[0]
        svc.db.update_action_job(job["job_id"], status="running", started_at="2026-04-03T01:00:00Z")
        svc.db.update_action_job_item(
            item["item_id"],
            status="running",
            started_at="2026-04-03T01:00:01Z",
            completed_at=None,
            lease_expires_at="2099-04-03T01:00:30Z",
            claimed_by="worker-live",
        )

        recovered_jobs = []
        monkeypatch.setattr(GovernanceService, "_start_action_job_runner", lambda self, job_id: recovered_jobs.append(job_id))
        recovered_service = GovernanceService()

        assert recovered_jobs == []
        recovered_job = recovered_service.get_action_job(job["job_id"])
        recovered_item = recovered_service.get_action_job_items(job["job_id"])[0]
        assert recovered_job is not None
        assert recovered_job["status"] == "running"
        assert recovered_item["status"] == "running"
        assert recovered_item["claimed_by"] == "worker-live"
        assert recovered_item["lease_expires_at"] == "2099-04-03T01:00:30Z"

    def test_run_action_job_refreshes_item_lease_with_heartbeat(self, tmp_path, monkeypatch):
        svc = self._make_service(tmp_path, monkeypatch)
        monkeypatch.setattr(svc, "_start_action_job_runner", lambda job_id: None)
        monkeypatch.setenv("SKILL0_ACTION_JOB_LEASE_SECONDS", "5")
        monkeypatch.setenv("SKILL0_ACTION_JOB_HEARTBEAT_SECONDS", "0.05")

        refresh_calls = []
        original_refresh = svc.db.refresh_action_job_item_lease

        def tracked_refresh(item_id, worker_id, lease_seconds):
            refresh_calls.append((item_id, worker_id, lease_seconds))
            return original_refresh(item_id, worker_id, lease_seconds)

        monkeypatch.setattr(svc.db, "refresh_action_job_item_lease", tracked_refresh)

        def slow_scan(skill_id):
            import time
            time.sleep(0.2)
            return {
                "status": "success",
                "skill_id": skill_id,
                "processed": 1,
                "results": [{"skill_id": skill_id, "status": "success"}],
            }

        monkeypatch.setattr(svc, "run_scan", slow_scan)

        job = svc.enqueue_action_job(
            job_type="scan_batch",
            skill_ids=["skill_heartbeat"],
            requested_by="reviewer",
            selection_mode="explicit",
            max_attempts=2,
        )

        svc._run_action_job(job["job_id"])

        assert refresh_calls

    def test_test_source_path_missing(self, tmp_path):
        from apps.api.services.governance import GovernanceService  # noqa

        inst = tmp_path / "installed.md"
        inst.write_text("installed")
        svc = object.__new__(GovernanceService)
        svc.db = MagicMock()
        skill = MagicMock()
        skill.skill_id = "skill_001"
        skill.source_path = "/missing/file.md"
        skill.installed_path = str(inst)
        svc.db.get_skill.return_value = skill
        result = svc.run_test("skill_001")
        assert result["status"] == "failed"
        assert result["error_code"] == "SOURCE_PATH_MISSING"
