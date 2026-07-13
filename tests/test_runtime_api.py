from __future__ import annotations

from fastapi.testclient import TestClient

import api.main as api_module
from runtime.ledger import RuntimeLedger
from runtime.models import RuntimeEvent, RuntimeEventType


def _auth_headers() -> dict[str, str]:
    token = api_module.create_access_token({"sub": "testadmin"})
    return {"Authorization": f"Bearer {token}"}


def _create_runtime_run(database, *, run_id: str = "run-api-test") -> str:
    with RuntimeLedger(database) as ledger:
        rid = ledger.create_run(skill_name="demo", skill_version="1", run_id=run_id)
        ledger.append_event(
            RuntimeEvent(
                run_id=rid,
                event_type=RuntimeEventType.PLAN_CREATED,
                skill_name="demo",
                skill_version="1",
            )
        )
        return rid


def test_runtime_runs_require_authentication(tmp_path, monkeypatch):
    database = tmp_path / "runtime.db"
    run_id = _create_runtime_run(database)
    monkeypatch.setenv("SKILL0_RUNTIME_DB_PATH", str(database))

    client = TestClient(api_module.app)
    response = client.get(f"/api/runs/{run_id}")

    assert response.status_code == 401


def test_runtime_run_and_events_use_configured_database_path(tmp_path, monkeypatch):
    database = tmp_path / "runtime.db"
    run_id = _create_runtime_run(database)
    monkeypatch.setenv("SKILL0_RUNTIME_DB_PATH", str(database))

    client = TestClient(api_module.app)
    headers = _auth_headers()

    run_response = client.get(f"/api/runs/{run_id}", headers=headers)
    assert run_response.status_code == 200
    assert run_response.json()["run_id"] == run_id
    assert run_response.json()["status"] == "planned"

    events_response = client.get(f"/api/runs/{run_id}/events", headers=headers)
    assert events_response.status_code == 200
    assert [event["event_type"] for event in events_response.json()] == [
        "run_created",
        "plan_created",
    ]


def test_runtime_run_missing_from_configured_database_returns_404(tmp_path, monkeypatch):
    database = tmp_path / "runtime.db"
    monkeypatch.setenv("SKILL0_RUNTIME_DB_PATH", str(database))

    client = TestClient(api_module.app)
    response = client.get("/api/runs/missing-run", headers=_auth_headers())

    assert response.status_code == 404
    assert response.json()["detail"] == "Run not found"


def test_runtime_runs_inherit_baseline_api_rate_limit(tmp_path, monkeypatch):
    database = tmp_path / "runtime.db"
    run_id = _create_runtime_run(database)
    monkeypatch.setenv("SKILL0_RUNTIME_DB_PATH", str(database))
    monkeypatch.setattr(api_module, "API_RATE_LIMIT", "1/minute")
    api_module._rate_limit_store.clear()

    client = TestClient(api_module.app)
    headers = _auth_headers()

    first = client.get(f"/api/runs/{run_id}", headers=headers)
    second = client.get(f"/api/runs/{run_id}", headers=headers)

    assert first.status_code == 200
    assert second.status_code == 429
    assert api_module._is_rate_limit_exempt_path(f"/api/runs/{run_id}") is False
