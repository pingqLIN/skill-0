import importlib
import sys
import types
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent))


def load_embedder_module():
    fake_sentence_transformers = types.ModuleType("sentence_transformers")

    class DummySentenceTransformer:  # pragma: no cover
        def __init__(self, *args, **kwargs):
            raise AssertionError("SkillEmbedder.__init__ should not run in this contract test")

    fake_sentence_transformers.SentenceTransformer = DummySentenceTransformer
    sys.modules["sentence_transformers"] = fake_sentence_transformers

    if "vector_db.embedder" in sys.modules:
        return importlib.reload(sys.modules["vector_db.embedder"])
    return importlib.import_module("vector_db.embedder")


def test_skill_to_text_prefers_canonical_fields_over_legacy_aliases():
    module = load_embedder_module()
    embedder = module.SkillEmbedder.__new__(module.SkillEmbedder)

    skill = {
        "meta": {
            "title": "Canonical Skill",
            "description": "Contract verification fixture",
        },
        "decomposition": {
            "actions": [
                {
                    "id": "a_001",
                    "name": "Read Input",
                    "action_type": "io_read",
                    "type": "legacy_action_type",
                    "description": "Read source payload",
                }
            ],
            "rules": [
                {
                    "id": "r_001",
                    "name": "Validate Input",
                    "condition_type": "validation",
                    "mode": "legacy_rule_mode",
                    "condition_expression": "input is present",
                    "condition": "legacy condition",
                    "description": "Check required input",
                }
            ],
            "directives": [
                {
                    "id": "d_001",
                    "name": "Completion State",
                    "directive_type": "completion",
                    "type": "legacy_directive_type",
                    "description": "Done successfully",
                    "content": "legacy directive content",
                }
            ],
        },
    }

    text = embedder.skill_to_text(skill)

    assert "Skill: Canonical Skill" in text
    assert "io_read: Read Input - Read source payload" in text
    assert "validation: Validate Input - input is present" in text
    assert "completion: Completion State - Done successfully" in text
    assert "legacy_action_type" not in text
    assert "legacy_rule_mode" not in text
    assert "legacy_directive_type" not in text
    assert "legacy directive content" not in text
