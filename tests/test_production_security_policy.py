import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "docs" / "contracts" / "production-security-policy-v1.json"


def _policy():
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def test_production_security_policy_freezes_supported_boundary():
    policy = _policy()

    assert policy["policy_version"] == "1.4.0"
    assert policy["status"] == "stable-foundation"
    assert policy["deployment_boundary"] == {
        "topology": "single-host-docker-compose",
        "runtime_mode": "dry-run-only",
        "supported_asset_types": ["skill"],
        "physical_stores": ["skills.db", "governance.db", "runtime.db"],
    }
    assert policy["failed_or_unknown_gate_blocks_release"] is True


def test_production_security_policy_keeps_derived_surfaces_non_authoritative():
    assert _policy()["authority"] == {
        "search_is_authority": False,
        "knowledge_is_authority": False,
        "evaluation_is_authority": False,
        "dashboard_is_authority": False,
        "skills_status_is_authority": False,
        "runtime_hitl_grants_governance_authority": False,
    }


def test_production_security_policy_locks_prohibited_scope():
    assert _policy()["prohibited"] == {
        "real_adapter_execution": True,
        "non_dry_run": True,
        "fts5_production_integration": True,
        "dashboard_redesign_dependency": True,
        "new_asset_type": True,
        "physical_database_migration": True,
        "wildcard_or_localhost_cors": True,
        "direct_untrusted_http_exposure": True,
        "credential_persistence_in_repository_or_image": True,
        "runtime_initialization_during_normal_operation": True,
        "writable_governance_mount_in_core_api": True,
    }


def test_production_security_policy_separates_verified_and_external_controls():
    policy = _policy()

    assert "production-config-fail-closed" in policy["verified_application_controls"]
    assert "dry-run-literal-request-contract" in policy["verified_application_controls"]
    assert "tls-termination" in policy["required_external_controls"]
    assert "secret-manager" in policy["required_external_controls"]
    assert "tls-inside-compose" in policy["known_unenforced_controls"]
    assert "fresh-evidence-reapproval" in policy["known_unenforced_controls"]
    assert "governance-decision-current-target-enforcement" in policy[
        "verified_application_controls"
    ]
    assert "governance-decision-current-target-enforcement" not in policy[
        "known_unenforced_controls"
    ]
    assert (
        "runtime-initialization-disabled-production-startup"
        in policy["verified_application_controls"]
    )
    assert "authenticated-redacted-health-detail" in policy[
        "verified_application_controls"
    ]
    assert "embedding-model-remote-fallback-disabled" in policy[
        "verified_application_controls"
    ]
    assert "approved-local-model-artifact-digest" in policy[
        "verified_application_controls"
    ]
    assert "approved-local-model-artifact-digest" not in policy[
        "known_unenforced_controls"
    ]
    assert set(policy["verified_application_controls"]).isdisjoint(
        policy["known_unenforced_controls"]
    )


def test_production_security_policy_matches_runtime_and_compose_guards():
    runtime_api = (ROOT / "api" / "routers" / "runs_v4.py").read_text(encoding="utf-8")
    compose = (ROOT / "docker-compose.prod.yml").read_text(encoding="utf-8")

    assert "dry_run: Literal[True] = True" in runtime_api
    assert "Batch A accepts only test adapters" in runtime_api
    assert "simulation adapter refuses real execution" in runtime_api
    assert "skill0-governance-db:/app/governance/db:ro" in compose
    assert 'SKILL0_ENABLE_DOCS: "false"' in compose
    assert "SKILL0_RUNTIME_ALLOW_INITIALIZE: ${SKILL0_RUNTIME_ALLOW_INITIALIZE:-false}" in compose
    assert "SKILL0_EMBEDDING_MODEL_ARTIFACT_DIGEST:" in compose
    assert "model-cache:/app/.cache:ro" in compose


def test_public_security_entrypoints_link_authoritative_policy_and_companion():
    security = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
    companion = (ROOT / "SECURITY.zh-tw.md").read_text(encoding="utf-8")

    assert "docs/production-security-policy.md" in security
    assert "SECURITY.zh-tw.md" in security
    assert "SECURITY.md" in companion


def test_ci_remote_actions_pin_full_commit_shas():
    workflow_dir = ROOT / ".github" / "workflows"
    action_pattern = re.compile(r"^\s*-?\s*uses:\s+([^\s#]+)", re.MULTILINE)

    for workflow_path in workflow_dir.glob("*.yml"):
        workflow = workflow_path.read_text(encoding="utf-8")
        remote_actions = [
            action
            for action in action_pattern.findall(workflow)
            if not action.startswith(("./", "docker://"))
        ]

        assert remote_actions
        for action in remote_actions:
            assert re.fullmatch(r"[^@\s]+@[0-9a-f]{40}", action), (
                f"{workflow_path.name} has an unpinned action: {action}"
            )
