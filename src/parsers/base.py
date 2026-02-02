"""
Base parser abstraction for skill processing.

Provides a unified interface for different parsing strategies.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
import json


class SkillParser(ABC):
    """
    Abstract base class for skill parsers.
    
    Inspired by Agent-Lightning's algorithm abstraction pattern.
    All parsers must implement this interface to ensure consistency.
    """
    
    @abstractmethod
    async def parse(self, skill_path: str) -> Dict[str, Any]:
        """
        Parse skill into decomposition format.
        
        Args:
            skill_path: Path to skill file
            
        Returns:
            Parsed skill dictionary in decomposition format
            
        Raises:
            ParseError: If parsing fails
        """
        pass
    
    @abstractmethod
    def validate(self, parsed_skill: Dict[str, Any]) -> bool:
        """
        Validate parsed skill against schema.
        
        Args:
            parsed_skill: Parsed skill dictionary
            
        Returns:
            True if valid, False otherwise
        """
        pass
    
    def get_name(self) -> str:
        """
        Get parser name.
        
        Returns:
            Parser name
        """
        return self.__class__.__name__
    
    def get_capabilities(self) -> List[str]:
        """
        Get list of parser capabilities.
        
        Returns:
            List of capability strings
        """
        return ['parse', 'validate']
    
    async def batch_parse(
        self, 
        skill_paths: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Parse multiple skills.
        
        Args:
            skill_paths: List of skill file paths
            
        Returns:
            List of parsed skill dictionaries
        """
        results = []
        for path in skill_paths:
            try:
                result = await self.parse(path)
                results.append(result)
            except Exception as e:
                results.append({
                    'error': str(e),
                    'path': path
                })
        return results


class ParseError(Exception):
    """Exception raised when parsing fails."""
    pass
