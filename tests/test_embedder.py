import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from vector_db.embedder import SkillEmbedder


def test_skill_to_text_uses_canonical_fields_without_model_dependency():
    embedder = SkillEmbedder.__new__(SkillEmbedder)
    skill = {
        "meta": {
            "title": "XLSX Skill",
            "description": "Spreadsheet workflows",
        },
        "decomposition": {
            "actions": [
                {
                    "id": "a_001",
                    "name": "Read Excel File",
                    "action_type": "io_read",
                    "description": "Load workbook contents",
                }
            ],
            "rules": [
                {
                    "id": "r_001",
                    "name": "Use formulas instead of hardcoded values",
                    "condition_type": "validation",
                    "condition_expression": "always",
                }
            ],
            "directives": [
                {
                    "id": "d_001",
                    "name": "Prefer formulas",
                    "directive_type": "principle",
                    "description": "Use spreadsheet formulas when possible",
                }
            ],
        },
    }

    text = embedder.skill_to_text(skill)

    assert "Skill: XLSX Skill" in text
    assert "Description: Spreadsheet workflows" in text
    assert "Actions: io_read: Read Excel File - Load workbook contents" in text
    assert (
        "Rules: validation: Use formulas instead of hardcoded values - always"
        in text
    )
    assert (
        "Directives: principle: Prefer formulas - Use spreadsheet formulas when possible"
        in text
    )
