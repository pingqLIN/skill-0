import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft7Validator

from tools.curation_contract import (
    CONTRACT_SCHEMA_PATHS,
    find_sensitive_content,
    load_contract_schema,
    normalize_contract_document,
    validate_contract_document,
    validate_evaluation_semantics,
    validate_proposal_base_revision,
    validate_proposal_semantics,
    validate_temporal_holdout,
    validate_trajectory_semantics,
)

FIXTURE_ROOT = Path("tests/fixtures/curation_contracts")
VALID_FIXTURES = {
    "trajectory": FIXTURE_ROOT / "valid" / "execution-trajectory.json",
    "proposal": FIXTURE_ROOT / "valid" / "curation-proposal.json",
    "evaluation": FIXTURE_ROOT / "valid" / "evaluation-result.json",
}


def load_fixture(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("contract_type", sorted(CONTRACT_SCHEMA_PATHS))
def test_curation_schemas_are_valid_draft7(contract_type):
    Draft7Validator.check_schema(load_contract_schema(contract_type))


@pytest.mark.parametrize("contract_type", sorted(VALID_FIXTURES))
def test_valid_contract_fixtures_pass_schema_and_semantics(contract_type):
    document = load_fixture(VALID_FIXTURES[contract_type])
    assert validate_contract_document(document, contract_type) == []


def test_normalization_adds_only_safe_structural_defaults_without_mutating_input():
    original = {
        "trajectory_id": "traj_normalize_001",
        "task": {
            "task_id": "task_normalize_001",
            "family": "normalization",
        },
        "redaction": {
            "status": "redacted",
        },
    }
    snapshot = copy.deepcopy(original)

    normalized = normalize_contract_document(original, "trajectory")

    assert original == snapshot
    assert normalized["contract_version"] == "1.0.0"
    assert normalized["task"]["attributes"] == []
    assert normalized["redaction"]["removed_fields"] == []
    assert normalized["steps"] == []
    assert normalized["retrieved_skills"] == []


def test_unknown_contract_type_is_rejected():
    with pytest.raises(ValueError, match="Unknown curation contract type"):
        load_contract_schema("runtime")


def test_normalization_leaves_wrong_typed_fields_for_schema_validation():
    original = {"task": "invalid", "redaction": "invalid"}

    normalized = normalize_contract_document(original, "trajectory")

    assert normalized["task"] == "invalid"
    assert normalized["redaction"] == "invalid"
    assert validate_contract_document(normalized, "trajectory")


def test_missing_update_candidate_fails_schema_validation():
    document = load_fixture(
        FIXTURE_ROOT / "invalid" / "curation-proposal-missing-candidate.json"
    )

    issues = validate_contract_document(document, "proposal")

    assert any("candidate" in issue for issue in issues)


def test_sensitive_trajectory_fixture_is_rejected_without_echoing_value():
    document = load_fixture(
        FIXTURE_ROOT / "invalid" / "execution-trajectory-sensitive.json"
    )

    issues = validate_trajectory_semantics(document)

    assert any("bearer token" in issue for issue in issues)
    assert all("TESTONLYTOKEN" not in issue for issue in issues)


def test_generic_security_wording_does_not_trigger_secret_detection():
    document = {
        "summary": "Remove secrets, passwords, and tokens before trajectory ingestion."
    }

    assert find_sensitive_content(document) == []


def test_sensitive_field_name_is_rejected_even_for_unrecognized_value_shape():
    findings = find_sensitive_content({"metadata": {"api_key": "fixture-value"}})

    assert [(finding.path, finding.reason) for finding in findings] == [
        ("/metadata/api_key", "sensitive field name")
    ]


def test_trajectory_steps_and_ranks_must_be_contiguous():
    document = load_fixture(VALID_FIXTURES["trajectory"])
    document["steps"][1]["index"] = 3
    document["retrieved_skills"][0]["rank"] = 2

    issues = validate_trajectory_semantics(document)

    assert "steps must be contiguous and ordered from 1" in issues
    assert "retrieved skill ranks must be contiguous and ordered from 1" in issues


def test_trajectory_steps_must_fall_within_run_window():
    document = load_fixture(VALID_FIXTURES["trajectory"])
    document["steps"][0]["timestamp"] = "2026-07-14T23:59:00Z"

    issues = validate_trajectory_semantics(document)

    assert "step timestamps must fall within the run time window" in issues


def test_stale_base_revision_fixture_is_rejected():
    proposal = load_fixture(
        FIXTURE_ROOT / "invalid" / "curation-proposal-stale-base.json"
    )

    issues = validate_proposal_base_revision(
        proposal,
        current_revision_id="rev_alpha_002",
        current_revision_checksum="6" * 64,
    )

    assert issues == [
        "proposal base_revision_id does not match the current revision",
        "proposal base_revision_checksum does not match the current revision",
    ]


def test_current_base_revision_passes_optimistic_concurrency_check():
    proposal = load_fixture(VALID_FIXTURES["proposal"])

    issues = validate_proposal_base_revision(
        proposal,
        current_revision_id="rev_alpha_001",
        current_revision_checksum="c" * 64,
    )

    assert issues == []


def test_approved_proposal_requires_every_validation_to_pass():
    proposal = load_fixture(VALID_FIXTURES["proposal"])
    proposal["governance"] = {
        "state": "approved",
        "decision": {
            "actor": "reviewer",
            "decided_at": "2026-07-15T00:20:00Z",
            "reason": "Fixture approval.",
            "resulting_revision_id": "rev_alpha_002",
        },
    }
    proposal["validations"]["conflict"]["status"] = "warn"

    issues = validate_proposal_semantics(proposal)

    assert issues == ["approved proposals require pass status for: conflict"]


def test_update_proposal_rejects_noop_candidate_checksum():
    proposal = load_fixture(VALID_FIXTURES["proposal"])
    proposal["candidate"]["artifact_checksum"] = proposal["target"]["base_revision_checksum"]

    issues = validate_proposal_semantics(proposal)

    assert "update candidate checksum must differ from the base revision" in issues


def test_valid_temporal_holdout_has_no_cross_document_issues():
    proposal = load_fixture(VALID_FIXTURES["proposal"])
    evaluation = load_fixture(VALID_FIXTURES["evaluation"])

    assert validate_temporal_holdout(proposal, evaluation) == []


def test_temporal_leakage_fixture_is_rejected():
    proposal = load_fixture(VALID_FIXTURES["proposal"])
    evaluation = load_fixture(
        FIXTURE_ROOT / "invalid" / "evaluation-result-temporal-leakage.json"
    )

    internal_issues = validate_evaluation_semantics(evaluation)
    cross_issues = validate_temporal_holdout(proposal, evaluation)

    assert "first evaluation task must occur after the curator cutoff" in internal_issues
    assert "evaluation reuses curator-observed task IDs: task_alpha_001" in cross_issues
    assert "temporal holdout begins before or at the curator cutoff" in cross_issues


def test_evaluation_metric_counts_match_holdout_tasks():
    evaluation = load_fixture(VALID_FIXTURES["evaluation"])
    evaluation["metrics"]["candidate"]["task_count"] = 1

    issues = validate_evaluation_semantics(evaluation)

    assert "metrics.candidate.task_count must equal the holdout task count" in issues


def test_evaluation_rejects_identical_snapshot_content_and_incorrect_delta():
    evaluation = load_fixture(VALID_FIXTURES["evaluation"])
    evaluation["snapshots"]["candidate"]["checksum"] = evaluation["snapshots"]["baseline"]["checksum"]
    evaluation["metrics"]["delta"]["success_rate"] = 0.25

    issues = validate_evaluation_semantics(evaluation)

    assert "baseline and candidate snapshot checksums must be distinct" in issues
    assert "metrics.delta.success_rate must equal candidate minus baseline" in issues
