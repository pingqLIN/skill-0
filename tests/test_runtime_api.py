from __future__ import annotations

import json
import os
import subprocess
import sys

from fastapi.testclient import TestClient
import pytest

import api.main as api_module
from api.routers.runs_v4 import get_runtime_governance_gate
from runtime.ledger import RuntimeLedger
from runtime.governance import RuntimeGovernanceError
from runtime.models import RuntimeEvent, RuntimeEventType


class ApprovedGovernanceGate:
    def evaluate(self, skill_document, contract):
        return {
            "policy": "governance.current_revision.approved",
            "canonical_skill_id": skill_document["meta"]["skill_id"],
            "governance_skill_id": "governance-runtime-api-test",
            "revision_id": "rev-runtime-api-test",
            "revision_number": 1,
            "artifact_digest": "sha256:" + "c" * 64,
            "approved_by": "reviewer",
            "approved_at": "2026-07-16T00:00:00+00:00",
        }


@pytest.fixture(autouse=True)
def approved_runtime_governance_gate():
    api_module.app.dependency_overrides[get_runtime_governance_gate] = (
        lambda: ApprovedGovernanceGate()
    )
    yield
    api_module.app.dependency_overrides.pop(get_runtime_governance_gate, None)


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


def test_runtime_events_use_payload_allowlist_and_redact_operation_keys(
    tmp_path, monkeypatch
):
    database = tmp_path / "runtime.db"
    with RuntimeLedger(database) as ledger:
        run_id = ledger.create_run(skill_name="demo", skill_version="1")
        ledger.append_event(
            RuntimeEvent(
                run_id=run_id,
                event_type=RuntimeEventType.ACTION_STARTED,
                skill_name="demo",
                skill_version="1",
                action_id="a_001",
                idempotency_key="secret-operation-key",
                payload={
                    "dry_run": True,
                    "reason": "private operator note",
                    "authorization": "Bearer secret-token",
                },
            )
        )
    monkeypatch.setenv("SKILL0_RUNTIME_DB_PATH", str(database))
    response = TestClient(api_module.app).get(
        f"/api/runs/{run_id}/events", headers=_auth_headers()
    )
    assert response.status_code == 200
    serialized = json.dumps(response.json())
    assert "private operator note" not in serialized
    assert "secret-operation-key" not in serialized
    assert "secret-token" not in serialized
    started = response.json()[-1]
    assert started["payload"] == {"dry_run": True}
    assert started["idempotency_key_present"] is True


def test_runtime_run_missing_from_configured_database_returns_404(tmp_path, monkeypatch):
    database = tmp_path / "runtime.db"
    monkeypatch.setenv("SKILL0_RUNTIME_DB_PATH", str(database))

    client = TestClient(api_module.app)
    response = client.get("/api/runs/missing-run", headers=_auth_headers())

    assert response.status_code == 404
    assert response.json()["detail"] == "Run not found"


def test_runtime_evidence_requires_authentication(tmp_path, monkeypatch):
    database = tmp_path / "runtime.db"
    run_id = _create_runtime_run(database)
    monkeypatch.setenv("SKILL0_RUNTIME_DB_PATH", str(database))
    response = TestClient(api_module.app).get(f"/api/runs/{run_id}/evidence")
    assert response.status_code == 401


def test_runtime_evidence_is_deterministic_and_schema_valid(
    tmp_path, monkeypatch, root
):
    database = tmp_path / "runtime.db"
    with RuntimeLedger(database) as ledger:
        run_id = ledger.create_run(skill_name="demo", skill_version="1")
        ledger.append_event(
            RuntimeEvent(
                run_id=run_id,
                event_type=RuntimeEventType.RUN_FAILED,
                skill_name="demo",
                skill_version="1",
                action_id="a_001",
                payload={"reason": "private failure detail"},
            )
        )
    monkeypatch.setenv("SKILL0_RUNTIME_DB_PATH", str(database))
    before = database.read_bytes()
    client = TestClient(api_module.app)
    first = client.get(f"/api/runs/{run_id}/evidence", headers=_auth_headers())
    second = client.get(f"/api/runs/{run_id}/evidence", headers=_auth_headers())
    assert first.status_code == 200
    assert first.json() == second.json()
    assert first.json()["run_ref"] == {"run_id": run_id, "status": "failed"}
    assert first.json()["event_count"] == 2
    assert first.json()["last_event_type"] == "run_failed"
    assert "private failure detail" not in first.text
    assert database.read_bytes() == before
    cli = subprocess.run(
        [
            sys.executable,
            str(root / "scripts" / "runtime_evidence.py"),
            "--db",
            str(database),
            "--run-id",
            run_id,
        ],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(cli.stdout) == first.json()


def test_runtime_evidence_missing_run_returns_404(tmp_path, monkeypatch):
    database = tmp_path / "runtime.db"
    monkeypatch.setenv("SKILL0_RUNTIME_DB_PATH", str(database))
    response = TestClient(api_module.app).get(
        "/api/runs/missing/evidence", headers=_auth_headers()
    )
    assert response.status_code == 404
    assert not database.exists()


def test_runtime_evidence_corrupt_ledger_returns_generic_error(tmp_path, monkeypatch):
    database = tmp_path / "runtime.db"
    database.write_bytes(b"not-a-sqlite-database secret-value")
    monkeypatch.setenv("SKILL0_RUNTIME_DB_PATH", str(database))
    response = TestClient(api_module.app).get(
        "/api/runs/anything/evidence", headers=_auth_headers()
    )
    assert response.status_code == 500
    assert response.json()["detail"] == "Runtime Evidence unavailable"
    assert "secret-value" not in response.text


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


def test_create_runtime_run_rejects_placeholder_or_reused_binding_key(
    tmp_path, monkeypatch, read_json
):
    parsed_dir = tmp_path / "parsed"
    monkeypatch.setenv("SKILL0_RUNTIME_DB_PATH", str(tmp_path / "runtime.db"))
    monkeypatch.setenv("SKILL0_PARSED_DIR", str(parsed_dir))
    payload = _create_payload(read_json, parsed_dir)
    client = TestClient(api_module.app)

    monkeypatch.setenv(
        "SKILL0_RUNTIME_BINDING_KEY",
        "CHANGE_ME_TO_AN_INDEPENDENT_RUNTIME_SECRET",
    )
    placeholder = client.post("/api/runs", json=payload, headers=_auth_headers())
    assert placeholder.status_code == 503

    monkeypatch.setenv(
        "SKILL0_RUNTIME_BINDING_KEY", os.environ["JWT_SECRET_KEY"]
    )
    reused = client.post("/api/runs", json=payload, headers=_auth_headers())
    assert reused.status_code == 503


def test_create_runtime_run_executes_deterministic_simulation(
    tmp_path, monkeypatch, read_json
):
    database = tmp_path / "runtime.db"
    monkeypatch.setenv("SKILL0_RUNTIME_DB_PATH", str(database))
    parsed_dir = tmp_path / "parsed"
    monkeypatch.setenv("SKILL0_PARSED_DIR", str(parsed_dir))
    client = TestClient(api_module.app)
    response = client.post(
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
        basis = ledger.get_execution_basis(body["run_id"])
        assert basis["governance_revision_id"] == "rev-runtime-api-test"
    evidence = client.get(
        f"/api/runs/{body['run_id']}/evidence", headers=_auth_headers()
    )
    assert evidence.status_code == 200
    assert evidence.json()["governance_ref"] == {
        "policy": "governance.current_revision.approved",
        "canonical_skill_id": "claude__skill__runtime_api_fixture",
        "governance_skill_id": "governance-runtime-api-test",
        "revision_id": "rev-runtime-api-test",
        "revision_number": 1,
        "artifact_digest": "sha256:" + "c" * 64,
        "approved_by": "reviewer",
        "approved_at": "2026-07-16T00:00:00+00:00",
    }


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


def test_create_runtime_run_requires_governance_approved_revision(
    tmp_path, monkeypatch, read_json
):
    class DeniedGate:
        def evaluate(self, skill_document, contract):
            del skill_document, contract
            raise RuntimeGovernanceError("GOVERNANCE_REVISION_NOT_APPROVED")

    database = tmp_path / "runtime.db"
    parsed_dir = tmp_path / "parsed"
    monkeypatch.setenv("SKILL0_RUNTIME_DB_PATH", str(database))
    monkeypatch.setenv("SKILL0_PARSED_DIR", str(parsed_dir))
    api_module.app.dependency_overrides[get_runtime_governance_gate] = DeniedGate
    response = TestClient(api_module.app).post(
        "/api/runs",
        json=_create_payload(read_json, parsed_dir),
        headers=_auth_headers(),
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "GOVERNANCE_REVISION_NOT_APPROVED"
    with RuntimeLedger(database) as ledger:
        assert ledger.connection.execute(
            "SELECT COUNT(*) FROM runtime_runs"
        ).fetchone()[0] == 0


def test_hitl_resume_rechecks_governance_before_consuming_claim(
    tmp_path, monkeypatch, read_json
):
    class MutableGate(ApprovedGovernanceGate):
        denied = False

        def evaluate(self, skill_document, contract):
            if self.denied:
                raise RuntimeGovernanceError("GOVERNANCE_REVISION_REVOKED")
            return super().evaluate(skill_document, contract)

    database = tmp_path / "runtime.db"
    parsed_dir = tmp_path / "parsed"
    monkeypatch.setenv("SKILL0_RUNTIME_DB_PATH", str(database))
    monkeypatch.setenv("SKILL0_PARSED_DIR", str(parsed_dir))
    gate = MutableGate()
    api_module.app.dependency_overrides[get_runtime_governance_gate] = lambda: gate
    client = TestClient(api_module.app)
    headers = _auth_headers()
    payload, created = _create_manual_hitl(client, headers, read_json, parsed_dir)
    item_id = created["hitl_item_id"]
    assert client.post(
        f"/api/runs/hitl/items/{item_id}/decision",
        json={"decision": "approve", "reason_code": "REVIEWED"},
        headers=headers,
    ).status_code == 200
    gate.denied = True
    response = client.post(
        f"/api/runs/hitl/items/{item_id}/resume",
        json={
            "runtime_contract": payload["runtime_contract"],
            "parameters": payload["parameters"],
        },
        headers=headers,
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "GOVERNANCE_REVISION_REVOKED"
    with RuntimeLedger(database) as ledger:
        assert ledger.get_run(created["run_id"])["status"] == "ready"
        assert ledger.connection.execute(
            "SELECT COUNT(*) FROM runtime_resume_claims"
        ).fetchone()[0] == 0


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


def _create_manual_hitl(client, headers, read_json, parsed_dir):
    payload = _create_payload(
        read_json, parsed_dir, "examples/runtime-contract.manual-approval.json"
    )
    payload["parameters"] = {"branch": "old"}
    response = client.post("/api/runs", json=payload, headers=headers)
    assert response.status_code == 201
    assert response.json()["status"] == "awaiting_approval"
    assert response.json()["hitl_item_id"]
    return payload, response.json()


def test_hitl_queue_is_publicly_minimized_and_bound_to_run(
    tmp_path, monkeypatch, read_json
):
    database = tmp_path / "runtime.db"
    parsed_dir = tmp_path / "parsed"
    monkeypatch.setenv("SKILL0_RUNTIME_DB_PATH", str(database))
    monkeypatch.setenv("SKILL0_PARSED_DIR", str(parsed_dir))
    client = TestClient(api_module.app)
    headers = _auth_headers()
    payload, created = _create_manual_hitl(client, headers, read_json, parsed_dir)

    response = client.get(
        f"/api/runs/hitl/items?run_id={created['run_id']}", headers=headers
    )
    assert response.status_code == 200
    assert len(response.json()) == 1
    item = response.json()[0]
    assert item["item_id"] == created["hitl_item_id"]
    assert item["action_id"] == "a_010"
    assert item["status"] == "pending"
    assert "basis_digest" not in item
    serialized = json.dumps(item)
    assert payload["parameters"]["branch"] not in serialized
    assert "hmac-sha256" not in serialized


def test_hitl_decision_uses_jwt_actor_and_does_not_execute_action(
    tmp_path, monkeypatch, read_json
):
    database = tmp_path / "runtime.db"
    parsed_dir = tmp_path / "parsed"
    monkeypatch.setenv("SKILL0_RUNTIME_DB_PATH", str(database))
    monkeypatch.setenv("SKILL0_PARSED_DIR", str(parsed_dir))
    client = TestClient(api_module.app)
    reviewer_headers = {
        "Authorization": f"Bearer {api_module.create_access_token({'sub': 'reviewer-1'})}"
    }
    _, created = _create_manual_hitl(
        client, reviewer_headers, read_json, parsed_dir
    )

    rejected_shape = client.post(
        f"/api/runs/hitl/items/{created['hitl_item_id']}/decision",
        json={"decision": "approve", "reason_code": "REVIEWED", "actor": "forged"},
        headers=reviewer_headers,
    )
    assert rejected_shape.status_code == 422

    response = client.post(
        f"/api/runs/hitl/items/{created['hitl_item_id']}/decision",
        json={"decision": "approve", "reason_code": "REVIEWED"},
        headers=reviewer_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "approved"

    with RuntimeLedger(database) as ledger:
        decisions = ledger.list_hitl_decisions(created["hitl_item_id"])
        assert decisions[0]["actor"] == "reviewer-1"
        assert ledger.count_events(
            created["run_id"], RuntimeEventType.ACTION_STARTED
        ) == 0
        assert ledger.get_run(created["run_id"])["status"] == "ready"


def test_hitl_decision_authorization_fails_closed(
    tmp_path, monkeypatch, read_json
):
    database = tmp_path / "runtime.db"
    parsed_dir = tmp_path / "parsed"
    monkeypatch.setenv("SKILL0_RUNTIME_DB_PATH", str(database))
    monkeypatch.setenv("SKILL0_PARSED_DIR", str(parsed_dir))
    client = TestClient(api_module.app)
    headers = _auth_headers()
    _, created = _create_manual_hitl(client, headers, read_json, parsed_dir)
    endpoint = f"/api/runs/hitl/items/{created['hitl_item_id']}/decision"
    unauthorized_headers = {
        "Authorization": f"Bearer {api_module.create_access_token({'sub': 'intruder'})}"
    }
    forbidden = client.post(
        endpoint,
        json={"decision": "approve", "reason_code": "REVIEWED"},
        headers=unauthorized_headers,
    )
    assert forbidden.status_code == 403

    monkeypatch.delenv("SKILL0_RUNTIME_DECISION_ACTORS")
    unconfigured = client.post(
        endpoint,
        json={"decision": "approve", "reason_code": "REVIEWED"},
        headers=headers,
    )
    assert unconfigured.status_code == 503
    with RuntimeLedger(database) as ledger:
        assert ledger.get_hitl_item(created["hitl_item_id"])["status"] == "pending"
        assert ledger.list_hitl_decisions(created["hitl_item_id"]) == []


def test_approved_hitl_item_resumes_same_run_once(
    tmp_path, monkeypatch, read_json
):
    database = tmp_path / "runtime.db"
    parsed_dir = tmp_path / "parsed"
    monkeypatch.setenv("SKILL0_RUNTIME_DB_PATH", str(database))
    monkeypatch.setenv("SKILL0_PARSED_DIR", str(parsed_dir))
    client = TestClient(api_module.app)
    headers = _auth_headers()
    payload, created = _create_manual_hitl(client, headers, read_json, parsed_dir)
    item_id = created["hitl_item_id"]
    decision = client.post(
        f"/api/runs/hitl/items/{item_id}/decision",
        json={"decision": "approve", "reason_code": "CHANGE_REVIEWED"},
        headers=headers,
    )
    assert decision.status_code == 200

    resumed = client.post(
        f"/api/runs/hitl/items/{item_id}/resume",
        json={
            "runtime_contract": payload["runtime_contract"],
            "parameters": payload["parameters"],
        },
        headers=headers,
    )
    assert resumed.status_code == 200
    assert resumed.json()["run_id"] == created["run_id"]
    assert resumed.json()["status"] == "succeeded"
    assert resumed.json()["hitl_item_id"] is None

    replay = client.post(
        f"/api/runs/hitl/items/{item_id}/resume",
        json={
            "runtime_contract": payload["runtime_contract"],
            "parameters": payload["parameters"],
        },
        headers=headers,
    )
    assert replay.status_code == 409


def test_hitl_resume_rejects_changed_inputs_or_contract(
    tmp_path, monkeypatch, read_json
):
    database = tmp_path / "runtime.db"
    parsed_dir = tmp_path / "parsed"
    monkeypatch.setenv("SKILL0_RUNTIME_DB_PATH", str(database))
    monkeypatch.setenv("SKILL0_PARSED_DIR", str(parsed_dir))
    client = TestClient(api_module.app)
    headers = _auth_headers()
    payload, created = _create_manual_hitl(client, headers, read_json, parsed_dir)
    item_id = created["hitl_item_id"]
    assert client.post(
        f"/api/runs/hitl/items/{item_id}/decision",
        json={"decision": "approve", "reason_code": "REVIEWED"},
        headers=headers,
    ).status_code == 200

    changed_inputs = client.post(
        f"/api/runs/hitl/items/{item_id}/resume",
        json={
            "runtime_contract": payload["runtime_contract"],
            "parameters": {"branch": "different"},
        },
        headers=headers,
    )
    assert changed_inputs.status_code == 409
    assert "basis" in changed_inputs.json()["detail"]

    changed_contract = json.loads(json.dumps(payload["runtime_contract"]))
    changed_contract["directive_manifest"]["token_budget"] += 1
    contract_response = client.post(
        f"/api/runs/hitl/items/{item_id}/resume",
        json={
            "runtime_contract": changed_contract,
            "parameters": payload["parameters"],
        },
        headers=headers,
    )
    assert contract_response.status_code == 409

    skill_path = parsed_dir / "runtime-api-skill.json"
    changed_skill = json.loads(skill_path.read_text(encoding="utf-8"))
    changed_skill["meta"]["description"] = "changed after approval"
    skill_path.write_text(json.dumps(changed_skill), encoding="utf-8")
    skill_response = client.post(
        f"/api/runs/hitl/items/{item_id}/resume",
        json={
            "runtime_contract": payload["runtime_contract"],
            "parameters": payload["parameters"],
        },
        headers=headers,
    )
    assert skill_response.status_code == 409
    with RuntimeLedger(database) as ledger:
        assert ledger.get_run(created["run_id"])["status"] == "ready"
        assert ledger.count_events(
            created["run_id"], RuntimeEventType.ACTION_STARTED
        ) == 0


def test_hitl_resume_rejects_binding_key_rotation_without_consuming_claim(
    tmp_path, monkeypatch, read_json
):
    database = tmp_path / "runtime.db"
    parsed_dir = tmp_path / "parsed"
    monkeypatch.setenv("SKILL0_RUNTIME_DB_PATH", str(database))
    monkeypatch.setenv("SKILL0_PARSED_DIR", str(parsed_dir))
    original_key = "skill0-test-runtime-binding-key-0123456789"
    monkeypatch.setenv("SKILL0_RUNTIME_BINDING_KEY", original_key)
    client = TestClient(api_module.app)
    headers = _auth_headers()
    payload, created = _create_manual_hitl(client, headers, read_json, parsed_dir)
    item_id = created["hitl_item_id"]
    assert client.post(
        f"/api/runs/hitl/items/{item_id}/decision",
        json={"decision": "approve", "reason_code": "REVIEWED"},
        headers=headers,
    ).status_code == 200

    monkeypatch.setenv(
        "SKILL0_RUNTIME_BINDING_KEY",
        "rotated-test-runtime-binding-key-9876543210",
    )
    rotated = client.post(
        f"/api/runs/hitl/items/{item_id}/resume",
        json={
            "runtime_contract": payload["runtime_contract"],
            "parameters": payload["parameters"],
        },
        headers=headers,
    )
    assert rotated.status_code == 409

    monkeypatch.setenv("SKILL0_RUNTIME_BINDING_KEY", original_key)
    resumed = client.post(
        f"/api/runs/hitl/items/{item_id}/resume",
        json={
            "runtime_contract": payload["runtime_contract"],
            "parameters": payload["parameters"],
        },
        headers=headers,
    )
    assert resumed.status_code == 200
    assert resumed.json()["status"] == "succeeded"


def test_hitl_rejection_is_final_and_decision_replay_conflicts(
    tmp_path, monkeypatch, read_json
):
    database = tmp_path / "runtime.db"
    parsed_dir = tmp_path / "parsed"
    monkeypatch.setenv("SKILL0_RUNTIME_DB_PATH", str(database))
    monkeypatch.setenv("SKILL0_PARSED_DIR", str(parsed_dir))
    client = TestClient(api_module.app)
    headers = _auth_headers()
    payload, created = _create_manual_hitl(client, headers, read_json, parsed_dir)
    item_id = created["hitl_item_id"]
    endpoint = f"/api/runs/hitl/items/{item_id}/decision"
    first = client.post(
        endpoint,
        json={"decision": "reject", "reason_code": "RISK_NOT_ACCEPTED"},
        headers=headers,
    )
    second = client.post(
        endpoint,
        json={"decision": "approve", "reason_code": "REVIEWED"},
        headers=headers,
    )
    assert first.status_code == 200
    assert first.json()["status"] == "rejected"
    assert second.status_code == 409
    resume = client.post(
        f"/api/runs/hitl/items/{item_id}/resume",
        json={
            "runtime_contract": payload["runtime_contract"],
            "parameters": payload["parameters"],
        },
        headers=headers,
    )
    assert resume.status_code == 409
    with RuntimeLedger(database) as ledger:
        assert ledger.get_run(created["run_id"])["status"] == "denied"
        assert len(ledger.list_hitl_decisions(item_id)) == 1


def test_manual_recovery_requires_confirmation_and_auto_recovery_executes(
    tmp_path, monkeypatch, read_json
):
    database = tmp_path / "runtime.db"
    parsed_dir = tmp_path / "parsed"
    monkeypatch.setenv("SKILL0_RUNTIME_DB_PATH", str(database))
    monkeypatch.setenv("SKILL0_PARSED_DIR", str(parsed_dir))
    client = TestClient(api_module.app)
    headers = _auth_headers()
    payload, created = _create_manual_hitl(client, headers, read_json, parsed_dir)
    item_id = created["hitl_item_id"]
    assert client.post(
        f"/api/runs/hitl/items/{item_id}/decision",
        json={"decision": "approve", "reason_code": "REVIEWED"},
        headers=headers,
    ).status_code == 200
    assert client.post(
        f"/api/runs/hitl/items/{item_id}/resume",
        json={
            "runtime_contract": payload["runtime_contract"],
            "parameters": payload["parameters"],
        },
        headers=headers,
    ).json()["status"] == "succeeded"

    recovery = client.post(
        f"/api/runs/{created['run_id']}/recover", json={}, headers=headers
    )
    assert recovery.status_code == 200
    assert recovery.json()["status"] == "hitl_required"
    recovery_item = recovery.json()["hitl_item_id"]
    assert recovery_item
    invalid = client.post(
        f"/api/runs/hitl/items/{recovery_item}/decision",
        json={"decision": "approve", "reason_code": "REVIEWED"},
        headers=headers,
    )
    assert invalid.status_code == 409
    confirmed = client.post(
        f"/api/runs/hitl/items/{recovery_item}/decision",
        json={"decision": "confirm_recovered", "reason_code": "RECOVERY_VERIFIED"},
        headers=headers,
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "confirmed"
    with RuntimeLedger(database) as ledger:
        assert ledger.get_run(created["run_id"])["status"] == "recovery_pending"
    finalized = client.post(
        f"/api/runs/{created['run_id']}/recover", json={}, headers=headers
    )
    assert finalized.status_code == 200
    assert finalized.json()["status"] == "compensated"

    auto_payload = _create_payload(
        read_json, parsed_dir, "examples/runtime-contract.auto-rollback.json"
    )
    auto_payload["parameters"] = {"customer_id": "42"}
    auto_created = client.post("/api/runs", json=auto_payload, headers=headers)
    assert auto_created.status_code == 201
    auto_recovery = client.post(
        f"/api/runs/{auto_created.json()['run_id']}/recover",
        json={},
        headers=headers,
    )
    assert auto_recovery.status_code == 200
    assert auto_recovery.json() == {
        "run_id": auto_created.json()["run_id"],
        "status": "compensated",
        "hitl_item_id": None,
    }
