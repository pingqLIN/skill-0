"""
Parser abstraction layer for skill processing.

Inspired by Agent-Lightning's algorithm abstraction pattern.
"""

from .base import SkillParser
from .advanced_parser import AdvancedSkillParser

__all__ = ['SkillParser', 'AdvancedSkillParser']
