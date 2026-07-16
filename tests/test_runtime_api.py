from __future__ import annotations

import json

from fastapi.testclient import TestClient

import api.main as api_module
from runtime.ledger import RuntimeLedger
from runtime.models import RuntimeEvent, RuntimeEventType


def _skill_document(contract: dict) -> dict:
    return {
        "meta": {
            "skill_id": "claude__skill__runtime_api_fixture",
            "name": contract["skill_ref"]["name"],
            "skill_layer": "claude_skill",
            "title": contract["skill_ref"]["name"],
            "description": "Runtime API test fixture",
            "schema_version": "2.4.0",
            "parse_timestamp": "2026-07-16T00:00:00Z",
            "version": contract["skill_ref"]["version"],
        },
        "decomposition": {
            "actions": [
                {
                    "id": item["action_id"],
                    "name": item["action_id"],
                    "action_type": "transform",
                    "description": "Runtime action fixture",
                    "deterministic": True,
                    "immutable_elements": [],
                    "mutable_elements": [],
                    "side_effects": [],
                }
                for item in contract["action_bindings"]
            ],
            "rules": [
                {
                    "id": item["rule_id"],
                    "name": item["rule_id"],
                    "condition_type": "validation",
                    "condition_expression": "fixture",
                    "returns": "boolean",
                    "description": "Runtime rule fixture",
                }
                for item in contract["governance"]["rule_policy_bindings"]
            ],
            "directives": [
                {
                    "id": item,
                    "name": item,
                    "directive_type": "completion",
                    "description": "Runtime directive fixture",
                    "decomposable": False,
                }
                for item in contract["directive_manifest"]["include"]
            ],
        },
    }


def _create_payload(
    read_json,
    parsed_dir,
    fixture="examples/runtime-contract.read-only.json",
    *,
    keep_validation=False,
):
    contract = read_json(fixture)
    if not keep_validation:
        for binding in contract["action_bindings"]:
            binding["validation"] = {
                "precondition_rule_ids": [],
                "postcondition_rule_ids": [],
            }
    skill_document = _skill_document(contract)
    parsed_dir.mkdir(parents=True, exist_ok=True)
    (parsed_dir / "runtime-api-skill.json").write_text(
        json.dumps(skill_document), encoding="utf-8"
    )
    return {
        "skill_id": skill_document["meta"]["skill_id"],
        "runtime_contract": contract,
        "parameters": {},
    }


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


def test_create_runtime_run_requires_authentication(tmp_path, monkeypatch, read_json):
    monkeypatch.setenv("SKILL0_RUNTIME_DB_PATH", str(tmp_path / "runtime.db"))
    parsed_dir = tmp_path / "parsed"
    monkeypatch.setenv("SKILL0_PARSED_DIR", str(parsed_dir))
    response = TestClient(api_module.app).post(
        "/api/runs", json=_create_payload(read_json, parsed_dir)
    )
    assert response.status_code == 401


def test_create_runtime_run_is_dry_run_only(tmp_path, monkeypatch, read_json):
    monkeypatch.setenv("SKILL0_RUNTIME_DB_PATH", str(tmp_path / "runtime.db"))
    parsed_dir = tmp_path / "parsed"
    monkeypatch.setenv("SKILL0_PARSED_DIR", str(parsed_dir))
    payload = _create_payload(read_json, parsed_dir)
    payload["dry_run"] = False
    response = TestClient(api_module.app).post(
        "/api/runs", json=payload, headers=_auth_headers()
    )
    assert response.status_code == 422


def test_create_runtime_run_executes_deterministic_simulation(
    tmp_path, monkeypatch, read_json
):
    database = tmp_path / "runtime.db"
    monkeypatch.setenv("SKILL0_RUNTIME_DB_PATH", str(database))
    parsed_dir = tmp_path / "parsed"
    monkeypatch.setenv("SKILL0_PARSED_DIR", str(parsed_dir))
    response = TestClient(api_module.app).post(
        "/api/runs", json=_create_payload(read_json, parsed_dir), headers=_auth_headers()
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "succeeded"
    assert body["output_summary"] == {"a_001": ["action_id", "dry_run", "id"]}
    with RuntimeLedger(database) as ledger:
        events = ledger.list_events(body["run_id"])
        assert any(event.event_type == RuntimeEventType.PREFLIGHT_PASSED for event in events)
        assert all(event.payload.get("dry_run", True) is True for event in events)


def test_create_runtime_run_rejects_unvalidated_rule(tmp_path, monkeypatch, read_json):
    monkeypatch.setenv("SKILL0_RUNTIME_DB_PATH", str(tmp_path / "runtime.db"))
    parsed_dir = tmp_path / "parsed"
    monkeypatch.setenv("SKILL0_PARSED_DIR", str(parsed_dir))
    payload = _create_payload(read_json, parsed_dir, keep_validation=True)
    response = TestClient(api_module.app).post(
        "/api/runs", json=payload, headers=_auth_headers()
    )
    assert response.status_code == 422
    assert "server-side evaluator is unavailable" in response.json()["detail"]


def test_create_runtime_run_rejects_non_test_adapter(tmp_path, monkeypatch, read_json):
    monkeypatch.setenv("SKILL0_RUNTIME_DB_PATH", str(tmp_path / "runtime.db"))
    parsed_dir = tmp_path / "parsed"
    monkeypatch.setenv("SKILL0_PARSED_DIR", str(parsed_dir))
    payload = _create_payload(read_json, parsed_dir)
    payload["runtime_contract"]["action_bindings"][0]["adapter"]["kind"] = "command"
    response = TestClient(api_module.app).post(
        "/api/runs", json=payload, headers=_auth_headers()
    )
    assert response.status_code == 422
    assert "only test adapters" in response.json()["detail"]


def test_create_runtime_run_rejects_malformed_adapter(tmp_path, monkeypatch, read_json):
    monkeypatch.setenv("SKILL0_RUNTIME_DB_PATH", str(tmp_path / "runtime.db"))
    parsed_dir = tmp_path / "parsed"
    monkeypatch.setenv("SKILL0_PARSED_DIR", str(parsed_dir))
    payload = _create_payload(read_json, parsed_dir)
    payload["runtime_contract"]["action_bindings"][0]["adapter"] = "test"
    response = TestClient(api_module.app).post(
        "/api/runs", json=payload, headers=_auth_headers()
    )
    assert response.status_code == 422
    assert "only test adapters" in response.json()["detail"]


def test_create_runtime_run_returns_approval_boundary(tmp_path, monkeypatch, read_json):
    monkeypatch.setenv("SKILL0_RUNTIME_DB_PATH", str(tmp_path / "runtime.db"))
    parsed_dir = tmp_path / "parsed"
    monkeypatch.setenv("SKILL0_PARSED_DIR", str(parsed_dir))
    payload = _create_payload(
        read_json, parsed_dir, "examples/runtime-contract.manual-approval.json"
    )
    response = TestClient(api_module.app).post(
        "/api/runs", json=payload, headers=_auth_headers()
    )
    assert response.status_code == 201
    assert response.json()["status"] == "awaiting_approval"


def test_create_runtime_run_rejects_caller_supplied_approval(
    tmp_path, monkeypatch, read_json
):
    monkeypatch.setenv("SKILL0_RUNTIME_DB_PATH", str(tmp_path / "runtime.db"))
    parsed_dir = tmp_path / "parsed"
    monkeypatch.setenv("SKILL0_PARSED_DIR", str(parsed_dir))
    payload = _create_payload(
        read_json, parsed_dir, "examples/runtime-contract.manual-approval.json"
    )
    payload["approved_action_ids"] = ["a_010"]
    response = TestClient(api_module.app).post(
        "/api/runs", json=payload, headers=_auth_headers()
    )
    assert response.status_code == 422


def test_create_runtime_run_requires_canonical_skill(tmp_path, monkeypatch, read_json):
    monkeypatch.setenv("SKILL0_RUNTIME_DB_PATH", str(tmp_path / "runtime.db"))
    parsed_dir = tmp_path / "parsed"
    monkeypatch.setenv("SKILL0_PARSED_DIR", str(parsed_dir))
    payload = _create_payload(read_json, parsed_dir)
    payload["skill_id"] = "claude__skill__missing"
    response = TestClient(api_module.app).post(
        "/api/runs", json=payload, headers=_auth_headers()
    )
    assert response.status_code == 404


def test_events_redact_recovery_material(tmp_path, monkeypatch, read_json):
    database = tmp_path / "runtime.db"
    monkeypatch.setenv("SKILL0_RUNTIME_DB_PATH", str(database))
    parsed_dir = tmp_path / "parsed"
    monkeypatch.setenv("SKILL0_PARSED_DIR", str(parsed_dir))
    payload = _create_payload(
        read_json, parsed_dir, "examples/runtime-contract.auto-rollback.json"
    )
    payload["parameters"] = {"customer_id": "42"}
    created = TestClient(api_module.app).post(
        "/api/runs", json=payload, headers=_auth_headers()
    )
    assert created.status_code == 201
    assert created.json()["status"] == "succeeded"
    response = TestClient(api_module.app).get(
        f"/api/runs/{created.json()['run_id']}/events", headers=_auth_headers()
    )
    assert response.status_code == 200
    succeeded = next(
        event for event in response.json() if event["event_type"] == "action_succeeded"
    )
    assert "resolved_compensation_parameters" not in succeeded["payload"]
    assert "external_resource_id" not in succeeded
    assert succeeded["external_resource_id_present"] is True
    assert succeeded["payload"]["resolved_compensation_parameter_keys"] == [
        "contact_id"
    ]


def test_secret_recovery_mapping_is_not_persisted(tmp_path, monkeypatch, read_json):
    database = tmp_path / "runtime.db"
    monkeypatch.setenv("SKILL0_RUNTIME_DB_PATH", str(database))
    parsed_dir = tmp_path / "parsed"
    monkeypatch.setenv("SKILL0_PARSED_DIR", str(parsed_dir))
    payload = _create_payload(
        read_json, parsed_dir, "examples/runtime-contract.auto-rollback.json"
    )
    payload["parameters"] = {"customer_id": "42", "secret": "do-not-store"}
    payload["runtime_contract"]["action_bindings"][0]["compensation"][
        "parameters_mapping"
    ] = {"contact_id": "/inputs/secret"}
    created = TestClient(api_module.app).post(
        "/api/runs", json=payload, headers=_auth_headers()
    )
    assert created.status_code == 201
    assert created.json()["status"] == "hitl_required"
    response = TestClient(api_module.app).get(
        f"/api/runs/{created.json()['run_id']}/events", headers=_auth_headers()
    )
    serialized = json.dumps(response.json())
    assert "do-not-store" not in serialized
