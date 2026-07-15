import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from curation.offline_curator import (
    DEFAULT_MANIFEST_PATH,
    CuratorBoundaryError,
    build_draft_proposal,
    build_prompt_package,
    canonical_json_bytes,
    load_curator_resources,
    load_json_object,
    sha256_bytes,
    validate_prompt_package,
    write_dry_json_artifact,
)
from tools.curation_contract import validate_contract_document
from tools.offline_curator import main

CONTRACT_FIXTURES = Path("tests/fixtures/curation_contracts")
CURATOR_FIXTURES = Path("tests/fixtures/offline_curator")
TRAJECTORY_PATH = CONTRACT_FIXTURES / "valid" / "execution-trajectory.json"
SENSITIVE_TRAJECTORY_PATH = (
    CONTRACT_FIXTURES / "invalid" / "execution-trajectory-sensitive.json"
)
CONTEXT_PATH = CURATOR_FIXTURES / "skill-context.json"
CANDIDATE_PATH = CURATOR_FIXTURES / "candidate-skill.md"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_package() -> dict:
    return build_prompt_package(
        load(TRAJECTORY_PATH),
        load(CONTEXT_PATH),
        model_id="fixture-offline-model",
    )


def build_update_decision(package: dict) -> dict:
    return {
        "contract_version": "1.0.0",
        "prompt_package_checksum": package["package_checksum"],
        "operation": "update",
        "target_skill_id": "claude__skill__sample_skill",
        "proposed_skill_id": "claude__skill__sample_skill",
        "rationale_summary": "Clarify stale-revision validation using the observed task.",
        "confidence": 0.82,
    }


def test_static_resources_and_prompt_package_are_deterministic():
    resources = load_curator_resources(DEFAULT_MANIFEST_PATH)

    first = build_package()
    second = build_package()

    assert first == second
    assert first["manifest"]["manifest_checksum"] == resources.manifest_checksum
    assert first["manifest"]["prompt_template_checksum"] == resources.prompt_checksum
    assert validate_prompt_package(first) == []


def test_update_decision_builds_valid_dry_draft_proposal():
    package = build_package()
    proposal = build_draft_proposal(
        package,
        build_update_decision(package),
        load(CONTEXT_PATH),
        candidate_artifact=CANDIDATE_PATH.read_bytes(),
    )

    assert validate_contract_document(proposal, "proposal") == []
    assert proposal["governance"] == {"state": "draft"}
    assert proposal["target"]["base_revision_id"] == "rev_alpha_001"
    assert proposal["candidate"]["proposed_skill_id"] == proposal["target"]["skill_id"]
    assert proposal["candidate"]["artifact_ref"].startswith("proposal://")
    assert proposal["validations"]["schema"]["status"] == "pass"
    assert proposal["validations"]["ard"]["status"] == "not_run"


def test_insert_decision_builds_draft_without_existing_skill():
    trajectory = load(TRAJECTORY_PATH)
    trajectory["retrieved_skills"] = []
    context = {
        "contract_version": "1.0.0",
        "snapshot_id": "curctx_empty_001",
        "captured_at": "2026-07-15T00:08:00Z",
        "skills": [],
    }
    package = build_prompt_package(
        trajectory,
        context,
        model_id="fixture-offline-model",
    )
    decision = {
        "contract_version": "1.0.0",
        "prompt_package_checksum": package["package_checksum"],
        "operation": "insert",
        "proposed_skill_id": "claude__skill__new_skill",
        "rationale_summary": "No retrieved skill covered the observed task.",
        "confidence": 0.7,
    }

    proposal = build_draft_proposal(
        package,
        decision,
        context,
        candidate_artifact=CANDIDATE_PATH.read_bytes(),
    )

    assert proposal["operation"] == "insert"
    assert "target" not in proposal
    assert proposal["candidate"]["proposed_skill_id"] == "claude__skill__new_skill"
    assert proposal["governance"]["state"] == "draft"


def test_delete_decision_builds_draft_without_candidate():
    package = build_package()
    decision = {
        "contract_version": "1.0.0",
        "prompt_package_checksum": package["package_checksum"],
        "operation": "delete",
        "target_skill_id": "claude__skill__sample_skill",
        "rationale_summary": "Fixture evidence recommends retirement for human review.",
        "confidence": 0.6,
    }

    proposal = build_draft_proposal(package, decision, load(CONTEXT_PATH))

    assert proposal["operation"] == "delete"
    assert proposal["target"]["skill_id"] == "claude__skill__sample_skill"
    assert "candidate" not in proposal
    assert proposal["governance"]["state"] == "draft"


def test_prompt_preparation_rejects_sensitive_trajectory_without_echoing_value():
    with pytest.raises(CuratorBoundaryError) as exc_info:
        build_prompt_package(
            load(SENSITIVE_TRAJECTORY_PATH),
            {
                "contract_version": "1.0.0",
                "snapshot_id": "curctx_sensitive_001",
                "captured_at": "2026-07-15T00:04:00Z",
                "skills": [],
            },
            model_id="fixture-offline-model",
        )

    assert "bearer token" in str(exc_info.value)
    assert "TESTONLYTOKEN" not in str(exc_info.value)


def test_prompt_preparation_rejects_misaligned_retrieval_context():
    context = load(CONTEXT_PATH)
    context["skills"][0]["revision_id"] = "rev_alpha_002"

    with pytest.raises(CuratorBoundaryError, match="exactly match"):
        build_prompt_package(
            load(TRAJECTORY_PATH),
            context,
            model_id="fixture-offline-model",
        )


def test_proposal_rejects_unbound_decision():
    package = build_package()
    decision = build_update_decision(package)
    decision["prompt_package_checksum"] = "f" * 64

    with pytest.raises(CuratorBoundaryError, match="not bound"):
        build_draft_proposal(
            package,
            decision,
            load(CONTEXT_PATH),
            candidate_artifact=CANDIDATE_PATH.read_bytes(),
        )


def test_proposal_rejects_stale_current_revision():
    package = build_package()
    current_context = load(CONTEXT_PATH)
    current_context["snapshot_id"] = "curctx_alpha_002"
    current_context["captured_at"] = "2026-07-15T00:09:00Z"
    current_context["skills"][0]["revision_id"] = "rev_alpha_002"
    current_context["skills"][0]["revision_checksum"] = "d" * 64

    with pytest.raises(CuratorBoundaryError, match="changed after prompt preparation"):
        build_draft_proposal(
            package,
            build_update_decision(package),
            current_context,
            candidate_artifact=CANDIDATE_PATH.read_bytes(),
        )


def test_proposal_rejects_current_context_older_than_prompt_context():
    package = build_package()
    current_context = load(CONTEXT_PATH)
    current_context["captured_at"] = "2026-07-15T00:07:00Z"

    with pytest.raises(CuratorBoundaryError, match="older than"):
        build_draft_proposal(
            package,
            build_update_decision(package),
            current_context,
            candidate_artifact=CANDIDATE_PATH.read_bytes(),
        )


def test_proposal_rejects_created_at_before_validated_inputs():
    package = build_package()

    with pytest.raises(CuratorBoundaryError, match="created_at precedes"):
        build_draft_proposal(
            package,
            build_update_decision(package),
            load(CONTEXT_PATH),
            candidate_artifact=CANDIDATE_PATH.read_bytes(),
            created_at="2026-07-15T00:05:00Z",
        )


def test_proposal_rejects_sensitive_candidate_artifact():
    package = build_package()
    candidate = (
        "Authorization: Bearer " + "TESTONLYTOKEN" + "12345678901234567890"
    ).encode("utf-8")

    with pytest.raises(CuratorBoundaryError) as exc_info:
        build_draft_proposal(
            package,
            build_update_decision(package),
            load(CONTEXT_PATH),
            candidate_artifact=candidate,
        )

    assert "bearer token" in str(exc_info.value)
    assert "TESTONLYTOKEN" not in str(exc_info.value)


def test_delete_rejects_candidate_artifact():
    package = build_package()
    decision = {
        "contract_version": "1.0.0",
        "prompt_package_checksum": package["package_checksum"],
        "operation": "delete",
        "target_skill_id": "claude__skill__sample_skill",
        "rationale_summary": "Fixture-only deletion recommendation.",
        "confidence": 0.6,
    }

    with pytest.raises(CuratorBoundaryError, match="must not provide"):
        build_draft_proposal(
            package,
            decision,
            load(CONTEXT_PATH),
            candidate_artifact=CANDIDATE_PATH.read_bytes(),
        )


def test_repo_local_output_is_restricted_to_dry_output_root():
    protected_path = Path("schema/offline-curator-should-not-write.json")

    with pytest.raises(CuratorBoundaryError, match="only under output/curation"):
        write_dry_json_artifact({"dry": True}, protected_path)

    assert not protected_path.exists()


def test_cli_prepare_and_propose_round_trip(tmp_path, capsys):
    prompt_path = tmp_path / "prompt-package.json"
    decision_path = tmp_path / "decision.json"
    proposal_path = tmp_path / "proposal.json"

    assert main(
        [
            "prepare",
            "--trajectory",
            str(TRAJECTORY_PATH),
            "--skill-context",
            str(CONTEXT_PATH),
            "--model-id",
            "fixture-offline-model",
            "--output",
            str(prompt_path),
        ]
    ) == 0
    package = load_json_object(prompt_path)
    decision_path.write_text(
        json.dumps(build_update_decision(package), indent=2) + "\n",
        encoding="utf-8",
    )

    assert main(
        [
            "propose",
            "--prompt-package",
            str(prompt_path),
            "--decision",
            str(decision_path),
            "--current-context",
            str(CONTEXT_PATH),
            "--candidate-artifact",
            str(CANDIDATE_PATH),
            "--output",
            str(proposal_path),
        ]
    ) == 0

    proposal = load_json_object(proposal_path)
    assert proposal["governance"]["state"] == "draft"
    assert validate_contract_document(proposal, "proposal") == []
    assert "Dry Curator artifact written" in capsys.readouterr().out


def test_cli_script_entrypoint_loads_repo_package():
    result = subprocess.run(
        [sys.executable, "tools/offline_curator.py", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Prepare offline Curator prompts" in result.stdout


def test_prompt_package_tampering_is_rejected():
    package = build_package()
    package["trajectory"]["task"]["family"] = "tampered-family"

    assert "prompt package checksum is invalid" in validate_prompt_package(package)


def test_prompt_package_rejects_rechecksummed_extra_sensitive_fields():
    package = build_package()
    package.pop("package_checksum")
    package["api" + "_key"] = "fixture-sensitive-field"
    package["package_checksum"] = sha256_bytes(canonical_json_bytes(package))

    issues = validate_prompt_package(package)

    assert "prompt package has unexpected or missing top-level fields" in issues
    assert any("sensitive field name" in issue for issue in issues)


def test_build_draft_does_not_mutate_inputs():
    package = build_package()
    decision = build_update_decision(package)
    context = load(CONTEXT_PATH)
    snapshots = (copy.deepcopy(package), copy.deepcopy(decision), copy.deepcopy(context))

    build_draft_proposal(
        package,
        decision,
        context,
        candidate_artifact=CANDIDATE_PATH.read_bytes(),
    )

    assert (package, decision, context) == snapshots
