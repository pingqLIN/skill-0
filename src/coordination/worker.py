"""
Worker implementation for distributed skill processing.

Inspired by Agent-Lightning's Runner architecture.
"""

import asyncio
import time
import logging
from typing import Optional, Any, Dict
from pathlib import Path

from .store import SkillStore

logger = logging.getLogger(__name__)


class SkillWorker:
    """
    Worker that processes parsing tasks from the SkillStore.
    
    Similar to Agent-Lightning's Runner but adapted for skill parsing.
    """
    
    def __init__(
        self, 
        worker_id: str, 
        store: SkillStore,
        parser: Optional[Any] = None
    ):
        """
        Initialize worker.
        
        Args:
            worker_id: Unique worker identifier
            store: SkillStore instance for coordination
            parser: Parser instance (will use default if None)
        """
        self.worker_id = worker_id
        self.store = store
        self.parser = parser
        self.is_running = False
        self._heartbeat_task = None
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeats to the store."""
        while self.is_running:
            try:
                await self.store.worker_heartbeat(self.worker_id)
                await asyncio.sleep(30)  # Heartbeat every 30 seconds
            except Exception as e:
                logger.error(f"Heartbeat error for worker {self.worker_id}: {e}")
    
    async def run(self, max_tasks: Optional[int] = None):
        """
        Main worker loop.
        
        Args:
            max_tasks: Maximum number of tasks to process (None = unlimited)
        """
        self.is_running = True
        await self.store.register_worker(self.worker_id)
        
        # Start heartbeat
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        
        logger.info(f"Worker {self.worker_id} started")
        
        tasks_processed = 0
        
        try:
            while self.is_running:
                # Check if we've hit the max task limit
                if max_tasks is not None and tasks_processed >= max_tasks:
                    logger.info(
                        f"Worker {self.worker_id} reached max tasks ({max_tasks})"
                    )
                    break
                
                # Get next task
                task = await self.store.get_task(self.worker_id)
                
                if task is None:
                    # No tasks available, short sleep
                    await asyncio.sleep(0.1)
                    continue
                
                # Process task
                start_time = time.time()
                try:
                    result = await self._process_task(task)
                    duration = time.time() - start_time
                    
                    metrics = {
                        'duration_seconds': duration,
                        'worker_id': self.worker_id,
                        'task_type': task['type']
                    }
                    
                    await self.store.report_result(
                        task['id'], 
                        result, 
                        metrics=metrics
                    )
                    await self.store.complete_worker_task(self.worker_id)
                    
                    tasks_processed += 1
                    logger.info(
                        f"Worker {self.worker_id} completed task {task['id']} "
                        f"in {duration:.2f}s"
                    )
                    
                except Exception as e:
                    logger.exception(
                        f"Worker {self.worker_id} error processing task {task['id']}"
                    )
                    await self.store.report_error(task['id'], str(e))
        
        finally:
            self.is_running = False
            if self._heartbeat_task:
                self._heartbeat_task.cancel()
            logger.info(
                f"Worker {self.worker_id} stopped after processing "
                f"{tasks_processed} tasks"
            )
    
    async def _process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single task.
        
        Args:
            task: Task dictionary from store
            
        Returns:
            Parsed skill result
        """
        task_type = task['type']
        skill_path = task['path']
        
        if task_type == 'parse':
            return await self._parse_skill(skill_path)
        elif task_type == 'validate':
            return await self._validate_skill(skill_path)
        elif task_type == 'analyze':
            return await self._analyze_skill(skill_path)
        else:
            raise ValueError(f"Unknown task type: {task_type}")
    
    async def _parse_skill(self, skill_path: str) -> Dict[str, Any]:
        """
        Parse a skill file.
        
        Args:
            skill_path: Path to skill file
            
        Returns:
            Parsed skill data
        """
        if self.parser is None:
            # Import default parser if none provided
            from ..tools.advanced_skill_analyzer import SkillAnalyzer
            self.parser = SkillAnalyzer()
        
        # Run parser (in thread pool if synchronous)
        result = await asyncio.to_thread(
            self.parser.analyze_skill,
            skill_path
        )
        
        return result
    
    async def _validate_skill(self, skill_path: str) -> Dict[str, Any]:
        """
        Validate a skill file.
        
        Args:
            skill_path: Path to skill file
            
        Returns:
            Validation result
        """
        from ..tools.helper import validate_skill
        
        result = await asyncio.to_thread(validate_skill, skill_path)
        return {
            'valid': result.get('valid', False),
            'errors': result.get('errors', [])
        }
    
    async def _analyze_skill(self, skill_path: str) -> Dict[str, Any]:
        """
        Analyze skill complexity and metrics.
        
        Args:
            skill_path: Path to skill file
            
        Returns:
            Analysis result
        """
        # Placeholder for future analysis functionality
        return {
            'path': skill_path,
            'analyzed': True
        }
    
    async def stop(self):
        """Stop the worker gracefully."""
        logger.info(f"Stopping worker {self.worker_id}")
        self.is_running = False
