"""
Central coordination store for skill processing tasks.

Inspired by Agent-Lightning's LightningStore architecture.
"""

import asyncio
import sqlite3
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class SkillStore:
    """
    Central coordination hub for skill operations.
    
    Manages task queues, results, and coordination between workers.
    Similar to Agent-Lightning's LightningStore but adapted for skill processing.
    """
    
    def __init__(self, db_path: str = "db/coordination.db"):
        """
        Initialize the coordination store.
        
        Args:
            db_path: Path to SQLite database for coordination
        """
        self.db_path = db_path
        self.task_queue = asyncio.Queue()
        self.results: Dict[str, Dict[str, Any]] = {}
        self._init_db()
    
    def _init_db(self):
        """Initialize coordination database with required tables."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Tasks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                task_type TEXT NOT NULL,
                skill_path TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                worker_id TEXT,
                metadata TEXT
            )
        """)
        
        # Results table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS results (
                task_id TEXT PRIMARY KEY,
                result TEXT NOT NULL,
                error TEXT,
                metrics TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (task_id) REFERENCES tasks(task_id)
            )
        """)
        
        # Workers table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workers (
                worker_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                tasks_completed INTEGER DEFAULT 0,
                last_heartbeat TEXT,
                created_at TEXT NOT NULL
            )
        """)
        
        conn.commit()
        conn.close()
    
    async def enqueue_parse_task(
        self, 
        skill_path: str, 
        task_type: str = "parse",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add skill to parsing queue.
        
        Args:
            skill_path: Path to skill file
            task_type: Type of task (parse, validate, analyze)
            metadata: Additional task metadata
            
        Returns:
            Task ID
        """
        task_id = str(uuid.uuid4())
        task = {
            'id': task_id,
            'type': task_type,
            'path': skill_path,
            'status': 'queued',
            'created_at': datetime.utcnow().isoformat(),
            'metadata': metadata or {}
        }
        
        # Add to queue
        await self.task_queue.put(task)
        
        # Persist to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO tasks 
            (task_id, task_type, skill_path, status, created_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            task_id, 
            task_type, 
            skill_path, 
            'queued',
            task['created_at'],
            json.dumps(metadata or {})
        ))
        conn.commit()
        conn.close()
        
        logger.info(f"Enqueued task {task_id}: {task_type} for {skill_path}")
        return task_id
    
    async def get_task(self, worker_id: str) -> Optional[Dict[str, Any]]:
        """
        Get next task from queue.
        
        Args:
            worker_id: ID of requesting worker
            
        Returns:
            Task dictionary or None if queue is empty
        """
        try:
            task = await asyncio.wait_for(self.task_queue.get(), timeout=1.0)
            task['status'] = 'in_progress'
            task['started_at'] = datetime.utcnow().isoformat()
            task['worker_id'] = worker_id
            
            # Update in database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE tasks 
                SET status = ?, started_at = ?, worker_id = ?
                WHERE task_id = ?
            """, ('in_progress', task['started_at'], worker_id, task['id']))
            conn.commit()
            conn.close()
            
            logger.info(f"Worker {worker_id} claimed task {task['id']}")
            return task
        except asyncio.TimeoutError:
            return None
    
    async def report_result(
        self, 
        task_id: str, 
        result: Dict[str, Any],
        metrics: Optional[Dict[str, Any]] = None
    ):
        """
        Store task result.
        
        Args:
            task_id: Task ID
            result: Parsed skill result
            metrics: Performance metrics
        """
        self.results[task_id] = result
        
        # Update database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Update task status
        cursor.execute("""
            UPDATE tasks 
            SET status = ?, completed_at = ?
            WHERE task_id = ?
        """, ('completed', datetime.utcnow().isoformat(), task_id))
        
        # Insert result
        cursor.execute("""
            INSERT INTO results (task_id, result, metrics, created_at)
            VALUES (?, ?, ?, ?)
        """, (
            task_id,
            json.dumps(result),
            json.dumps(metrics or {}),
            datetime.utcnow().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Stored result for task {task_id}")
    
    async def report_error(self, task_id: str, error: str):
        """
        Report task error.
        
        Args:
            task_id: Task ID
            error: Error message
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Update task status
        cursor.execute("""
            UPDATE tasks 
            SET status = ?, completed_at = ?
            WHERE task_id = ?
        """, ('failed', datetime.utcnow().isoformat(), task_id))
        
        # Insert error result
        cursor.execute("""
            INSERT INTO results (task_id, result, error, created_at)
            VALUES (?, ?, ?, ?)
        """, (
            task_id,
            json.dumps({}),
            error,
            datetime.utcnow().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        logger.error(f"Task {task_id} failed: {error}")
    
    async def get_progress(self) -> Dict[str, int]:
        """
        Get overall progress statistics.
        
        Returns:
            Dictionary with total, completed, failed, in_progress counts
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT status, COUNT(*) 
            FROM tasks 
            GROUP BY status
        """)
        
        stats = {
            'total': 0,
            'queued': 0,
            'in_progress': 0,
            'completed': 0,
            'failed': 0
        }
        
        for status, count in cursor.fetchall():
            stats[status] = count
            stats['total'] += count
        
        conn.close()
        return stats
    
    def get_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get result for a specific task.
        
        Args:
            task_id: Task ID
            
        Returns:
            Result dictionary or None
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT result, error, metrics
            FROM results
            WHERE task_id = ?
        """, (task_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'result': json.loads(row[0]) if row[0] else None,
                'error': row[1],
                'metrics': json.loads(row[2]) if row[2] else None
            }
        return None
    
    async def register_worker(self, worker_id: str):
        """Register a new worker."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO workers 
            (worker_id, status, created_at, last_heartbeat)
            VALUES (?, ?, ?, ?)
        """, (
            worker_id,
            'active',
            datetime.utcnow().isoformat(),
            datetime.utcnow().isoformat()
        ))
        
        conn.commit()
        conn.close()
        logger.info(f"Registered worker {worker_id}")
    
    async def worker_heartbeat(self, worker_id: str):
        """Update worker heartbeat."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE workers 
            SET last_heartbeat = ?
            WHERE worker_id = ?
        """, (datetime.utcnow().isoformat(), worker_id))
        
        conn.commit()
        conn.close()
    
    async def complete_worker_task(self, worker_id: str):
        """Increment worker task completion count."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE workers 
            SET tasks_completed = tasks_completed + 1
            WHERE worker_id = ?
        """, (worker_id,))
        
        conn.commit()
        conn.close()
