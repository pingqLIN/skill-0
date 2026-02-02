"""
Coordination layer for distributed skill processing.

Inspired by Agent-Lightning's LightningStore pattern.
"""

from .store import SkillStore
from .worker import SkillWorker

__all__ = ['SkillStore', 'SkillWorker']
