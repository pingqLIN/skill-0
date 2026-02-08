"""
Skill-0 Vector Database Module
Stage 2: 向量化索引與語義搜尋
Stage 3: 技能間連結與知識圖譜（借鑑 Obsidian）
"""

from .vector_store import VectorStore
from .link_cache import SkillLinkCache

try:
    from .embedder import SkillEmbedder
    from .search import SemanticSearch
except ImportError:
    SkillEmbedder = None
    SemanticSearch = None

__all__ = ['VectorStore', 'SkillEmbedder', 'SemanticSearch', 'SkillLinkCache']
__version__ = '0.2.0'
