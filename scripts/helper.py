"""
Helper module for skill-0 decomposition utilities.

Provides:
- SkillValidator: Schema validation logic
- SkillConverter: Format conversion (markdown -> JSON)
- SkillTester: Execution path testing and complexity analysis
- generate_template: Template generation utility
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

VALID_SKILL_LAYERS = {"claude_skill", "mcp_tool", "mcp_server_internal"}
VALID_ACTION_TYPES = {
    "transform", "io_read", "io_write", "compute",
    "external_call", "state_change", "llm_inference", "await_input",
}
REQUIRED_META_FIELDS = {"skill_id", "name", "skill_layer", "title", "description", "schema_version"}
ACTION_ID_PATTERN = re.compile(r"^a_\d{3}$")
RULE_ID_PATTERN = re.compile(r"^r_\d{3}$")
DIRECTIVE_ID_PATTERN = re.compile(r"^d_\d{3}$")


class SkillValidator:
    """Validates skill JSON files against the schema."""

    def __init__(self):
        self.errors = []
        self.warnings = []

    def validate(self, path: str) -> bool:
        """Validate a skill JSON file. Returns True if valid."""
        self.errors = []
        self.warnings = []

        skill_path = Path(path)
        if not skill_path.exists():
            self.errors.append(f"File not found: {path}")
            return False

        try:
            with open(skill_path, encoding="utf-8") as f:
                skill = json.load(f)
        except json.JSONDecodeError as exc:
            self.errors.append(f"Invalid JSON: {exc}")
            return False

        self._validate_meta(skill)
        self._validate_decomposition(skill)

        return len(self.errors) == 0

    def _validate_meta(self, skill: dict) -> None:
        meta = skill.get("meta", {})
        if not meta:
            self.errors.append("Missing required 'meta' section")
            return

        missing = REQUIRED_META_FIELDS - set(meta.keys())
        for field in sorted(missing):
            self.errors.append(f"Missing required meta field: {field}")

        layer = meta.get("skill_layer")
        if layer and layer not in VALID_SKILL_LAYERS:
            self.errors.append(
                f"Invalid skill_layer '{layer}'. Must be one of: {sorted(VALID_SKILL_LAYERS)}"
            )

    def _validate_decomposition(self, skill: dict) -> None:
        decomp = skill.get("decomposition")
        if decomp is None:
            self.errors.append("Missing required 'decomposition' section")
            return

        for action in decomp.get("actions", []):
            action_id = action.get("id", "")
            if not ACTION_ID_PATTERN.match(action_id):
                self.errors.append(f"Invalid action ID '{action_id}'. Must match a_NNN pattern")
            action_type = action.get("action_type", "")
            if action_type and action_type not in VALID_ACTION_TYPES:
                self.errors.append(
                    f"Invalid action_type '{action_type}'. Must be one of: {sorted(VALID_ACTION_TYPES)}"
                )

        for rule in decomp.get("rules", []):
            rule_id = rule.get("id", "")
            if not RULE_ID_PATTERN.match(rule_id):
                self.errors.append(f"Invalid rule ID '{rule_id}'. Must match r_NNN pattern")

        for directive in decomp.get("directives", []):
            directive_id = directive.get("id", "")
            if not DIRECTIVE_ID_PATTERN.match(directive_id):
                self.errors.append(f"Invalid directive ID '{directive_id}'. Must match d_NNN pattern")


class SkillConverter:
    """Converts skill definitions between formats."""

    def _extract_title(self, content: str) -> str:
        """Extract title from markdown H1 header."""
        for line in content.splitlines():
            if line.startswith("# "):
                return line[2:].strip()
        return "Untitled Skill"

    def _extract_description(self, content: str) -> str:
        """Extract first paragraph following the title."""
        lines = content.splitlines()
        past_title = False
        paragraph_lines = []

        for line in lines:
            if line.startswith("# ") and not past_title:
                past_title = True
                continue
            if past_title:
                if line.strip():
                    paragraph_lines.append(line.strip())
                elif paragraph_lines:
                    break

        if paragraph_lines:
            return " ".join(paragraph_lines)
        return "No description provided"

    def _create_template(self, title: str, description: str) -> dict:
        """Create a minimal skill template structure."""
        slug = re.sub(r"\s+", "-", title.lower())
        return {
            "meta": {
                "skill_id": slug,
                "name": slug,
                "skill_layer": "claude_skill",
                "title": title,
                "description": description,
                "schema_version": "2.0.0",
            },
            "decomposition": {
                "actions": [],
                "rules": [],
                "directives": [],
            },
        }

    def markdown_to_json(self, input_path: str, output_path: str) -> None:
        """Convert a markdown skill file to JSON format."""
        with open(input_path, encoding="utf-8") as f:
            content = f.read()

        title = self._extract_title(content)
        description = self._extract_description(content)
        template = self._create_template(title, description)
        template["meta"]["parse_timestamp"] = datetime.now(timezone.utc).isoformat()

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(template, f, indent=2, ensure_ascii=False)


class SkillTester:
    """Tests execution paths and analyses complexity of a skill."""

    def __init__(self, skill_path: str):
        with open(skill_path, encoding="utf-8") as f:
            self.skill = json.load(f)
        self.decomposition = self.skill.get("decomposition", {})

    def _get_all_element_ids(self) -> set:
        """Return all element IDs from the decomposition."""
        ids = set()
        for action in self.decomposition.get("actions", []):
            if "id" in action:
                ids.add(action["id"])
        for rule in self.decomposition.get("rules", []):
            if "id" in rule:
                ids.add(rule["id"])
        for directive in self.decomposition.get("directives", []):
            if "id" in directive:
                ids.add(directive["id"])
        return ids

    def _get_element_type(self, element_id: str) -> str:
        """Return the type of an element based on its ID prefix."""
        if element_id.startswith("a_"):
            return "action"
        if element_id.startswith("r_"):
            return "rule"
        if element_id.startswith("d_"):
            return "directive"
        return "unknown"

    def test_execution_paths(self) -> None:
        """Test and report on defined execution paths."""
        paths = self.skill.get("execution_paths", [])
        if not paths:
            print("No execution paths defined.")
            return

        known_ids = self._get_all_element_ids()
        for path in paths:
            path_name = path.get("path_name", "Unnamed Path")
            sequence = path.get("sequence", [])
            print(f"Execution path: {path_name}")
            for step in sequence:
                element_type = self._get_element_type(step)
                valid = step in known_ids
                print(f"  [{element_type}] {step} {'OK' if valid else 'MISSING'}")

    def analyze_complexity(self) -> None:
        """Analyze and print complexity metrics for the skill."""
        actions = self.decomposition.get("actions", [])
        rules = self.decomposition.get("rules", [])
        directives = self.decomposition.get("directives", [])
        total = len(actions) + len(rules) + len(directives)

        if total < 8:
            level = "Simple"
        elif total < 20:
            level = "Moderate"
        else:
            level = "Complex"

        print(f"Actions: {len(actions)}")
        print(f"Rules: {len(rules)}")
        print(f"Directives: {len(directives)}")
        print(f"Complexity Level: {level} (total elements: {total})")


def generate_template(output_path: str) -> None:
    """Generate a skeleton skill decomposition template JSON file."""
    template = {
        "meta": {
            "skill_id": "template__new-skill",
            "name": "new-skill",
            "skill_layer": "claude_skill",
            "title": "New Skill Template",
            "description": "Template for a new skill decomposition",
            "schema_version": "2.0.0",
            "parse_timestamp": datetime.now(timezone.utc).isoformat(),
            "parser_version": "1.0.0",
            "parsed_by": "generate_template",
        },
        "original_definition": {
            "source": "template",
            "skill_name": "New Skill Template",
            "skill_description": "Template skill definition",
        },
        "decomposition": {
            "actions": [
                {
                    "id": "a_001",
                    "name": "Sample Action",
                    "action_type": "transform",
                    "description": "A sample action",
                    "deterministic": True,
                    "immutable_elements": [],
                    "mutable_elements": [],
                    "side_effects": [],
                }
            ],
            "rules": [
                {
                    "id": "r_001",
                    "name": "Sample Rule",
                    "condition_type": "validation",
                    "condition": "Input is valid",
                    "output": "boolean",
                    "description": "A sample validation rule",
                }
            ],
            "directives": [
                {
                    "id": "d_001",
                    "directive_type": "completion",
                    "description": "Processing completed",
                    "decomposable": False,
                }
            ],
        },
        "execution_paths": [
            {
                "path_name": "Happy Path",
                "sequence": ["a_001", "r_001", "d_001"],
                "description": "Default execution flow",
            }
        ],
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(template, f, indent=2, ensure_ascii=False)
