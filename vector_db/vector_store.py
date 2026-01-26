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
        
        # 建立索引
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_skills_name ON skills(name)')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_skills_category ON skills(category)')
        
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
        
        return stats
    
    def delete_skill(self, skill_id: int) -> bool:
        """刪除 skill"""
        self.conn.execute('DELETE FROM skill_embeddings WHERE rowid = ?', (skill_id,))
        result = self.conn.execute('DELETE FROM skills WHERE id = ?', (skill_id,))
        self.conn.commit()
        return result.rowcount > 0
    
    def clear(self):
        """清空資料庫"""
        self.conn.execute('DELETE FROM skill_embeddings')
        self.conn.execute('DELETE FROM skills')
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
