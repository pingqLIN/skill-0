"""Tests for the top-down Skill-0 intent router."""

from tools import intent_router


def test_infer_goal_prefers_discovery_language():
    assert (
        intent_router.infer_goal("搜尋相似 skill 並做 inventory dedup")
        == "discover"
    )


def test_infer_goal_detects_governance_language():
    assert (
        intent_router.infer_goal("需要治理審核與 audit risk review")
        == "govern"
    )


def test_build_route_for_compare_uses_similarity_commands():
    decision = intent_router.build_route(
        goal="compare",
        phase="triage",
        query="agent skills overlap",
        skill_name="agent-skills",
    )

    assert decision.primary_capability == "similarity-and-overlap-analysis"
    assert any("similar" in command for command in decision.recommended_commands)
    assert any("pattern_extractor.py" in command for command in decision.recommended_commands)


def test_compare_route_without_skill_name_avoids_placeholder_command():
    decision = intent_router.build_route(
        goal="compare",
        phase="triage",
        query="agent skills overlap",
    )

    assert all("<skill-name>" not in command for command in decision.recommended_commands)
    assert any("search" in command for command in decision.recommended_commands)


def test_discover_intake_phase_bootstraps_indexing():
    decision = intent_router.build_route(
        goal="discover",
        phase="intake",
        query="document processing",
    )

    assert decision.recommended_commands[0].endswith("--parsed-dir parsed index")
    assert any("search \"document processing\"" in command for command in decision.recommended_commands)


def test_router_json_payload_is_serializable():
    decision = intent_router.build_route(
        goal="validate",
        phase="review",
        source_path="converted-skills",
    )
    payload = intent_router.asdict(decision)

    assert payload["goal"] == "validate"
    assert payload["phase"] == "review"
    assert payload["primary_capability"] == "schema-and-regression-validation"
    assert len(payload["recommended_commands"]) == 4
    assert any("report_db_identity_drift.py" in command for command in payload["recommended_commands"])
