#!/usr/bin/env python3
"""
Helper utilities for skill-0 format conversion and testing

This script provides utilities to:
1. Convert between different skill formats
2. Validate skill decompositions
3. Generate templates from examples
4. Extract patterns from parsed skills
5. Test execution flows

Usage:
    python scripts/helper.py validate parsed/my-skill.json
    python scripts/helper.py convert input.md parsed/output.json
    python scripts/helper.py template --output template.json
    python scripts/helper.py test parsed/my-skill.json
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import re


class SkillValidator:
    """Validates skill decompositions against schema"""
    
    def __init__(self, schema_path: str = "schema/skill-decomposition.schema.json"):
        self.schema_path = Path(schema_path)
        self.errors = []
        self.warnings = []
    
    def validate(self, skill_path: str) -> bool:
        """Validate a skill file"""
        skill_file = Path(skill_path)
        
        if not skill_file.exists():
            self.errors.append(f"File not found: {skill_path}")
            return False
        
        try:
            with open(skill_file) as f:
                skill = json.load(f)
        except json.JSONDecodeError as e:
            self.errors.append(f"Invalid JSON: {e}")
            return False
        
        # Validate structure
        self._validate_meta(skill.get('meta', {}))
        self._validate_decomposition(skill.get('decomposition', {}))
        
        return len(self.errors) == 0
    
    def _validate_meta(self, meta: Dict) -> None:
        """Validate meta section"""
        required = ['skill_id', 'name', 'skill_layer', 'title', 'description', 'schema_version']
        for field in required:
            if field not in meta:
                self.errors.append(f"Missing required meta field: {field}")
        
        # Validate skill_layer
        if meta.get('skill_layer') not in ['claude_skill', 'mcp_tool', 'mcp_server_internal']:
            self.errors.append(f"Invalid skill_layer: {meta.get('skill_layer')}")
        
        # Validate schema version
        if meta.get('schema_version') != '2.0.0':
            self.warnings.append(f"Schema version {meta.get('schema_version')} may be outdated")
    
    def _validate_decomposition(self, decomposition: Dict) -> None:
        """Validate decomposition section"""
        # Validate actions
        for action in decomposition.get('actions', []):
            self._validate_action(action)
        
        # Validate rules
        for rule in decomposition.get('rules', []):
            self._validate_rule(rule)
        
        # Validate directives
        for directive in decomposition.get('directives', []):
            self._validate_directive(directive)
    
    def _validate_action(self, action: Dict) -> None:
        """Validate an action"""
        # Check ID pattern
        if not re.match(r'^a_\d{3}$', action.get('id', '')):
            self.errors.append(f"Invalid action ID: {action.get('id')}")
        
        # Check action_type
        valid_types = ['transform', 'io_read', 'io_write', 'compute', 
                       'external_call', 'state_change', 'llm_inference', 'await_input']
        if action.get('action_type') not in valid_types:
            self.errors.append(f"Invalid action_type: {action.get('action_type')}")
        
        # Check required fields
        required = ['id', 'name', 'action_type', 'description', 'deterministic']
        for field in required:
            if field not in action:
                self.errors.append(f"Action {action.get('id')} missing field: {field}")
    
    def _validate_rule(self, rule: Dict) -> None:
        """Validate a rule"""
        # Check ID pattern
        if not re.match(r'^r_\d{3}$', rule.get('id', '')):
            self.errors.append(f"Invalid rule ID: {rule.get('id')}")
        
        # Check condition_type
        valid_types = ['validation', 'existence_check', 'type_check', 'range_check',
                       'permission_check', 'state_check', 'consistency_check', 'threshold_check']
        if rule.get('condition_type') not in valid_types:
            self.errors.append(f"Invalid condition_type: {rule.get('condition_type')}")
    
    def _validate_directive(self, directive: Dict) -> None:
        """Validate a directive"""
        # Check ID pattern
        if not re.match(r'^d_\d{3}$', directive.get('id', '')):
            self.errors.append(f"Invalid directive ID: {directive.get('id')}")
        
        # Check directive_type
        valid_types = ['completion', 'knowledge', 'principle', 'constraint', 'preference', 'strategy']
        if directive.get('directive_type') not in valid_types:
            self.errors.append(f"Invalid directive_type: {directive.get('directive_type')}")
    
    def print_results(self) -> None:
        """Print validation results"""
        if self.errors:
            print("❌ Validation Errors:")
            for error in self.errors:
                print(f"  - {error}")
        
        if self.warnings:
            print("\n⚠️  Warnings:")
            for warning in self.warnings:
                print(f"  - {warning}")
        
        if not self.errors and not self.warnings:
            print("✅ Validation passed")


class SkillConverter:
    """Convert between different skill formats"""
    
    def markdown_to_json(self, md_path: str, output_path: str) -> None:
        """Convert markdown description to JSON template"""
        with open(md_path) as f:
            content = f.read()
        
        # Extract basic info from markdown
        title = self._extract_title(content)
        description = self._extract_description(content)
        
        # Generate template
        skill = self._create_template(title, description)
        
        with open(output_path, 'w') as f:
            json.dump(skill, f, indent=2)
        
        print(f"✅ Converted {md_path} -> {output_path}")
        print("⚠️  Template created - please fill in actions, rules, and directives manually")
    
    def _extract_title(self, content: str) -> str:
        """Extract title from markdown"""
        match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        return match.group(1) if match else "Untitled Skill"
    
    def _extract_description(self, content: str) -> str:
        """Extract description from markdown"""
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.startswith('# '):
                # Get next non-empty line after title
                for j in range(i+1, len(lines)):
                    if lines[j].strip() and not lines[j].startswith('#'):
                        return lines[j].strip()
        return "No description available"
    
    def _create_template(self, title: str, description: str) -> Dict:
        """Create JSON template"""
        return {
            "meta": {
                "skill_id": f"claude__{title.lower().replace(' ', '-')}",
                "name": title.lower().replace(' ', '-'),
                "skill_layer": "claude_skill",
                "title": title,
                "description": description,
                "schema_version": "2.0.0",
                "parse_timestamp": datetime.utcnow().isoformat() + "Z",
                "parser_version": "skill-0 v2.0",
                "parsed_by": "helper.py"
            },
            "original_definition": {
                "source": "converted from markdown",
                "skill_name": title,
                "skill_description": description
            },
            "decomposition": {
                "actions": [],
                "rules": [],
                "directives": []
            }
        }


class SkillTester:
    """Test skill execution flows"""
    
    def __init__(self, skill_path: str):
        with open(skill_path) as f:
            self.skill = json.load(f)
        self.decomposition = self.skill.get('decomposition', {})
    
    def test_execution_paths(self) -> None:
        """Test all execution paths"""
        paths = self.skill.get('execution_paths', [])
        
        if not paths:
            print("⚠️  No execution paths defined")
            return
        
        print(f"Testing {len(paths)} execution path(s)...\n")
        
        for path in paths:
            self._test_path(path)
    
    def _test_path(self, path: Dict) -> None:
        """Test a single execution path"""
        name = path.get('path_name', 'Unnamed')
        sequence = path.get('sequence', [])
        
        print(f"Path: {name}")
        print(f"  Steps: {len(sequence)}")
        
        # Verify all IDs exist
        all_ids = self._get_all_element_ids()
        missing = [id for id in sequence if id not in all_ids]
        
        if missing:
            print(f"  ❌ Missing elements: {missing}")
        else:
            print(f"  ✅ All elements found")
        
        # Check for action → rule → directive pattern
        types = [self._get_element_type(id) for id in sequence if id in all_ids]
        print(f"  Flow: {' → '.join(types)}")
        print()
    
    def _get_all_element_ids(self) -> set:
        """Get all element IDs in skill"""
        ids = set()
        for action in self.decomposition.get('actions', []):
            ids.add(action.get('id'))
        for rule in self.decomposition.get('rules', []):
            ids.add(rule.get('id'))
        for directive in self.decomposition.get('directives', []):
            ids.add(directive.get('id'))
        return ids
    
    def _get_element_type(self, element_id: str) -> str:
        """Get element type from ID"""
        if element_id.startswith('a_'):
            return 'action'
        elif element_id.startswith('r_'):
            return 'rule'
        elif element_id.startswith('d_'):
            return 'directive'
        return 'unknown'
    
    def analyze_complexity(self) -> None:
        """Analyze skill complexity"""
        actions = len(self.decomposition.get('actions', []))
        rules = len(self.decomposition.get('rules', []))
        directives = len(self.decomposition.get('directives', []))
        total = actions + rules + directives
        
        print("Skill Complexity Analysis")
        print("=" * 40)
        print(f"Actions:    {actions:3d} ({actions/total*100:.1f}%)")
        print(f"Rules:      {rules:3d} ({rules/total*100:.1f}%)")
        print(f"Directives: {directives:3d} ({directives/total*100:.1f}%)")
        print(f"Total:      {total:3d}")
        print()
        
        # Determine complexity level
        if total < 8:
            level = "Simple"
        elif total < 15:
            level = "Medium"
        else:
            level = "Complex"
        
        print(f"Complexity Level: {level}")
        
        # Check for non-deterministic operations
        non_det = [a['id'] for a in self.decomposition.get('actions', []) 
                   if not a.get('deterministic', True)]
        if non_det:
            print(f"\n⚠️  Non-deterministic actions: {', '.join(non_det)}")


def generate_template(output_path: str) -> None:
    """Generate empty skill template"""
    template = {
        "meta": {
            "skill_id": "claude__template",
            "name": "template",
            "skill_layer": "claude_skill",
            "title": "Skill Template",
            "description": "Template for creating new skills",
            "schema_version": "2.0.0",
            "parse_timestamp": datetime.utcnow().isoformat() + "Z",
            "parser_version": "skill-0 v2.0",
            "parsed_by": "helper.py"
        },
        "original_definition": {
            "source": "",
            "skill_name": "",
            "skill_description": ""
        },
        "decomposition": {
            "actions": [
                {
                    "id": "a_001",
                    "name": "Example Action",
                    "action_type": "transform",
                    "description": "Describe what this action does",
                    "deterministic": True,
                    "immutable_elements": [],
                    "mutable_elements": [],
                    "side_effects": []
                }
            ],
            "rules": [
                {
                    "id": "r_001",
                    "name": "Example Rule",
                    "condition_type": "validation",
                    "condition": "Condition to evaluate",
                    "output": "boolean",
                    "description": "Describe what this rule checks"
                }
            ],
            "directives": [
                {
                    "id": "d_001",
                    "directive_type": "completion",
                    "description": "Describe the completion state",
                    "decomposable": False
                }
            ]
        },
        "execution_paths": [
            {
                "path_name": "Happy Path",
                "sequence": ["a_001", "r_001", "d_001"],
                "description": "Normal execution flow"
            }
        ]
    }
    
    with open(output_path, 'w') as f:
        json.dump(template, f, indent=2)
    
    print(f"✅ Template created: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Helper utilities for skill-0 format conversion and testing"
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate skill file')
    validate_parser.add_argument('file', help='Path to skill JSON file')
    
    # Convert command
    convert_parser = subparsers.add_parser('convert', help='Convert markdown to JSON')
    convert_parser.add_argument('input', help='Input markdown file')
    convert_parser.add_argument('output', help='Output JSON file')
    
    # Template command
    template_parser = subparsers.add_parser('template', help='Generate skill template')
    template_parser.add_argument('--output', '-o', default='template.json', 
                                 help='Output file path')
    
    # Test command
    test_parser = subparsers.add_parser('test', help='Test skill execution paths')
    test_parser.add_argument('file', help='Path to skill JSON file')
    test_parser.add_argument('--analyze', '-a', action='store_true',
                            help='Also analyze complexity')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Execute command
    if args.command == 'validate':
        validator = SkillValidator()
        if validator.validate(args.file):
            print(f"✅ {args.file} is valid")
        else:
            validator.print_results()
            sys.exit(1)
    
    elif args.command == 'convert':
        converter = SkillConverter()
        converter.markdown_to_json(args.input, args.output)
    
    elif args.command == 'template':
        generate_template(args.output)
    
    elif args.command == 'test':
        tester = SkillTester(args.file)
        tester.test_execution_paths()
        if args.analyze:
            print()
            tester.analyze_complexity()


if __name__ == '__main__':
    main()
