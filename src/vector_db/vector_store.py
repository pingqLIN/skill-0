"""
Vector Store - SQLite-vec 向量資料庫封裝
"""

import sqlite3
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import numpy as np

try:
    import sqlite_vec
    SQLITE_VEC_AVAILABLE = True
except ImportError:
    SQLITE_VEC_AVAILABLE = False


class VectorStore:
    """SQLite-vec 向量資料庫封裝"""
    
    def __init__(self, db_path: Union[str, Path] = 'skills.db', dimension: int = 384):
        """
        初始化向量資料庫
        
        Args:
            db_path: 資料庫檔案路徑
            dimension: 向量維度 (預設 384 for all-MiniLM-L6-v2)
        """
        if not SQLITE_VEC_AVAILABLE:
            raise ImportError("sqlite-vec not installed. Run: pip install sqlite-vec")
            
        self.db_path = Path(db_path)
        self.dimension = dimension
        self.conn = None
        self._connect()
        
    def _connect(self):
        """建立資料庫連線並載入 sqlite-vec 擴充"""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.enable_load_extension(True)
        sqlite_vec.load(self.conn)
        self.conn.enable_load_extension(False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()
        
    def _init_schema(self):
        """初始化資料庫 schema"""
        # 技能元資料表
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS skills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                filename TEXT UNIQUE NOT NULL,
                description TEXT,
                category TEXT,
                version TEXT,
                action_count INTEGER,
                rule_count INTEGER,
                directive_count INTEGER,
                raw_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 向量索引表 (使用 vec0 虛擬表)
        self.conn.execute(f'''
            CREATE VIRTUAL TABLE IF NOT EXISTS skill_embeddings
            USING vec0(embedding FLOAT[{self.dimension}])
        ''')
        
        # 技能間連結表（借鑑 Obsidian resolvedLinks）
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS skill_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_skill_id TEXT NOT NULL,
                target_skill_id TEXT NOT NULL,
                link_type TEXT NOT NULL,
                description TEXT,
                strength REAL DEFAULT 0.5,
                bidirectional BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(source_skill_id, target_skill_id, link_type)
            )
        ''')
        
        # 建立索引
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_skills_name ON skills(name)')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_skills_category ON skills(category)')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_skill_links_source ON skill_links(source_skill_id)')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_skill_links_target ON skill_links(target_skill_id)')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_skill_links_type ON skill_links(link_type)')
        
        self.conn.commit()
        
    def insert_skill(self, skill: Dict, embedding: np.ndarray) -> int:
        """
        插入單個 skill 及其向量
        
        Args:
            skill: skill 字典 (v2.0 格式)
            embedding: 向量 (numpy array)
            
        Returns:
            skill_id: 插入的 skill ID
        """
        filename = skill.get('_filename', 'unknown.json')
        meta = skill.get('meta', {})
        decomp = skill.get('decomposition', {})
        
        # 檢查是否已存在
        existing = self.conn.execute(
            'SELECT id FROM skills WHERE filename = ?', (filename,)
        ).fetchone()
        
        name = meta.get('title') or meta.get('name', '')
        description = meta.get('description', '')
        category = meta.get('skill_layer', '')
        version = meta.get('schema_version', '')
        action_count = len(decomp.get('actions', []))
        rule_count = len(decomp.get('rules', []))
        directive_count = len(decomp.get('directives', []))
        
        if existing:
            # 更新現有記錄
            skill_id = existing['id']
            self.conn.execute('''
                UPDATE skills SET
                    name = ?, description = ?, category = ?, version = ?,
                    action_count = ?, rule_count = ?, directive_count = ?,
                    raw_json = ?
                WHERE id = ?
            ''', (
                name, description, category, version,
                action_count, rule_count, directive_count,
                json.dumps(skill, ensure_ascii=False),
                skill_id
            ))
            
            # 更新向量
            self.conn.execute(
                'UPDATE skill_embeddings SET embedding = ? WHERE rowid = ?',
                (embedding, skill_id)
            )
        else:
            # 插入新記錄
            cursor = self.conn.execute('''
                INSERT INTO skills (name, filename, description, category, version,
                                   action_count, rule_count, directive_count, raw_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                name, filename, description, category, version,
                action_count, rule_count, directive_count,
                json.dumps(skill, ensure_ascii=False)
            ))
            skill_id = cursor.lastrowid
            
            # 插入向量 (rowid 必須與 skills.id 匹配)
            self.conn.execute(
                'INSERT INTO skill_embeddings (rowid, embedding) VALUES (?, ?)',
                (skill_id, embedding)
            )
            
        self.conn.commit()
        return skill_id
    
    def insert_skills_batch(self, skills: List[Dict], embeddings: List[np.ndarray]) -> List[int]:
        """
        批次插入多個 skills
        
        Args:
            skills: skill 字典列表
            embeddings: 向量列表
            
        Returns:
            List[int]: 插入的 skill IDs
        """
        ids = []
        for skill, emb in zip(skills, embeddings):
            skill_id = self.insert_skill(skill, emb)
            ids.append(skill_id)
        return ids
    
    def search(self, query_embedding: np.ndarray, limit: int = 5) -> List[Dict]:
        """
        向量相似度搜尋
        
        Args:
            query_embedding: 查詢向量
            limit: 返回結果數量
            
        Returns:
            List[Dict]: 相似 skills 列表 (含 distance 分數)
        """
        # sqlite-vec 需要使用 k=? 語法進行 KNN 查詢
        results = self.conn.execute('''
            SELECT 
                s.id, s.name, s.filename, s.description, s.category,
                s.action_count, s.rule_count, s.directive_count,
                e.distance
            FROM skill_embeddings e
            JOIN skills s ON e.rowid = s.id
            WHERE e.embedding MATCH ? AND k = ?
            ORDER BY e.distance
        ''', (query_embedding, limit)).fetchall()
        
        return [dict(r) for r in results]
    
    def search_by_category(self, category: str, limit: int = 10) -> List[Dict]:
        """按類別搜尋 skills"""
        results = self.conn.execute('''
            SELECT id, name, filename, description, category,
                   action_count, rule_count, directive_count
            FROM skills
            WHERE category = ?
            LIMIT ?
        ''', (category, limit)).fetchall()
        
        return [dict(r) for r in results]
    
    def get_all_skills(self) -> List[Dict]:
        """取得所有 skills 的基本資訊"""
        results = self.conn.execute('''
            SELECT id, name, filename, description, category,
                   action_count, rule_count, directive_count
            FROM skills
            ORDER BY name
        ''').fetchall()
        
        return [dict(r) for r in results]
    
    def get_skill_by_id(self, skill_id: int, include_json: bool = False) -> Optional[Dict]:
        """根據 ID 取得 skill"""
        if include_json:
            result = self.conn.execute(
                'SELECT * FROM skills WHERE id = ?', (skill_id,)
            ).fetchone()
        else:
            result = self.conn.execute('''
                SELECT id, name, filename, description, category,
                       action_count, rule_count, directive_count
                FROM skills WHERE id = ?
            ''', (skill_id,)).fetchone()
            
        return dict(result) if result else None
    
    def get_embedding(self, skill_id: int) -> Optional[np.ndarray]:
        """取得 skill 的向量"""
        result = self.conn.execute(
            'SELECT embedding FROM skill_embeddings WHERE rowid = ?',
            (skill_id,)
        ).fetchone()
        
        if result:
            return np.frombuffer(result['embedding'], dtype=np.float32)
        return None
    
    def get_statistics(self) -> Dict:
        """取得資料庫統計"""
        stats = {}
        
        # 總數
        stats['total_skills'] = self.conn.execute(
            'SELECT COUNT(*) FROM skills'
        ).fetchone()[0]
        
        # 類別分布
        categories = self.conn.execute('''
            SELECT category, COUNT(*) as count
            FROM skills
            GROUP BY category
            ORDER BY count DESC
        ''').fetchall()
        stats['categories'] = {r['category'] or 'uncategorized': r['count'] for r in categories}
        
        # 元素統計
        totals = self.conn.execute('''
            SELECT 
                SUM(action_count) as actions,
                SUM(rule_count) as rules,
                SUM(directive_count) as directives
            FROM skills
        ''').fetchone()
        stats['total_actions'] = totals['actions'] or 0
        stats['total_rules'] = totals['rules'] or 0
        stats['total_directives'] = totals['directives'] or 0
        
        # 連結統計
        stats['total_links'] = self.conn.execute(
            'SELECT COUNT(*) FROM skill_links'
        ).fetchone()[0]
        
        return stats
    
    def delete_skill(self, skill_id: int) -> bool:
        """刪除 skill"""
        self.conn.execute('DELETE FROM skill_embeddings WHERE rowid = ?', (skill_id,))
        result = self.conn.execute('DELETE FROM skills WHERE id = ?', (skill_id,))
        self.conn.commit()
        return result.rowcount > 0
    
    # ==================== Skill Links (借鑑 Obsidian 雙向連結) ====================
    
    # 反向連結類型映射
    REVERSE_LINK_TYPES = {
        'depends_on': 'depended_by',
        'extends': 'extended_by',
        'parent_of': 'child_of',
        'derived_from': 'derivative_of',
        'composes_with': 'composes_with',
        'alternative_to': 'alternative_to',
        'related_to': 'related_to',
    }
    
    def add_skill_link(
        self,
        source_skill_id: str,
        target_skill_id: str,
        link_type: str,
        description: str = None,
        strength: float = 0.5,
        bidirectional: bool = False
    ) -> int:
        """
        新增技能間連結（借鑑 Obsidian Internal Links）
        
        Args:
            source_skill_id: 來源技能 ID
            target_skill_id: 目標技能 ID
            link_type: 連結類型
            description: 關係說明
            strength: 關係強度 (0-1)
            bidirectional: 是否為雙向連結
            
        Returns:
            int: 連結記錄 ID
        """
        VALID_LINK_TYPES = [
            'depends_on', 'extends', 'composes_with',
            'alternative_to', 'related_to', 'derived_from', 'parent_of'
        ]
        if link_type not in VALID_LINK_TYPES:
            raise ValueError(f"Invalid link_type '{link_type}'. Must be one of: {VALID_LINK_TYPES}")
        
        cursor = self.conn.execute('''
            INSERT OR REPLACE INTO skill_links 
                (source_skill_id, target_skill_id, link_type, description, strength, bidirectional)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (source_skill_id, target_skill_id, link_type, description, strength, bidirectional))
        
        self.conn.commit()
        return cursor.lastrowid
    
    def get_skill_links(self, skill_id: str) -> List[Dict]:
        """
        取得技能的所有出站連結
        
        Args:
            skill_id: 技能識別碼
            
        Returns:
            List[Dict]: 出站連結列表
        """
        results = self.conn.execute('''
            SELECT id, source_skill_id, target_skill_id, link_type,
                   description, strength, bidirectional, created_at
            FROM skill_links
            WHERE source_skill_id = ?
            ORDER BY link_type, target_skill_id
        ''', (skill_id,)).fetchall()
        
        return [dict(r) for r in results]
    
    def get_skill_backlinks(self, skill_id: str) -> List[Dict]:
        """
        取得技能的反向連結（借鑑 Obsidian Backlinks）
        
        包含：
        1. 直接指向此技能的連結
        2. 雙向連結的反向關係（自動反轉 link_type）
        
        Args:
            skill_id: 技能識別碼
            
        Returns:
            List[Dict]: 反向連結列表
        """
        # 直接指向此技能的連結
        direct = self.conn.execute('''
            SELECT source_skill_id AS linked_from, link_type,
                   description, strength
            FROM skill_links
            WHERE target_skill_id = ?
        ''', (skill_id,)).fetchall()
        
        # 雙向連結的反向（此技能為 source 且標記為 bidirectional）
        reverse = self.conn.execute('''
            SELECT target_skill_id AS linked_from, link_type,
                   description, strength
            FROM skill_links
            WHERE source_skill_id = ? AND bidirectional = 1
        ''', (skill_id,)).fetchall()
        
        backlinks = []
        for r in direct:
            d = dict(r)
            d['direction'] = 'incoming'
            backlinks.append(d)
        
        for r in reverse:
            d = dict(r)
            d['direction'] = 'bidirectional_reverse'
            # 反轉連結類型
            d['link_type'] = self.REVERSE_LINK_TYPES.get(d['link_type'], d['link_type'])
            backlinks.append(d)
        
        return backlinks
    
    def get_all_links(self) -> List[Dict]:
        """取得所有技能連結"""
        results = self.conn.execute('''
            SELECT id, source_skill_id, target_skill_id, link_type,
                   description, strength, bidirectional, created_at
            FROM skill_links
            ORDER BY source_skill_id, link_type
        ''').fetchall()
        
        return [dict(r) for r in results]
    
    def delete_skill_link(self, link_id: int) -> bool:
        """刪除特定連結"""
        result = self.conn.execute('DELETE FROM skill_links WHERE id = ?', (link_id,))
        self.conn.commit()
        return result.rowcount > 0
    
    def delete_skill_links_by_skill(self, skill_id: str) -> int:
        """刪除與某技能相關的所有連結"""
        result = self.conn.execute('''
            DELETE FROM skill_links 
            WHERE source_skill_id = ? OR target_skill_id = ?
        ''', (skill_id, skill_id))
        self.conn.commit()
        return result.rowcount
    
    def get_graph_data(self) -> Dict:
        """
        取得技能關係圖譜資料（借鑑 Obsidian Graph View）
        
        回傳 nodes + edges 格式，適用於力導向圖視覺化
        
        Returns:
            Dict: {nodes: [...], edges: [...], stats: {...}}
        """
        # 節點：所有技能
        skills = self.get_all_skills()
        links = self.get_all_links()
        
        # 計算每個技能的連結數量（用於節點大小）
        link_counts = {}
        for link in links:
            src = link['source_skill_id']
            tgt = link['target_skill_id']
            link_counts[src] = link_counts.get(src, 0) + 1
            link_counts[tgt] = link_counts.get(tgt, 0) + 1
        
        # 建立節點列表
        nodes = []
        linked_skill_ids = set()
        for link in links:
            linked_skill_ids.add(link['source_skill_id'])
            linked_skill_ids.add(link['target_skill_id'])
        
        for skill in skills:
            skill_id = skill.get('filename', '').replace('.json', '')
            nodes.append({
                'id': skill_id,
                'name': skill['name'],
                'category': skill.get('category', ''),
                'link_count': link_counts.get(skill_id, 0),
                'action_count': skill.get('action_count', 0),
                'rule_count': skill.get('rule_count', 0),
                'directive_count': skill.get('directive_count', 0),
            })
        
        # 建立邊列表
        edges = []
        for link in links:
            edges.append({
                'source': link['source_skill_id'],
                'target': link['target_skill_id'],
                'link_type': link['link_type'],
                'strength': link['strength'],
                'bidirectional': bool(link['bidirectional']),
            })
        
        # 統計
        orphan_count = sum(1 for n in nodes if n['link_count'] == 0)
        
        return {
            'nodes': nodes,
            'edges': edges,
            'stats': {
                'total_nodes': len(nodes),
                'total_edges': len(edges),
                'orphan_nodes': orphan_count,
                'link_type_distribution': self._get_link_type_distribution(),
            }
        }
    
    def _get_link_type_distribution(self) -> Dict[str, int]:
        """取得連結類型分布"""
        results = self.conn.execute('''
            SELECT link_type, COUNT(*) as count
            FROM skill_links
            GROUP BY link_type
            ORDER BY count DESC
        ''').fetchall()
        return {r['link_type']: r['count'] for r in results}
    
    def get_skill_moc(self) -> Dict:
        """
        生成技能 Map of Content（借鑑 Obsidian MOC 模式）
        
        按類別組織技能，並附加連結統計資訊
        
        Returns:
            Dict: MOC 結構化索引
        """
        skills = self.get_all_skills()
        links = self.get_all_links()
        
        # 計算連結統計
        link_counts = {}
        for link in links:
            src = link['source_skill_id']
            tgt = link['target_skill_id']
            link_counts[src] = link_counts.get(src, 0) + 1
            link_counts[tgt] = link_counts.get(tgt, 0) + 1
        
        # 按類別分組
        categories = {}
        for skill in skills:
            cat = skill.get('category') or 'uncategorized'
            if cat not in categories:
                categories[cat] = {
                    'category': cat,
                    'skills': [],
                    'total_actions': 0,
                    'total_rules': 0,
                    'total_directives': 0,
                    'total_links': 0,
                }
            
            skill_id = skill.get('filename', '').replace('.json', '')
            skill_link_count = link_counts.get(skill_id, 0)
            
            categories[cat]['skills'].append({
                'name': skill['name'],
                'skill_id': skill_id,
                'description': skill.get('description', ''),
                'action_count': skill.get('action_count', 0),
                'rule_count': skill.get('rule_count', 0),
                'directive_count': skill.get('directive_count', 0),
                'link_count': skill_link_count,
            })
            categories[cat]['total_actions'] += skill.get('action_count', 0)
            categories[cat]['total_rules'] += skill.get('rule_count', 0)
            categories[cat]['total_directives'] += skill.get('directive_count', 0)
            categories[cat]['total_links'] += skill_link_count
        
        # 排序：按技能數量降序
        sorted_categories = sorted(
            categories.values(),
            key=lambda c: len(c['skills']),
            reverse=True
        )
        
        return {
            'categories': sorted_categories,
            'summary': {
                'total_skills': len(skills),
                'total_categories': len(categories),
                'total_links': len(links),
                'orphan_skills': sum(
                    1 for s in skills
                    if link_counts.get(s.get('filename', '').replace('.json', ''), 0) == 0
                ),
            }
        }
    
    def get_link_statistics(self) -> Dict:
        """取得連結統計"""
        total_links = self.conn.execute('SELECT COUNT(*) FROM skill_links').fetchone()[0]
        bidirectional = self.conn.execute(
            'SELECT COUNT(*) FROM skill_links WHERE bidirectional = 1'
        ).fetchone()[0]
        
        return {
            'total_links': total_links,
            'bidirectional_links': bidirectional,
            'unidirectional_links': total_links - bidirectional,
            'link_type_distribution': self._get_link_type_distribution(),
        }
    
    def clear(self):
        """清空資料庫"""
        self.conn.execute('DELETE FROM skill_embeddings')
        self.conn.execute('DELETE FROM skills')
        self.conn.execute('DELETE FROM skill_links')
        self.conn.commit()
        
    def close(self):
        """關閉資料庫連線"""
        if self.conn:
            self.conn.close()
            self.conn = None
            
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


if __name__ == '__main__':
    # 測試
    import tempfile
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
        
    store = VectorStore(db_path)
    
    # 測試插入
    test_skill = {
        'name': 'Test Skill',
        'description': 'A test skill',
        'category': 'test',
        '_filename': 'test-skill.json',
        'actions': [{'id': 'a1'}],
        'rules': [],
        'directives': [{'id': 'd1'}]
    }
    test_embedding = np.random.randn(384).astype(np.float32)
    
    skill_id = store.insert_skill(test_skill, test_embedding)
    print(f"Inserted skill with ID: {skill_id}")
    
    # 測試統計
    stats = store.get_statistics()
    print(f"Statistics: {stats}")
    
    store.close()
    print("VectorStore test passed!")
