import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.schema_contract import iter_validation_errors, normalize_skill_document
from tools.validate_skill_schema import validate_file
from tools.batch_parse import parse_skill, SKILLS


def test_normalize_skill_document_backfills_legacy_fields():
    legacy_skill = {
        "meta": {
            "skill_id": "claude__legacy-skill",
            "name": "legacy-skill",
            "skill_layer": "claude_skill",
            "schema_version": "2.1.0",
            "parse_timestamp": "2026-03-27T00:00:00Z",
        },
        "decomposition": {
            "actions": [
                {
                    "id": "a_001",
                    "description": "Read input",
                    "action_type": "io_read",
                }
            ],
            "rules": [
                {
                    "id": "r_001",
                    "description": "Validate input is present",
                    "condition": "input exists",
                    "output": "proceed_or_halt",
                }
            ],
            "directives": [
                {
                    "id": "d_001",
                    "directive_type": "completion",
                    "description": "Processing completed successfully",
                }
            ],
        },
    }

    normalized = normalize_skill_document(legacy_skill)

    assert normalized["meta"]["skill_id"] == "claude__skill__legacy_skill"
    assert normalized["meta"]["schema_version"] == "2.4.0"
    assert normalized["decomposition"]["actions"][0]["name"] == "Read input"
    assert normalized["decomposition"]["rules"][0]["name"] == "Validate input is present"
    assert normalized["decomposition"]["rules"][0]["condition_type"] == "existence_check"
    assert normalized["decomposition"]["rules"][0]["returns"] == "boolean"
    assert normalized["decomposition"]["rules"][0]["condition_expression"] == "input exists"
    assert "condition" not in normalized["decomposition"]["rules"][0]
    assert "output" not in normalized["decomposition"]["rules"][0]
    assert normalized["decomposition"]["directives"][0]["name"] == "Processing completed successfully"
    assert not list(iter_validation_errors(normalized))


def test_valid_fixture_is_schema_compliant():
    fixture_path = Path("tests/fixtures/valid_skill.json")
    skill = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert not list(iter_validation_errors(skill))


def test_validate_file_reports_schema_errors(tmp_path):
    invalid_file = tmp_path / "invalid.json"
    invalid_file.write_text(
        json.dumps(
            {
                "meta": {
                    "skill_id": "claude__broken",
                    "name": "broken",
                    "skill_layer": "claude_skill",
                    "schema_version": "2.1.0",
                    "parse_timestamp": "2026-03-27T00:00:00Z",
                },
                "decomposition": {
                    "actions": [],
                    "rules": [{"id": "r_001", "description": "Missing canonical fields"}],
                    "directives": [],
                },
            }
        ),
        encoding="utf-8",
    )

    errors = validate_file(invalid_file, Path("schema/skill-decomposition.schema.json"), max_errors=10)

    assert errors
    assert any("condition_type" in error for error in errors)


def test_batch_parse_emits_canonical_meta():
    parsed = parse_skill("xlsx", SKILLS["xlsx"])

    meta = parsed["meta"]
    first_rule = parsed["decomposition"]["rules"][0]
    first_directive = parsed["decomposition"]["directives"][0]

    assert meta["skill_id"] == "claude__skill__xlsx"
    assert meta["schema_version"] == "2.4.0"
    assert meta["parser_version"] == "skill-0 v2.4"
    assert "condition" not in first_rule
    assert "output" not in first_rule
    assert first_rule["condition_expression"] == "always"
    assert first_rule["returns"] == "boolean"
    assert first_directive["name"]
    assert not list(iter_validation_errors(parsed))
