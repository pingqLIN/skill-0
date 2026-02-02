"""
Advanced parser implementation wrapping existing skill analyzer.

Adapts the existing SkillAnalyzer to the new parser interface.
"""

import asyncio
from typing import Dict, Any
from pathlib import Path
import json

from .base import SkillParser, ParseError


class AdvancedSkillParser(SkillParser):
    """
    Advanced parser wrapping the existing SkillAnalyzer.
    
    Provides async interface and error handling.
    """
    
    def __init__(self):
        """Initialize the parser."""
        self._analyzer = None
    
    def _get_analyzer(self):
        """Lazy load the analyzer to avoid import issues."""
        if self._analyzer is None:
            # Import here to avoid circular dependencies
            import sys
            from pathlib import Path
            
            # Add tools directory to path
            tools_dir = Path(__file__).parent.parent / 'tools'
            if str(tools_dir) not in sys.path:
                sys.path.insert(0, str(tools_dir))
            
            try:
                from advanced_skill_analyzer import SkillAnalyzer
                self._analyzer = SkillAnalyzer()
            except ImportError:
                # Fallback to simple parser
                self._analyzer = None
        
        return self._analyzer
    
    async def parse(self, skill_path: str) -> Dict[str, Any]:
        """
        Parse skill using the advanced analyzer.
        
        Args:
            skill_path: Path to skill file
            
        Returns:
            Parsed skill dictionary
            
        Raises:
            ParseError: If parsing fails
        """
        try:
            # Check if file exists
            if not Path(skill_path).exists():
                raise ParseError(f"Skill file not found: {skill_path}")
            
            analyzer = self._get_analyzer()
            
            if analyzer is None:
                # Fallback to simple parsing
                return await self._simple_parse(skill_path)
            
            # Run in thread pool since analyzer is synchronous
            result = await asyncio.to_thread(
                analyzer.analyze_skill,
                skill_path
            )
            
            return result
            
        except Exception as e:
            raise ParseError(f"Failed to parse {skill_path}: {str(e)}")
    
    async def _simple_parse(self, skill_path: str) -> Dict[str, Any]:
        """
        Simple fallback parser that reads JSON skills.
        
        Args:
            skill_path: Path to skill file
            
        Returns:
            Parsed skill dictionary
        """
        def _read_skill():
            with open(skill_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        return await asyncio.to_thread(_read_skill)
    
    def validate(self, parsed_skill: Dict[str, Any]) -> bool:
        """
        Validate parsed skill against schema.
        
        Args:
            parsed_skill: Parsed skill dictionary
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # Check required top-level fields
            required_fields = ['meta', 'decomposition']
            if not all(field in parsed_skill for field in required_fields):
                return False
            
            # Check meta fields
            meta = parsed_skill['meta']
            required_meta = ['skill_id', 'name', 'version']
            if not all(field in meta for field in required_meta):
                return False
            
            # Check decomposition structure
            decomp = parsed_skill['decomposition']
            if not isinstance(decomp, dict):
                return False
            
            # Validate actions if present
            if 'actions' in decomp:
                if not isinstance(decomp['actions'], list):
                    return False
                for action in decomp['actions']:
                    if not self._validate_action(action):
                        return False
            
            # Validate rules if present
            if 'rules' in decomp:
                if not isinstance(decomp['rules'], list):
                    return False
                for rule in decomp['rules']:
                    if not self._validate_rule(rule):
                        return False
            
            # Validate directives if present
            if 'directives' in decomp:
                if not isinstance(decomp['directives'], list):
                    return False
                for directive in decomp['directives']:
                    if not self._validate_directive(directive):
                        return False
            
            return True
            
        except Exception:
            return False
    
    def _validate_action(self, action: Dict[str, Any]) -> bool:
        """Validate an action structure."""
        required = ['id', 'name', 'action_type']
        return all(field in action for field in required)
    
    def _validate_rule(self, rule: Dict[str, Any]) -> bool:
        """Validate a rule structure."""
        required = ['id', 'name', 'condition_type']
        return all(field in rule for field in required)
    
    def _validate_directive(self, directive: Dict[str, Any]) -> bool:
        """Validate a directive structure."""
        required = ['id', 'directive_type', 'description']
        return all(field in directive for field in required)
    
    def get_capabilities(self) -> list:
        """Get parser capabilities."""
        return [
            'parse',
            'validate',
            'batch_parse',
            'async_execution',
            'llm_based_analysis'
        ]
