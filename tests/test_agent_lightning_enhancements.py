"""
Tests for Agent-Lightning inspired enhancements.
"""

import asyncio
import pytest
from pathlib import Path
import sys
import tempfile
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from coordination import SkillStore, SkillWorker
from parsers import SkillParser, AdvancedSkillParser


class TestSkillStore:
    """Test the SkillStore coordination layer."""
    
    @pytest.mark.asyncio
    async def test_enqueue_task(self):
        """Test enqueuing a task."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            store = SkillStore(db_path=db_path)
            task_id = await store.enqueue_parse_task(
                skill_path="/test/skill.json",
                task_type="parse"
            )
            
            assert task_id is not None
            assert len(task_id) > 0
        finally:
            Path(db_path).unlink(missing_ok=True)
    
    @pytest.mark.asyncio
    async def test_get_progress(self):
        """Test getting progress statistics."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            store = SkillStore(db_path=db_path)
            
            # Enqueue some tasks
            await store.enqueue_parse_task("/test/skill1.json")
            await store.enqueue_parse_task("/test/skill2.json")
            
            progress = await store.get_progress()
            
            assert progress['total'] == 2
            assert 'queued' in progress
        finally:
            Path(db_path).unlink(missing_ok=True)


class TestAdvancedSkillParser:
    """Test the AdvancedSkillParser."""
    
    def test_parser_initialization(self):
        """Test parser can be initialized."""
        parser = AdvancedSkillParser()
        assert parser is not None
        assert parser.get_name() == "AdvancedSkillParser"
    
    def test_parser_capabilities(self):
        """Test parser reports correct capabilities."""
        parser = AdvancedSkillParser()
        capabilities = parser.get_capabilities()
        
        assert 'parse' in capabilities
        assert 'validate' in capabilities
    
    @pytest.mark.asyncio
    async def test_parse_json_skill(self):
        """Test parsing a simple JSON skill file."""
        # Create a temporary skill file
        skill_data = {
            "meta": {
                "skill_id": "test__skill",
                "name": "Test Skill",
                "version": "1.0.0"
            },
            "decomposition": {
                "actions": [],
                "rules": [],
                "directives": []
            }
        }
        
        with tempfile.NamedTemporaryFile(
            mode='w', 
            suffix='.json', 
            delete=False
        ) as f:
            json.dump(skill_data, f)
            skill_path = f.name
        
        try:
            parser = AdvancedSkillParser()
            result = await parser.parse(skill_path)
            
            assert result is not None
            assert 'meta' in result
            assert result['meta']['name'] == "Test Skill"
        finally:
            Path(skill_path).unlink(missing_ok=True)
    
    def test_validate_skill(self):
        """Test skill validation."""
        parser = AdvancedSkillParser()
        
        # Valid skill
        valid_skill = {
            "meta": {
                "skill_id": "test__skill",
                "name": "Test Skill",
                "version": "1.0.0"
            },
            "decomposition": {
                "actions": [{
                    "id": "a_001",
                    "name": "Test Action",
                    "action_type": "transform"
                }],
                "rules": [],
                "directives": []
            }
        }
        
        assert parser.validate(valid_skill) is True
        
        # Invalid skill (missing meta)
        invalid_skill = {
            "decomposition": {}
        }
        
        assert parser.validate(invalid_skill) is False


class TestSkillWorker:
    """Test the SkillWorker."""
    
    @pytest.mark.asyncio
    async def test_worker_registration(self):
        """Test worker can register with store."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            store = SkillStore(db_path=db_path)
            worker = SkillWorker("test-worker", store)
            
            await store.register_worker(worker.worker_id)
            
            # Worker should be registered
            assert worker.worker_id == "test-worker"
        finally:
            Path(db_path).unlink(missing_ok=True)
    
    @pytest.mark.asyncio
    async def test_worker_process_task(self):
        """Test worker can process a task."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        # Create a test skill file
        skill_data = {
            "meta": {
                "skill_id": "test__skill",
                "name": "Test Skill",
                "version": "1.0.0"
            },
            "decomposition": {
                "actions": [],
                "rules": [],
                "directives": []
            }
        }
        
        with tempfile.NamedTemporaryFile(
            mode='w', 
            suffix='.json', 
            delete=False
        ) as f:
            json.dump(skill_data, f)
            skill_path = f.name
        
        try:
            store = SkillStore(db_path=db_path)
            parser = AdvancedSkillParser()
            worker = SkillWorker("test-worker", store, parser)
            
            # Enqueue task
            task_id = await store.enqueue_parse_task(skill_path)
            
            # Run worker for one task with timeout
            try:
                await asyncio.wait_for(
                    worker.run(max_tasks=1), 
                    timeout=10.0
                )
            except asyncio.TimeoutError:
                await worker.stop()
            
            # Check result
            result = store.get_result(task_id)
            assert result is not None
            assert result['result'] is not None
            assert result['error'] is None
            
        finally:
            Path(db_path).unlink(missing_ok=True)
            Path(skill_path).unlink(missing_ok=True)


class TestIntegration:
    """Integration tests for the full system."""
    
    @pytest.mark.asyncio
    async def test_distributed_parsing(self):
        """Test distributed parsing with multiple workers."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        # Create test skill files
        skill_files = []
        for i in range(4):
            skill_data = {
                "meta": {
                    "skill_id": f"test__skill_{i}",
                    "name": f"Test Skill {i}",
                    "version": "1.0.0"
                },
                "decomposition": {
                    "actions": [],
                    "rules": [],
                    "directives": []
                }
            }
            
            with tempfile.NamedTemporaryFile(
                mode='w', 
                suffix='.json', 
                delete=False
            ) as f:
                json.dump(skill_data, f)
                skill_files.append(f.name)
        
        try:
            store = SkillStore(db_path=db_path)
            parser = AdvancedSkillParser()
            
            # Enqueue all tasks
            task_ids = []
            for skill_file in skill_files:
                task_id = await store.enqueue_parse_task(skill_file)
                task_ids.append(task_id)
            
            # Create 2 workers
            workers = [
                SkillWorker(f"worker-{i}", store, parser)
                for i in range(2)
            ]
            
            # Run workers with timeout
            worker_tasks = [
                asyncio.create_task(worker.run(max_tasks=2))
                for worker in workers
            ]
            
            try:
                await asyncio.wait_for(
                    asyncio.gather(*worker_tasks),
                    timeout=20.0
                )
            except asyncio.TimeoutError:
                for worker in workers:
                    await worker.stop()
            
            # Check all tasks completed
            progress = await store.get_progress()
            assert progress['completed'] == 4
            assert progress['total'] == 4
            
            # Check all results are available
            for task_id in task_ids:
                result = store.get_result(task_id)
                assert result is not None
                assert result['result'] is not None
            
        finally:
            Path(db_path).unlink(missing_ok=True)
            for skill_file in skill_files:
                Path(skill_file).unlink(missing_ok=True)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
