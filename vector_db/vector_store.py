"""
Vector Store - SQLite-vec vector database wrapper
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
    """SQLite-vec vector database wrapper"""
    
    def __init__(self, db_path: Union[str, Path] = 'skills.db', dimension: int = 384):
        """
        Initialize vector database
        
        Args:
            db_path: Database file path
            dimension: Vector dimension (default 384 for all-MiniLM-L6-v2)
        """
        if not SQLITE_VEC_AVAILABLE:
            raise ImportError("sqlite-vec not installed. Run: pip install sqlite-vec")
            
        self.db_path = Path(db_path)
        self.dimension = dimension
        self.conn = None
        self._connect()
        
    def _connect(self):
        """Establish database connection and load sqlite-vec extension"""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.enable_load_extension(True)
        sqlite_vec.load(self.conn)
        self.conn.enable_load_extension(False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()
        
    def _init_schema(self):
        """Initialize database schema"""
        # Skill metadata table
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
        
        # Vector index table (using vec0 virtual table)
        self.conn.execute(f'''
            CREATE VIRTUAL TABLE IF NOT EXISTS skill_embeddings
            USING vec0(embedding FLOAT[{self.dimension}])
        ''')
        
        # Create indexes
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_skills_name ON skills(name)')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_skills_category ON skills(category)')
        
        self.conn.commit()
        
    def insert_skill(self, skill: Dict, embedding: np.ndarray) -> int:
        """
        Insert a single skill with its vector
        
        Args:
            skill: Skill dictionary (v2.0 format)
            embedding: Vector (numpy array)
            
        Returns:
            skill_id: ID of inserted skill
        """
        filename = skill.get('_filename', 'unknown.json')
        meta = skill.get('meta', {})
        decomp = skill.get('decomposition', {})
        
        # Check if already exists
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
            # Update existing record
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
            
            # Update vector
            self.conn.execute(
                'UPDATE skill_embeddings SET embedding = ? WHERE rowid = ?',
                (embedding, skill_id)
            )
        else:
            # Insert new record
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
            
            # Insert vector (rowid must match skills.id)
            self.conn.execute(
                'INSERT INTO skill_embeddings (rowid, embedding) VALUES (?, ?)',
                (skill_id, embedding)
            )
            
        self.conn.commit()
        return skill_id
    
    def insert_skills_batch(self, skills: List[Dict], embeddings: List[np.ndarray]) -> List[int]:
        """
        Batch insert multiple skills
        
        Args:
            skills: List of skill dictionaries
            embeddings: List of vectors
            
        Returns:
            List[int]: List of inserted skill IDs
        """
        ids = []
        for skill, emb in zip(skills, embeddings):
            skill_id = self.insert_skill(skill, emb)
            ids.append(skill_id)
        return ids
    
    def search(self, query_embedding: np.ndarray, limit: int = 5) -> List[Dict]:
        """
        Vector similarity search
        
        Args:
            query_embedding: Query vector
            limit: Number of results to return
            
        Returns:
            List[Dict]: List of similar skills (with distance scores)
        """
        # sqlite-vec requires k=? syntax for KNN queries
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
        """Search skills by category"""
        results = self.conn.execute('''
            SELECT id, name, filename, description, category,
                   action_count, rule_count, directive_count
            FROM skills
            WHERE category = ?
            LIMIT ?
        ''', (category, limit)).fetchall()
        
        return [dict(r) for r in results]
    
    def get_all_skills(self) -> List[Dict]:
        """Get basic information of all skills"""
        results = self.conn.execute('''
            SELECT id, name, filename, description, category,
                   action_count, rule_count, directive_count
            FROM skills
            ORDER BY name
        ''').fetchall()
        
        return [dict(r) for r in results]
    
    def get_skill_by_id(self, skill_id: int, include_json: bool = False) -> Optional[Dict]:
        """Get skill by ID"""
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
        """Get skill's vector"""
        result = self.conn.execute(
            'SELECT embedding FROM skill_embeddings WHERE rowid = ?',
            (skill_id,)
        ).fetchone()
        
        if result:
            return np.frombuffer(result['embedding'], dtype=np.float32)
        return None
    
    def get_statistics(self) -> Dict:
        """Get database statistics"""
        stats = {}
        
        # Total count
        stats['total_skills'] = self.conn.execute(
            'SELECT COUNT(*) FROM skills'
        ).fetchone()[0]
        
        # Category distribution
        categories = self.conn.execute('''
            SELECT category, COUNT(*) as count
            FROM skills
            GROUP BY category
            ORDER BY count DESC
        ''').fetchall()
        stats['categories'] = {r['category'] or 'uncategorized': r['count'] for r in categories}
        
        # Element statistics
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
        """Delete skill"""
        self.conn.execute('DELETE FROM skill_embeddings WHERE rowid = ?', (skill_id,))
        result = self.conn.execute('DELETE FROM skills WHERE id = ?', (skill_id,))
        self.conn.commit()
        return result.rowcount > 0
    
    def clear(self):
        """Clear database"""
        self.conn.execute('DELETE FROM skill_embeddings')
        self.conn.execute('DELETE FROM skills')
        self.conn.commit()
        
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None
            
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


if __name__ == '__main__':
    # Test
    import tempfile
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
        
    store = VectorStore(db_path)
    
    # Test insert
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
    
    # Test statistics
    stats = store.get_statistics()
    print(f"Statistics: {stats}")
    
    store.close()
    print("VectorStore test passed!")
