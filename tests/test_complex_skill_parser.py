from pathlib import Path

from scripts.auto_parse import parse_skill_md
from scripts.complex_skill_parser import parse_skill_manifest


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "complex_skills"


def _fixture_entry(name: str) -> Path:
    return FIXTURE_ROOT / name / "SKILL.md"


def test_parse_skill_md_remains_single_file_and_backward_compatible():
    content = _fixture_entry("fixture-simple-frontmatter").read_text(encoding="utf-8")

    result = parse_skill_md("fixture-simple-frontmatter", content)

    assert "manifest" not in result
    assert result["meta"]["schema_version"] == "2.4.0"
    assert result["decomposition"]["actions"]


def test_parse_skill_manifest_extracts_simple_manifest_summary():
    result = parse_skill_manifest(_fixture_entry("fixture-simple-frontmatter"))

    assert result["manifest"]["analysis_level"] == "manifest"
    assert result["manifest"]["supporting_files_count"] == 1
    assert result["manifest"]["command_references_count"] == 1
    assert result["manifest"]["delegation_nodes_count"] == 0
    assert result["parser_meta"]["target_schema_version"] == "2.5.0-draft"
    assert result["supporting_files"][0]["path"] == "README.md"
    assert result["command_references"][0]["authority_profile"] == "read_only"


def test_parse_skill_manifest_resolves_multi_ref_supporting_files_and_findings():
    result = parse_skill_manifest(_fixture_entry("fixture-multi-ref"))

    assert result["manifest"]["supporting_files_count"] == 5
    assert result["manifest"]["command_references_count"] == 2
    assert result["manifest"]["unresolved_references_count"] == 1

    supporting_paths = {item["path"]: item for item in result["supporting_files"]}
    assert supporting_paths["docs/release-checklist.md"]["resolved"] is True
    assert supporting_paths["docs/missing.md"]["resolved"] is False
    assert supporting_paths["scripts/prepare_release.sh"]["kind"] == "script"

    findings = {item["title"]: item for item in result["analysis_findings"]}
    assert "Unresolved reference: docs/missing.md" in findings
    assert any(
        finding["category"] == "execution_authority"
        for finding in result["analysis_findings"]
    )


def test_parse_skill_manifest_extracts_delegation_signals():
    result = parse_skill_manifest(_fixture_entry("fixture-delegation"))

    assert result["manifest"]["delegation_nodes_count"] == 3
    delegation_kinds = {node["kind"] for node in result["delegation_nodes"]}
    assert {"fork_context", "named_agent", "subagent_reference"} <= delegation_kinds

    command = result["command_references"][0]
    assert command["authority_profile"] == "process_exec"
    assert command["risk_grade"] == "medium"
    assert any(
        finding["title"] == "Delegation path present"
        for finding in result["analysis_findings"]
    )
