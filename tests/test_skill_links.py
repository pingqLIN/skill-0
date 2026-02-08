"""
Test suite for Skill Links (Obsidian-inspired features)

Tests for:
- VectorStore skill_links table operations
- SkillLinkCache caching mechanism
- Bidirectional links and backlinks
- Graph data generation
- MOC (Map of Content) generation
"""

import pytest
import tempfile
import time
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

# Import directly to avoid sentence_transformers dependency in tests
from vector_db.link_cache import SkillLinkCache


# ==================== SkillLinkCache Tests ====================

class TestSkillLinkCache:
    """Test suite for SkillLinkCache (Obsidian MetadataCache inspired)"""
    
    @pytest.fixture
    def cache(self):
        """Create a cache with short TTL for testing"""
        return SkillLinkCache(ttl_seconds=2)
    
    def test_cache_initialization(self, cache):
        """Test cache initializes with correct defaults"""
        assert cache.ttl_seconds == 2
        stats = cache.get_stats()
        assert stats['hits'] == 0
        assert stats['misses'] == 0
        assert stats['cached_entries'] == 0
    
    def test_set_and_get_links(self, cache):
        """Test storing and retrieving links from cache"""
        test_links = [
            {'target_skill_id': 'skill_b', 'link_type': 'depends_on'}
        ]
        cache.set_links('skill_a', test_links)
        
        result = cache.get_links('skill_a')
        assert result is not None
        assert len(result) == 1
        assert result[0]['target_skill_id'] == 'skill_b'
    
    def test_cache_miss(self, cache):
        """Test cache miss returns None"""
        result = cache.get_links('nonexistent')
        assert result is None
        
        stats = cache.get_stats()
        assert stats['misses'] == 1
    
    def test_cache_hit_tracking(self, cache):
        """Test cache hit/miss tracking"""
        cache.set_links('skill_a', [{'test': True}])
        
        # First access = hit
        cache.get_links('skill_a')
        # Second access = hit
        cache.get_links('skill_a')
        # Miss
        cache.get_links('nonexistent')
        
        stats = cache.get_stats()
        assert stats['hits'] == 2
        assert stats['misses'] == 1
        assert stats['hit_rate'] == pytest.approx(2/3)
    
    def test_cache_ttl_expiration(self, cache):
        """Test cache entries expire after TTL"""
        cache.set_links('skill_a', [{'test': True}])
        
        # Should be in cache
        assert cache.get_links('skill_a') is not None
        
        # Wait for TTL to expire
        time.sleep(2.5)
        
        # Should be expired now
        result = cache.get_links('skill_a')
        assert result is None
    
    def test_set_and_get_backlinks(self, cache):
        """Test backlinks caching"""
        backlinks = [
            {'linked_from': 'skill_x', 'link_type': 'depends_on'}
        ]
        cache.set_backlinks('skill_a', backlinks)
        
        result = cache.get_backlinks('skill_a')
        assert result is not None
        assert len(result) == 1
    
    def test_set_and_get_graph(self, cache):
        """Test graph data caching"""
        graph = {'nodes': [{'id': 'a'}], 'edges': [], 'stats': {}}
        cache.set_graph(graph)
        
        result = cache.get_graph()
        assert result is not None
        assert len(result['nodes']) == 1
    
    def test_set_and_get_moc(self, cache):
        """Test MOC data caching"""
        moc = {'categories': [], 'summary': {'total_skills': 0}}
        cache.set_moc(moc)
        
        result = cache.get_moc()
        assert result is not None
    
    def test_invalidate_specific_skill(self, cache):
        """Test invalidating cache for a specific skill"""
        cache.set_links('skill_a', [{'test': True}])
        cache.set_backlinks('skill_a', [{'test': True}])
        cache.set_links('skill_b', [{'test': True}])
        cache.set_graph({'nodes': []})
        
        # Invalidate skill_a
        cache.invalidate('skill_a')
        
        # skill_a should be gone
        assert cache.get_links('skill_a') is None
        assert cache.get_backlinks('skill_a') is None
        
        # skill_b should still be there
        assert cache.get_links('skill_b') is not None
        
        # Global caches should be invalidated too
        assert cache.get_graph() is None
    
    def test_invalidate_all(self, cache):
        """Test clearing all cache"""
        cache.set_links('skill_a', [{'test': True}])
        cache.set_links('skill_b', [{'test': True}])
        cache.set_graph({'nodes': []})
        cache.set_moc({'categories': []})
        
        cache.invalidate()
        
        assert cache.get_links('skill_a') is None
        assert cache.get_links('skill_b') is None
        assert cache.get_graph() is None
        assert cache.get_moc() is None


# ==================== VectorStore Skill Links Tests ====================
# These tests require sqlite-vec, skip if not available

try:
    import sqlite_vec
    SQLITE_VEC_AVAILABLE = True
except ImportError:
    SQLITE_VEC_AVAILABLE = False

import numpy as np


@pytest.mark.skipif(not SQLITE_VEC_AVAILABLE, reason="sqlite-vec not installed")
class TestVectorStoreSkillLinks:
    """Test suite for VectorStore skill link operations"""
    
    @pytest.fixture
    def store(self):
        """Create a temporary VectorStore"""
        from vector_db.vector_store import VectorStore
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        store = VectorStore(db_path)
        yield store
        store.close()
    
    @pytest.fixture
    def store_with_skills(self, store):
        """Create a store with test skills"""
        for i, name in enumerate(['PDF Reader', 'File System', 'Data Transform']):
            skill = {
                'meta': {'title': name, 'skill_layer': 'claude_skill', 'schema_version': '2.3.0'},
                'decomposition': {'actions': [{'id': f'a_{i}'}], 'rules': [], 'directives': []},
                '_filename': f'skill_{i}.json',
            }
            embedding = np.random.randn(384).astype(np.float32)
            store.insert_skill(skill, embedding)
        return store
    
    def test_add_skill_link(self, store):
        """Test adding a skill link"""
        link_id = store.add_skill_link(
            source_skill_id='skill_a',
            target_skill_id='skill_b',
            link_type='depends_on',
            description='A depends on B',
            strength=0.8,
        )
        assert link_id > 0
    
    def test_add_invalid_link_type(self, store):
        """Test adding a link with invalid type raises error"""
        with pytest.raises(ValueError, match="Invalid link_type"):
            store.add_skill_link('skill_a', 'skill_b', 'invalid_type')
    
    def test_get_skill_links(self, store):
        """Test retrieving outgoing links"""
        store.add_skill_link('skill_a', 'skill_b', 'depends_on', 'test')
        store.add_skill_link('skill_a', 'skill_c', 'extends', 'test2')
        
        links = store.get_skill_links('skill_a')
        assert len(links) == 2
    
    def test_get_skill_backlinks_direct(self, store):
        """Test retrieving direct backlinks"""
        store.add_skill_link('skill_a', 'skill_b', 'depends_on')
        store.add_skill_link('skill_c', 'skill_b', 'related_to')
        
        backlinks = store.get_skill_backlinks('skill_b')
        assert len(backlinks) == 2
        linked_from = [bl['linked_from'] for bl in backlinks]
        assert 'skill_a' in linked_from
        assert 'skill_c' in linked_from
    
    def test_get_skill_backlinks_bidirectional(self, store):
        """Test bidirectional backlinks reverse link types correctly"""
        store.add_skill_link(
            'skill_a', 'skill_b', 'depends_on',
            bidirectional=True
        )
        
        # skill_b should see backlinks from skill_a
        backlinks_b = store.get_skill_backlinks('skill_b')
        assert len(backlinks_b) >= 1
        direct = [bl for bl in backlinks_b if bl['direction'] == 'incoming']
        assert len(direct) == 1
        
        # skill_a should see reverse backlink (depended_by from skill_b)
        backlinks_a = store.get_skill_backlinks('skill_a')
        reverse = [bl for bl in backlinks_a if bl['direction'] == 'bidirectional_reverse']
        assert len(reverse) == 1
        assert reverse[0]['link_type'] == 'depended_by'
    
    def test_get_all_links(self, store):
        """Test retrieving all links"""
        store.add_skill_link('skill_a', 'skill_b', 'depends_on')
        store.add_skill_link('skill_b', 'skill_c', 'extends')
        
        all_links = store.get_all_links()
        assert len(all_links) == 2
    
    def test_delete_skill_link(self, store):
        """Test deleting a specific link"""
        link_id = store.add_skill_link('skill_a', 'skill_b', 'depends_on')
        
        success = store.delete_skill_link(link_id)
        assert success is True
        
        links = store.get_skill_links('skill_a')
        assert len(links) == 0
    
    def test_delete_skill_links_by_skill(self, store):
        """Test deleting all links for a skill"""
        store.add_skill_link('skill_a', 'skill_b', 'depends_on')
        store.add_skill_link('skill_a', 'skill_c', 'extends')
        store.add_skill_link('skill_d', 'skill_a', 'related_to')
        
        count = store.delete_skill_links_by_skill('skill_a')
        assert count == 3
    
    def test_unique_constraint(self, store):
        """Test that duplicate links are replaced (UPSERT)"""
        store.add_skill_link('skill_a', 'skill_b', 'depends_on', strength=0.5)
        store.add_skill_link('skill_a', 'skill_b', 'depends_on', strength=0.9)
        
        links = store.get_skill_links('skill_a')
        assert len(links) == 1
        assert links[0]['strength'] == 0.9
    
    def test_graph_data(self, store_with_skills):
        """Test graph data generation"""
        store = store_with_skills
        store.add_skill_link('skill_0', 'skill_1', 'depends_on', strength=0.8)
        store.add_skill_link('skill_1', 'skill_2', 'composes_with', strength=0.6)
        
        graph = store.get_graph_data()
        
        assert 'nodes' in graph
        assert 'edges' in graph
        assert 'stats' in graph
        assert len(graph['nodes']) == 3
        assert len(graph['edges']) == 2
        assert graph['stats']['total_nodes'] == 3
        assert graph['stats']['total_edges'] == 2
    
    def test_graph_orphan_detection(self, store_with_skills):
        """Test orphan node detection in graph"""
        store = store_with_skills
        # Only link 2 of 3 skills
        store.add_skill_link('skill_0', 'skill_1', 'depends_on')
        
        graph = store.get_graph_data()
        assert graph['stats']['orphan_nodes'] == 1  # skill_2 is orphan
    
    def test_skill_moc(self, store_with_skills):
        """Test MOC generation"""
        store = store_with_skills
        store.add_skill_link('skill_0', 'skill_1', 'depends_on')
        
        moc = store.get_skill_moc()
        
        assert 'categories' in moc
        assert 'summary' in moc
        assert moc['summary']['total_skills'] == 3
        assert moc['summary']['total_links'] == 1
    
    def test_link_statistics(self, store):
        """Test link statistics"""
        store.add_skill_link('skill_a', 'skill_b', 'depends_on', bidirectional=True)
        store.add_skill_link('skill_a', 'skill_c', 'related_to')
        
        stats = store.get_link_statistics()
        assert stats['total_links'] == 2
        assert stats['bidirectional_links'] == 1
        assert stats['unidirectional_links'] == 1
        assert 'depends_on' in stats['link_type_distribution']
    
    def test_statistics_includes_links(self, store):
        """Test that general statistics include link count"""
        store.add_skill_link('skill_a', 'skill_b', 'depends_on')
        
        stats = store.get_statistics()
        assert 'total_links' in stats
        assert stats['total_links'] == 1
    
    def test_clear_includes_links(self, store):
        """Test that clear() also clears skill_links"""
        store.add_skill_link('skill_a', 'skill_b', 'depends_on')
        store.clear()
        
        links = store.get_all_links()
        assert len(links) == 0
    
    def test_all_valid_link_types(self, store):
        """Test all 7 valid link types can be used"""
        valid_types = [
            'depends_on', 'extends', 'composes_with',
            'alternative_to', 'related_to', 'derived_from', 'parent_of'
        ]
        for i, lt in enumerate(valid_types):
            store.add_skill_link(f'skill_a', f'skill_{i}', lt)
        
        links = store.get_skill_links('skill_a')
        assert len(links) == 7
    
    def test_reverse_link_type_mapping(self, store):
        """Test that reverse link types are correctly mapped"""
        mappings = {
            'depends_on': 'depended_by',
            'extends': 'extended_by',
            'parent_of': 'child_of',
            'derived_from': 'derivative_of',
            'composes_with': 'composes_with',  # symmetric
            'alternative_to': 'alternative_to',  # symmetric
            'related_to': 'related_to',  # symmetric
        }
        
        for link_type, expected_reverse in mappings.items():
            assert store.REVERSE_LINK_TYPES[link_type] == expected_reverse
