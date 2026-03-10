"""Tests for the Governance Dashboard API — service and router"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
from typing import Optional

import pytest
from fastapi.testclient import TestClient

# Ensure the dashboard API package is importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api.main import app  # noqa: E402 — dashboard API
from api.dependencies import get_governance_service  # noqa: E402


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
        "results": [{"skill_id": "skill_001", "status": "success", "overall_score": 0.95}],
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
    def test_readiness_all_ok(self, client, mock_service):
        resp = client.get("/api/skills/skill_001/action-readiness")
        assert resp.status_code == 200
        data = resp.json()
        assert data["can_scan"] is True
        assert data["can_test"] is True
        assert data["reasons"] == []

    def test_readiness_source_missing(self, client, mock_service):
        mock_service.get_action_readiness.return_value = {
            "skill_id": "skill_001",
            "can_scan": False,
            "can_test": True,
            "source_path_exists": False,
            "installed_path_exists": True,
            "reasons": ["source_path does not exist: /missing/file.md"],
        }
        resp = client.get("/api/skills/skill_001/action-readiness")
        assert resp.status_code == 200
        data = resp.json()
        assert data["can_scan"] is False
        assert len(data["reasons"]) == 1
        assert "source_path" in data["reasons"][0]

    def test_readiness_installed_missing(self, client, mock_service):
        mock_service.get_action_readiness.return_value = {
            "skill_id": "skill_001",
            "can_scan": True,
            "can_test": False,
            "source_path_exists": True,
            "installed_path_exists": False,
            "reasons": ["installed_path is not set"],
        }
        resp = client.get("/api/skills/skill_001/action-readiness")
        assert resp.status_code == 200
        data = resp.json()
        assert data["can_test"] is False

    def test_readiness_skill_not_found(self, client, mock_service):
        mock_service.get_action_readiness.return_value = None
        resp = client.get("/api/skills/nonexistent/action-readiness")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Scan action
# ---------------------------------------------------------------------------


class TestScanAction:
    def test_scan_single_skill_success(self, client, mock_service):
        resp = client.post("/api/skills/scan?skill_id=skill_001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["processed"] == 1
        mock_service.run_scan.assert_called_once_with("skill_001")

    def test_scan_batch(self, client, mock_service):
        resp = client.post("/api/skills/scan")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "noop"
        mock_service.run_scan_batch.assert_called_once()

    def test_scan_failed(self, client, mock_service):
        mock_service.run_scan.return_value = {
            "status": "failed",
            "skill_id": "skill_001",
            "processed": 0,
            "results": [],
            "error_code": "SOURCE_PATH_MISSING",
            "error_message": "Source path does not exist",
            "hint": "Ensure the skill's source_path is set.",
        }
        resp = client.post("/api/skills/scan?skill_id=skill_001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "failed"
        assert data["error_code"] == "SOURCE_PATH_MISSING"


# ---------------------------------------------------------------------------
# Test action
# ---------------------------------------------------------------------------


class TestTestAction:
    def test_test_single_skill_success(self, client, mock_service):
        resp = client.post("/api/skills/test?skill_id=skill_001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["processed"] == 1
        mock_service.run_test.assert_called_once_with("skill_001")

    def test_test_batch(self, client, mock_service):
        resp = client.post("/api/skills/test")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "noop"
        mock_service.run_test_batch.assert_called_once()

    def test_test_failed_installed_missing(self, client, mock_service):
        mock_service.run_test.return_value = {
            "status": "failed",
            "skill_id": "skill_001",
            "processed": 0,
            "results": [],
            "error_code": "INSTALLED_PATH_MISSING",
            "error_message": "Installed path does not exist",
            "hint": "Ensure installed_path is set.",
        }
        resp = client.post("/api/skills/test?skill_id=skill_001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "failed"
        assert data["error_code"] == "INSTALLED_PATH_MISSING"


# ---------------------------------------------------------------------------
# GovernanceService unit tests
# ---------------------------------------------------------------------------


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
        from api.services.governance import GovernanceService  # noqa

        svc = object.__new__(GovernanceService)
        svc.db = MagicMock()
        svc.db.get_skill.return_value = skill
        return svc

    def test_readiness_with_existing_paths(self, tmp_path):
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

    def test_readiness_installed_missing(self, tmp_path):
        src = tmp_path / "source.md"
        src.write_text("skill content")

        skill = self._make_skill(source_path=str(src), installed_path="")
        svc = self._make_service(skill)

        result = svc.get_action_readiness("skill_001")
        assert result["can_test"] is False
        assert any("installed_path" in r for r in result["reasons"])

    def test_readiness_skill_not_found(self):
        from api.services.governance import GovernanceService  # noqa

        svc = object.__new__(GovernanceService)
        svc.db = MagicMock()
        svc.db.get_skill.return_value = None

        result = svc.get_action_readiness("ghost")
        assert result is None


class TestGovernanceServiceRunScan:
    """Unit tests for run_scan with a mocked DB and scanner."""

    def _make_service_with_skill(self, source_path=""):
        from api.services.governance import GovernanceService  # noqa

        svc = object.__new__(GovernanceService)
        svc.db = MagicMock()
        skill = MagicMock()
        skill.skill_id = "skill_001"
        skill.source_path = source_path
        skill.installed_path = ""
        svc.db.get_skill.return_value = skill
        return svc

    def test_scan_skill_not_found(self):
        from api.services.governance import GovernanceService  # noqa

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

    def test_scan_runtime_error(self, tmp_path):
        src = tmp_path / "source.md"
        src.write_text("skill content")
        svc = self._make_service_with_skill(source_path=str(src))

        mock_module = MagicMock()
        mock_module.AdvancedSkillAnalyzer.side_effect = RuntimeError("scanner crash")
        with patch.dict("sys.modules", {"advanced_skill_analyzer": mock_module}):
            result = svc.run_scan("skill_001")
        assert result["status"] == "failed"
        assert result["error_code"] == "SCAN_RUNTIME_ERROR"


class TestGovernanceServiceRunTest:
    """Unit tests for run_test with a mocked DB."""

    def _make_service(self, source_path="", installed_path=""):
        from api.services.governance import GovernanceService  # noqa

        svc = object.__new__(GovernanceService)
        svc.db = MagicMock()
        skill = MagicMock()
        skill.skill_id = "skill_001"
        skill.source_path = source_path
        skill.installed_path = installed_path
        svc.db.get_skill.return_value = skill
        return svc

    def test_test_skill_not_found(self):
        from api.services.governance import GovernanceService  # noqa

        svc = object.__new__(GovernanceService)
        svc.db = MagicMock()
        svc.db.get_skill.return_value = None

        result = svc.run_test("ghost")
        assert result["status"] == "failed"
        assert result["error_code"] == "PATH_NOT_FOUND"

    def test_test_installed_path_missing(self, tmp_path):
        src = tmp_path / "source.md"
        src.write_text("skill")
        svc = self._make_service(source_path=str(src), installed_path="")
        result = svc.run_test("skill_001")
        assert result["status"] == "failed"
        assert result["error_code"] == "INSTALLED_PATH_MISSING"

    def test_test_source_path_missing(self, tmp_path):
        inst = tmp_path / "installed.md"
        inst.write_text("installed")
        svc = self._make_service(source_path="/missing/file.md", installed_path=str(inst))
        result = svc.run_test("skill_001")
        assert result["status"] == "failed"
        assert result["error_code"] == "SOURCE_PATH_MISSING"
