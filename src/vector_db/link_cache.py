"""
Skill Link Cache - 技能連結快取（借鑑 Obsidian MetadataCache）

提供記憶體快取機制，加速技能間連結關係的查詢
"""

import time
from typing import Dict, List, Optional


class SkillLinkCache:
    """
    技能連結快取（借鑑 Obsidian MetadataCache 概念）
    
    提供：
    - 連結關係的記憶體快取
    - TTL 過期機制
    - 快取失效（invalidation）
    - 命中率統計
    """
    
    def __init__(self, ttl_seconds: int = 300):
        """
        初始化快取
        
        Args:
            ttl_seconds: 快取存活時間（秒），預設 5 分鐘
        """
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Dict] = {}
        self._timestamps: Dict[str, float] = {}
        self._hits = 0
        self._misses = 0
    
    def _make_key(self, prefix: str, skill_id: str) -> str:
        """生成快取鍵"""
        return f"{prefix}:{skill_id}"
    
    def _is_expired(self, key: str) -> bool:
        """檢查是否已過期"""
        if key not in self._timestamps:
            return True
        return (time.time() - self._timestamps[key]) > self.ttl_seconds
    
    def _evict(self, key: str):
        """清除過期的快取項目"""
        self._cache.pop(key, None)
        self._timestamps.pop(key, None)
    
    def get_links(self, skill_id: str) -> Optional[List[Dict]]:
        """取得快取中的出站連結"""
        key = self._make_key('links', skill_id)
        if key in self._cache:
            if not self._is_expired(key):
                self._hits += 1
                return self._cache[key]
            self._evict(key)
        self._misses += 1
        return None
    
    def set_links(self, skill_id: str, links: List[Dict]):
        """設定出站連結快取"""
        key = self._make_key('links', skill_id)
        self._cache[key] = links
        self._timestamps[key] = time.time()
    
    def get_backlinks(self, skill_id: str) -> Optional[List[Dict]]:
        """取得快取中的反向連結"""
        key = self._make_key('backlinks', skill_id)
        if key in self._cache:
            if not self._is_expired(key):
                self._hits += 1
                return self._cache[key]
            self._evict(key)
        self._misses += 1
        return None
    
    def set_backlinks(self, skill_id: str, backlinks: List[Dict]):
        """設定反向連結快取"""
        key = self._make_key('backlinks', skill_id)
        self._cache[key] = backlinks
        self._timestamps[key] = time.time()
    
    def get_graph(self) -> Optional[Dict]:
        """取得快取中的圖譜資料"""
        key = 'graph:all'
        if key in self._cache:
            if not self._is_expired(key):
                self._hits += 1
                return self._cache[key]
            self._evict(key)
        self._misses += 1
        return None
    
    def set_graph(self, graph_data: Dict):
        """設定圖譜資料快取"""
        key = 'graph:all'
        self._cache[key] = graph_data
        self._timestamps[key] = time.time()
    
    def get_moc(self) -> Optional[Dict]:
        """取得快取中的 MOC 資料"""
        key = 'moc:all'
        if key in self._cache:
            if not self._is_expired(key):
                self._hits += 1
                return self._cache[key]
            self._evict(key)
        self._misses += 1
        return None
    
    def set_moc(self, moc_data: Dict):
        """設定 MOC 資料快取"""
        key = 'moc:all'
        self._cache[key] = moc_data
        self._timestamps[key] = time.time()
    
    def invalidate(self, skill_id: str = None):
        """
        失效快取
        
        Args:
            skill_id: 指定技能 ID 失效其相關快取；若為 None 則清空全部
        """
        if skill_id is None:
            self._cache.clear()
            self._timestamps.clear()
        else:
            # 失效該技能的直接快取
            for prefix in ['links', 'backlinks']:
                key = self._make_key(prefix, skill_id)
                self._cache.pop(key, None)
                self._timestamps.pop(key, None)
            # 全域快取也失效
            for key in ['graph:all', 'moc:all']:
                self._cache.pop(key, None)
                self._timestamps.pop(key, None)
    
    def get_stats(self) -> Dict:
        """取得快取統計"""
        total = self._hits + self._misses
        return {
            'hits': self._hits,
            'misses': self._misses,
            'hit_rate': self._hits / total if total > 0 else 0.0,
            'cached_entries': len(self._cache),
            'ttl_seconds': self.ttl_seconds,
        }
