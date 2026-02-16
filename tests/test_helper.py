"""
Comprehensive test suite for scripts/helper.py

Tests for tool equivalence and code equivalence verification:
- SkillValidator: Schema validation logic
- SkillConverter: Format conversion correctness
- SkillTester: Execution path testing
- Template generation: Output correctness
- Complexity analysis: Calculation accuracy
"""

import pytest
import json
import re
import sys
import tempfile
from pathlib import Path

# Add parent directory to path to import helper
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.helper import (
    SkillValidator,
    SkillConverter,
    SkillTester,
    generate_template
)


def _expected_complexity_level(total: int) -> str:
    """Mirror helper.py thresholds so tests can validate level from parsed totals."""
    if total < 8:
        return "Simple"
    if total < 15:
        return "Medium"
    return "Complex"


def _parse_complexity_output(output: str) -> dict:
    """Extract complexity metrics from analyzer output for stable assertions."""
    metrics = {}
    for label, count, pct in re.findall(
        r"^(Actions|Rules|Directives):\s+(\d+)\s+\(([0-9.]+)%\)$",
        output,
        re.MULTILINE,
    ):
        metrics[label] = {"count": int(count), "pct": float(pct)}

    total_match = re.search(r"^Total:\s+(\d+)$", output, re.MULTILINE)
    level_match = re.search(r"^Complexity Level:\s+(\w+)$", output, re.MULTILINE)

    return {
        "metrics": metrics,
        "total": int(total_match.group(1)) if total_match else None,
        "level": level_match.group(1) if level_match else None,
    }


class TestSkillValidator:
    """Test suite for SkillValidator class - Tool Equivalence Tests"""
    
    @pytest.fixture
    def validator(self):
        """Create a validator instance"""
        return SkillValidator()
    
    @pytest.fixture
    def valid_skill_path(self):
        """Path to valid test skill"""
        return "tests/fixtures/valid_skill.json"
    
    @pytest.fixture
    def invalid_skill_path(self):
        """Path to invalid test skill"""
        return "tests/fixtures/invalid_skill.json"
    
    def test_validator_initialization(self, validator):
        """Test validator initializes correctly"""
        assert validator is not None
        assert validator.errors == []
        assert validator.warnings == []
    
    def test_validate_valid_skill(self, validator, valid_skill_path):
        """Test validation passes for valid skill"""
        result = validator.validate(valid_skill_path)
        assert result is True
        assert len(validator.errors) == 0
    
    def test_validate_nonexistent_file(self, validator):
        """Test validation fails for nonexistent file"""
        result = validator.validate("nonexistent.json")
        assert result is False
        assert len(validator.errors) > 0
        assert "File not found" in validator.errors[0]
    
    def test_validate_invalid_json(self, validator, tmp_path):
        """Test validation fails for invalid JSON"""
        bad_json = tmp_path / "bad.json"
        bad_json.write_text("{ invalid json }")
        
        result = validator.validate(str(bad_json))
        assert result is False
        assert len(validator.errors) > 0
        assert "Invalid JSON" in validator.errors[0]
    
    def test_validate_missing_required_fields(self, validator, invalid_skill_path):
        """Test validation fails for missing required fields"""
        result = validator.validate(invalid_skill_path)
        assert result is False
        assert len(validator.errors) > 0
    
    def test_validate_invalid_skill_layer(self, validator, tmp_path):
        """Test validation catches invalid skill_layer enum"""
        skill = {
            "meta": {
                "skill_id": "test",
                "name": "test",
                "skill_layer": "invalid_layer",
                "title": "Test",
                "description": "Test",
                "schema_version": "2.0.0"
            },
            "decomposition": {
                "actions": [],
                "rules": [],
                "directives": []
            }
        }
        
        skill_path = tmp_path / "test_skill.json"
        skill_path.write_text(json.dumps(skill))
        
        result = validator.validate(str(skill_path))
        assert result is False
        assert any("skill_layer" in error for error in validator.errors)
    
    def test_validate_invalid_action_id(self, validator, tmp_path):
        """Test validation catches invalid action ID pattern"""
        skill = {
            "meta": {
                "skill_id": "test",
                "name": "test",
                "skill_layer": "claude_skill",
                "title": "Test",
                "description": "Test",
                "schema_version": "2.0.0"
            },
            "decomposition": {
                "actions": [{
                    "id": "invalid_id",
                    "name": "Test",
                    "action_type": "transform",
                    "description": "Test",
                    "deterministic": True
                }],
                "rules": [],
                "directives": []
            }
        }
        
        skill_path = tmp_path / "test_skill.json"
        skill_path.write_text(json.dumps(skill))
        
        result = validator.validate(str(skill_path))
        assert result is False
        assert any("Invalid action ID" in error for error in validator.errors)
    
    def test_validate_invalid_action_type(self, validator, tmp_path):
        """Test validation catches invalid action_type enum"""
        skill = {
            "meta": {
                "skill_id": "test",
                "name": "test",
                "skill_layer": "claude_skill",
                "title": "Test",
                "description": "Test",
                "schema_version": "2.0.0"
            },
            "decomposition": {
                "actions": [{
                    "id": "a_001",
                    "name": "Test",
                    "action_type": "invalid_type",
                    "description": "Test",
                    "deterministic": True
                }],
                "rules": [],
                "directives": []
            }
        }
        
        skill_path = tmp_path / "test_skill.json"
        skill_path.write_text(json.dumps(skill))
        
        result = validator.validate(str(skill_path))
        assert result is False
        assert any("action_type" in error for error in validator.errors)


class TestSkillConverter:
    """Test suite for SkillConverter class - Code Equivalence Tests"""
    
    @pytest.fixture
    def converter(self):
        """Create a converter instance"""
        return SkillConverter()
    
    @pytest.fixture
    def sample_markdown_path(self):
        """Path to sample markdown file"""
        return "tests/fixtures/sample.md"
    
    def test_converter_initialization(self, converter):
        """Test converter initializes correctly"""
        assert converter is not None
    
    def test_extract_title_from_markdown(self, converter):
        """Test title extraction from markdown"""
        content = "# Test Title\n\nSome content"
        title = converter._extract_title(content)
        assert title == "Test Title"
    
    def test_extract_title_no_header(self, converter):
        """Test title extraction when no header exists"""
        content = "Some content without header"
        title = converter._extract_title(content)
        assert title == "Untitled Skill"
    
    def test_extract_description_from_markdown(self, converter):
        """Test description extraction from markdown"""
        content = "# Title\n\nThis is the description.\n\nMore content"
        description = converter._extract_description(content)
        assert "description" in description.lower()
    
    def test_create_template_structure(self, converter):
        """Test template creation has correct structure"""
        template = converter._create_template("Test Title", "Test Description")
        
        # Check meta section
        assert "meta" in template
        assert template["meta"]["title"] == "Test Title"
        assert template["meta"]["description"] == "Test Description"
        assert template["meta"]["schema_version"] == "2.0.0"
        
        # Check decomposition section
        assert "decomposition" in template
        assert "actions" in template["decomposition"]
        assert "rules" in template["decomposition"]
        assert "directives" in template["decomposition"]
    
    def test_markdown_to_json_conversion(self, converter, sample_markdown_path, tmp_path):
        """Test complete markdown to JSON conversion"""
        output_path = tmp_path / "output.json"
        
        converter.markdown_to_json(sample_markdown_path, str(output_path))
        
        # Verify file was created
        assert output_path.exists()
        
        # Verify JSON structure
        with open(output_path) as f:
            result = json.load(f)
        
        assert "meta" in result
        assert "decomposition" in result
        assert result["meta"]["title"] == "Test Skill"
    
    def test_converted_skill_is_valid_json(self, converter, sample_markdown_path, tmp_path):
        """Test converted skill is valid JSON (code equivalence)"""
        output_path = tmp_path / "output.json"
        converter.markdown_to_json(sample_markdown_path, str(output_path))
        
        # Should not raise JSONDecodeError
        with open(output_path) as f:
            data = json.load(f)
        
        assert isinstance(data, dict)


class TestSkillTester:
    """Test suite for SkillTester class - Execution Path Testing"""
    
    @pytest.fixture
    def tester(self, valid_skill_path):
        """Create a tester instance with valid skill"""
        return SkillTester(valid_skill_path)
    
    @pytest.fixture
    def valid_skill_path(self):
        """Path to valid test skill"""
        return "tests/fixtures/valid_skill.json"
    
    def test_tester_initialization(self, tester):
        """Test tester initializes correctly"""
        assert tester is not None
        assert hasattr(tester, 'skill')
        assert hasattr(tester, 'decomposition')
    
    def test_get_all_element_ids(self, tester):
        """Test element ID extraction"""
        ids = tester._get_all_element_ids()
        
        assert isinstance(ids, set)
        assert "a_001" in ids
        assert "a_002" in ids
        assert "r_001" in ids
        assert "d_001" in ids
    
    def test_get_element_type(self, tester):
        """Test element type detection"""
        assert tester._get_element_type("a_001") == "action"
        assert tester._get_element_type("r_001") == "rule"
        assert tester._get_element_type("d_001") == "directive"
        assert tester._get_element_type("x_001") == "unknown"
    
    def test_execution_path_validation(self, tester, capsys):
        """Test execution path testing functionality"""
        tester.test_execution_paths()
        
        captured = capsys.readouterr()
        output = captured.out
        
        paths = tester.skill.get("execution_paths", [])
        assert len(paths) > 0

        first_path = paths[0]
        expected_steps = len(first_path.get("sequence", []))

        assert re.search(r"Testing\s+\d+\s+execution path\(s\)", output)
        assert f"Path: {first_path['path_name']}" in output
        assert re.search(rf"Steps:\s+{expected_steps}\b", output)
        assert "All elements found" in output

        flow_match = re.search(r"Flow:\s+([^\n]+)", output)
        assert flow_match is not None

        flow_types = re.findall(r"(action|rule|directive|unknown)", flow_match.group(1))
        expected_types = [tester._get_element_type(i) for i in first_path["sequence"]]
        assert flow_types == expected_types
    
    def test_complexity_analysis(self, tester, capsys):
        """Test complexity analysis calculations"""
        tester.analyze_complexity()
        
        captured = capsys.readouterr()
        output = captured.out
        
        parsed = _parse_complexity_output(output)

        expected_counts = {
            "Actions": len(tester.decomposition.get("actions", [])),
            "Rules": len(tester.decomposition.get("rules", [])),
            "Directives": len(tester.decomposition.get("directives", [])),
        }
        expected_total = sum(expected_counts.values())

        assert set(parsed["metrics"]) == {"Actions", "Rules", "Directives"}
        assert parsed["total"] == expected_total
        assert parsed["level"] == _expected_complexity_level(expected_total)

        percentages = []
        for label, expected_count in expected_counts.items():
            assert parsed["metrics"][label]["count"] == expected_count
            pct = parsed["metrics"][label]["pct"]
            assert 0.0 <= pct <= 100.0
            percentages.append(pct)

        # Output is rounded to one decimal place, so use a small tolerance.
        assert abs(sum(percentages) - 100.0) <= 0.2
    
    def test_complexity_level_simple(self, tester, capsys):
        """Test complexity level calculation for simple skills"""
        tester.analyze_complexity()

        output = capsys.readouterr().out
        parsed = _parse_complexity_output(output)

        assert parsed["total"] is not None
        assert parsed["total"] < 8
        assert parsed["level"] == "Simple"


class TestTemplateGeneration:
    """Test suite for template generation - Tool Equivalence"""
    
    def test_generate_template_creates_file(self, tmp_path):
        """Test template generation creates a file"""
        output_path = tmp_path / "template.json"
        generate_template(str(output_path))
        
        assert output_path.exists()
    
    def test_generated_template_is_valid_json(self, tmp_path):
        """Test generated template is valid JSON"""
        output_path = tmp_path / "template.json"
        generate_template(str(output_path))
        
        with open(output_path) as f:
            data = json.load(f)
        
        assert isinstance(data, dict)
    
    def test_generated_template_has_required_structure(self, tmp_path):
        """Test generated template has all required sections"""
        output_path = tmp_path / "template.json"
        generate_template(str(output_path))
        
        with open(output_path) as f:
            template = json.load(f)
        
        # Check required sections
        assert "meta" in template
        assert "original_definition" in template
        assert "decomposition" in template
        assert "execution_paths" in template
        
        # Check decomposition has all element types
        assert "actions" in template["decomposition"]
        assert "rules" in template["decomposition"]
        assert "directives" in template["decomposition"]
        
        # Check elements exist with correct IDs
        assert len(template["decomposition"]["actions"]) > 0
        assert template["decomposition"]["actions"][0]["id"] == "a_001"
        assert template["decomposition"]["rules"][0]["id"] == "r_001"
        assert template["decomposition"]["directives"][0]["id"] == "d_001"
    
    def test_generated_template_validates(self, tmp_path):
        """Test generated template passes validation (code equivalence)"""
        output_path = tmp_path / "template.json"
        generate_template(str(output_path))
        
        validator = SkillValidator()
        result = validator.validate(str(output_path))
        
        assert result is True
        assert len(validator.errors) == 0


class TestIntegrationWorkflows:
    """Integration tests for end-to-end workflows"""
    
    def test_full_workflow_markdown_to_validated_skill(self, tmp_path):
        """Test complete workflow: markdown → JSON → validation"""
        # Step 1: Convert markdown to JSON
        md_content = "# Test Skill\n\nA test skill for integration testing"
        md_path = tmp_path / "input.md"
        md_path.write_text(md_content)
        
        json_path = tmp_path / "output.json"
        
        converter = SkillConverter()
        converter.markdown_to_json(str(md_path), str(json_path))
        
        # Step 2: Validate the generated JSON
        validator = SkillValidator()
        result = validator.validate(str(json_path))
        
        # Should pass validation
        assert result is True
        assert len(validator.errors) == 0
    
    def test_template_generation_validation_testing_workflow(self, tmp_path, capsys):
        """Test workflow: generate → validate → test"""
        # Step 1: Generate template
        template_path = tmp_path / "template.json"
        generate_template(str(template_path))
        
        # Step 2: Validate
        validator = SkillValidator()
        valid = validator.validate(str(template_path))
        assert valid is True
        
        # Step 3: Test execution paths
        tester = SkillTester(str(template_path))
        tester.test_execution_paths()
        tester.analyze_complexity()

        output = capsys.readouterr().out
        with open(template_path) as f:
            template = json.load(f)

        first_path = template["execution_paths"][0]
        assert f"Path: {first_path['path_name']}" in output
        assert re.search(rf"Steps:\s+{len(first_path['sequence'])}\b", output)
        assert "All elements found" in output

        parsed = _parse_complexity_output(output)
        expected_total = (
            len(template["decomposition"]["actions"])
            + len(template["decomposition"]["rules"])
            + len(template["decomposition"]["directives"])
        )
        assert parsed["total"] == expected_total
        assert parsed["level"] == _expected_complexity_level(expected_total)
    
    def test_tool_equivalence_validator_consistency(self, valid_skill_path="tests/fixtures/valid_skill.json"):
        """Test validator produces consistent results (tool equivalence)"""
        validator1 = SkillValidator()
        validator2 = SkillValidator()
        
        result1 = validator1.validate(valid_skill_path)
        result2 = validator2.validate(valid_skill_path)
        
        # Both validators should produce same result
        assert result1 == result2
        assert len(validator1.errors) == len(validator2.errors)
    
    def test_code_equivalence_converter_deterministic(self, tmp_path):
        """Test converter produces deterministic output (code equivalence)"""
        md_content = "# Test\n\nDescription"
        md_path = tmp_path / "input.md"
        md_path.write_text(md_content)
        
        output1 = tmp_path / "output1.json"
        output2 = tmp_path / "output2.json"
        
        converter1 = SkillConverter()
        converter2 = SkillConverter()
        
        converter1.markdown_to_json(str(md_path), str(output1))
        converter2.markdown_to_json(str(md_path), str(output2))
        
        # Load both outputs
        with open(output1) as f:
            data1 = json.load(f)
        with open(output2) as f:
            data2 = json.load(f)
        
        # Exclude timestamp which will differ
        del data1["meta"]["parse_timestamp"]
        del data2["meta"]["parse_timestamp"]
        
        # Should produce identical output
        assert data1 == data2


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    def test_validator_handles_malformed_json(self, tmp_path):
        """Test validator handles malformed JSON gracefully"""
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("{ this is not valid JSON }")
        
        validator = SkillValidator()
        result = validator.validate(str(bad_file))
        
        assert result is False
        assert len(validator.errors) > 0
    
    def test_converter_handles_empty_markdown(self, tmp_path):
        """Test converter handles empty markdown file"""
        empty_md = tmp_path / "empty.md"
        empty_md.write_text("")
        
        output = tmp_path / "output.json"
        
        converter = SkillConverter()
        # Should not crash
        converter.markdown_to_json(str(empty_md), str(output))
        
        assert output.exists()
    
    def test_tester_handles_skill_without_execution_paths(self, tmp_path):
        """Test tester handles skills without execution paths"""
        skill = {
            "meta": {
                "skill_id": "test",
                "name": "test",
                "skill_layer": "claude_skill",
                "title": "Test",
                "description": "Test",
                "schema_version": "2.0.0"
            },
            "decomposition": {
                "actions": [],
                "rules": [],
                "directives": []
            }
            # No execution_paths
        }
        
        skill_path = tmp_path / "skill.json"
        skill_path.write_text(json.dumps(skill))
        
        tester = SkillTester(str(skill_path))
        # Should handle gracefully
        tester.test_execution_paths()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
