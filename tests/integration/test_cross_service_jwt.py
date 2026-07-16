from __future__ import annotations

from pathlib import Path
import sys
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

import api.main as core_api
from runtime.ledger import RuntimeLedger


DASHBOARD_ROOT = Path(__file__).resolve().parents[2] / "skill-0-dashboard"
sys.path.insert(0, str(DASHBOARD_ROOT))

from apps.api.dependencies import get_governance_service  # noqa: E402
from apps.api.main import app as dashboard_app  # noqa: E402


def test_core_issued_jwt_authenticates_dashboard_and_runtime(
    tmp_path, monkeypatch
):
    token = core_api.create_access_token({"sub": "cross-service-reviewer"})
    headers = {"Authorization": f"Bearer {token}"}

    service = MagicMock()
    service.get_stats_overview.return_value = {
        "total_skills": 0,
        "pending_count": 0,
        "approved_count": 0,
        "rejected_count": 0,
        "blocked_count": 0,
        "high_risk_count": 0,
        "avg_fidelity_score": 0.0,
        "avg_equivalence_score": 0.0,
    }
    dashboard_app.dependency_overrides[get_governance_service] = lambda: service
    try:
        dashboard_response = TestClient(dashboard_app).get(
            "/api/stats", headers=headers
        )
    finally:
        dashboard_app.dependency_overrides.pop(get_governance_service, None)
    assert dashboard_response.status_code == 200

    runtime_db = tmp_path / "runtime.db"
    with RuntimeLedger(runtime_db) as ledger:
        run_id = ledger.create_run(skill_name="shared-jwt", skill_version="1")
    monkeypatch.setenv("SKILL0_RUNTIME_DB_PATH", str(runtime_db))
    runtime_response = TestClient(core_api.app).get(
        f"/api/runs/{run_id}", headers=headers
    )
    assert runtime_response.status_code == 200
    assert runtime_response.json()["run_id"] == run_id
