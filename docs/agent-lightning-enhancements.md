# Agent-Lightning Inspired Enhancements

This directory contains new features inspired by Microsoft's [Agent-Lightning](https://github.com/microsoft/agent-lightning) project.

## Overview

We've integrated key architectural patterns from Agent-Lightning to enhance Skill-0's capabilities:

1. **Coordination Layer** - Central hub for distributed task management
2. **Parser Abstraction** - Unified interface for different parsing strategies  
3. **Worker Pool** - Parallel execution of skill processing tasks

## New Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────┐
│   Parser    │────▶│  SkillStore  │◀────│ Worker  │
│(Algorithm)  │     │   (Central)  │     │(Runner) │
└─────────────┘     └──────────────┘     └─────────┘
      ▲                                        │
      │                                        │
      └────────── Results & Metrics ──────────┘
```

Similar to Agent-Lightning's architecture:
- **Parser** = Algorithm (decides how to parse)
- **SkillStore** = LightningStore (coordinates tasks)
- **Worker** = Runner (executes tasks)

## Components

### 1. Coordination Layer (`src/coordination/`)

**SkillStore** - Central coordination hub:
- Task queue management
- Result storage
- Worker coordination
- Progress tracking
- SQLite-based persistence

**SkillWorker** - Parallel task processor:
- Pulls tasks from SkillStore
- Executes parsing operations
- Reports results and metrics
- Automatic heartbeat monitoring

### 2. Parser Abstraction (`src/parsers/`)

**SkillParser (Base Class)** - Abstract interface:
- `parse()` - Parse skill into decomposition format
- `validate()` - Validate against schema
- `batch_parse()` - Process multiple skills
- Extensible for new parsing strategies

**AdvancedSkillParser** - Wraps existing SkillAnalyzer:
- Async interface
- Error handling
- Thread pool execution
- Fallback to simple JSON parsing

## Usage

### Basic Distributed Parsing

```python
import asyncio
from src.coordination import SkillStore, SkillWorker
from src.parsers import AdvancedSkillParser

async def parse_skills():
    # Initialize coordination store
    store = SkillStore(db_path="db/coordination.db")
    
    # Enqueue tasks
    for skill_path in skill_files:
        await store.enqueue_parse_task(skill_path)
    
    # Create worker pool
    parser = AdvancedSkillParser()
    workers = [
        SkillWorker(f"worker-{i}", store, parser)
        for i in range(4)  # 4 parallel workers
    ]
    
    # Run workers
    await asyncio.gather(*[w.run() for w in workers])
    
    # Check progress
    progress = await store.get_progress()
    print(f"Completed: {progress['completed']}/{progress['total']}")

asyncio.run(parse_skills())
```

### Run the Example

```bash
cd examples
python distributed_parsing.py
```

Expected output:
```
============================================================
Distributed Skill Parsing Example
Inspired by Microsoft Agent-Lightning Architecture
============================================================

1. Initializing SkillStore (central coordination hub)...
   ✓ Store initialized

2. Finding skills to parse...
   ✓ Found 10 skills

3. Enqueuing parse tasks...
   ✓ Enqueued 10 tasks

4. Starting worker pool (4 workers)...
   ✓ Created 4 workers

5. Processing tasks in parallel...
   Progress: 10/10 tasks (In Progress: 0, Failed: 0)

6. All workers completed!

============================================================
Final Statistics
============================================================
Total tasks:     10
Completed:       10
Failed:          0
Success rate:    100.0%
```

## Benefits

### 1. Parallel Processing
- **4x faster** with 4 workers (for I/O-bound tasks)
- Better resource utilization
- Scalable to more workers

### 2. Distributed Coordination
- Multiple machines can share work
- Fault tolerance (workers can fail independently)
- Real-time progress tracking

### 3. Extensible Parsers
- Easy to add new parsing strategies
- A/B test different approaches
- Community contributions welcome

### 4. Monitoring & Observability
- Task-level metrics (duration, worker_id)
- Progress statistics
- Worker health monitoring (heartbeats)

## Comparison with Agent-Lightning

| Feature | Agent-Lightning | Skill-0 Enhancement |
|---------|----------------|---------------------|
| **Central Coordination** | LightningStore (FastAPI) | SkillStore (SQLite) |
| **Workers** | Runner (RL training) | SkillWorker (parsing) |
| **Algorithms** | RL/Prompt Opt/SFT | Parser strategies |
| **Data** | Traces & Rollouts | Parsed skills |
| **Scale** | Distributed (multi-GPU) | Local/Distributed |
| **Real-time** | WebSocket updates | Polling-based |

## Future Enhancements

### Phase 2: Observability (Planned)
- OpenTelemetry tracing integration
- Prometheus metrics export
- Performance dashboards
- Grafana integration

### Phase 3: Advanced Features (Planned)
- Multi-strategy parsing (ensemble methods)
- Real-time collaboration (WebSocket)
- Advanced analytics (skill graphs)
- Cloud deployment support

## Technical Details

### Database Schema

**tasks table:**
```sql
CREATE TABLE tasks (
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
```

**results table:**
```sql
CREATE TABLE results (
    task_id TEXT PRIMARY KEY,
    result TEXT NOT NULL,
    error TEXT,
    metrics TEXT,
    created_at TEXT NOT NULL
)
```

**workers table:**
```sql
CREATE TABLE workers (
    worker_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    tasks_completed INTEGER DEFAULT 0,
    last_heartbeat TEXT,
    created_at TEXT NOT NULL
)
```

### Performance Metrics

Workers automatically collect metrics:
- `duration_seconds` - Task execution time
- `worker_id` - Which worker processed the task
- `task_type` - Type of task (parse/validate/analyze)

Access metrics via:
```python
result = store.get_result(task_id)
metrics = result['metrics']
print(f"Duration: {metrics['duration_seconds']:.2f}s")
```

## References

1. [Agent-Lightning GitHub](https://github.com/microsoft/agent-lightning)
2. [Agent-Lightning Documentation](https://microsoft.github.io/agent-lightning/)
3. [Agent-Lightning Paper](https://arxiv.org/abs/2508.03680)
4. [Skill-0 Comparison Document](../docs/agent-lightning-comparison.md)

## Contributing

To add a new parser:

1. Extend `SkillParser` base class:
```python
from src.parsers.base import SkillParser

class MyParser(SkillParser):
    async def parse(self, skill_path: str) -> dict:
        # Your parsing logic
        pass
    
    def validate(self, parsed_skill: dict) -> bool:
        # Your validation logic
        pass
```

2. Register and use:
```python
from src.parsers import MyParser

parser = MyParser()
worker = SkillWorker("worker-1", store, parser)
```

---

*For detailed comparison with Agent-Lightning, see [docs/agent-lightning-comparison.md](../docs/agent-lightning-comparison.md)*
