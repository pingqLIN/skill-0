"""
Example: Distributed Skill Parsing

Demonstrates the new coordination layer and worker pool inspired by Agent-Lightning.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from coordination import SkillStore, SkillWorker
from parsers import AdvancedSkillParser


async def distributed_parse_example():
    """
    Example of distributed skill parsing using the coordination layer.
    
    This demonstrates the Agent-Lightning inspired architecture:
    - SkillStore acts as the central coordination hub (like LightningStore)
    - Multiple workers process tasks in parallel (like Runners)
    - Tasks are queued and distributed automatically
    """
    
    print("=" * 60)
    print("Distributed Skill Parsing Example")
    print("Inspired by Microsoft Agent-Lightning Architecture")
    print("=" * 60)
    print()
    
    # Initialize the coordination store
    print("1. Initializing SkillStore (central coordination hub)...")
    store = SkillStore(db_path="db/coordination_example.db")
    print("   ✓ Store initialized\n")
    
    # Find some skills to parse
    print("2. Finding skills to parse...")
    data_dir = Path(__file__).parent.parent / 'data' / 'parsed'
    skill_files = list(data_dir.glob('*.json'))[:10]  # Limit to 10 for demo
    print(f"   ✓ Found {len(skill_files)} skills\n")
    
    # Enqueue tasks
    print("3. Enqueuing parse tasks...")
    task_ids = []
    for skill_file in skill_files:
        task_id = await store.enqueue_parse_task(
            str(skill_file),
            task_type='parse'
        )
        task_ids.append(task_id)
    print(f"   ✓ Enqueued {len(task_ids)} tasks\n")
    
    # Create worker pool
    print("4. Starting worker pool (4 workers)...")
    num_workers = 4
    parser = AdvancedSkillParser()
    workers = [
        SkillWorker(f"worker-{i}", store, parser)
        for i in range(num_workers)
    ]
    print(f"   ✓ Created {num_workers} workers\n")
    
    # Run workers with progress reporting
    print("5. Processing tasks in parallel...\n")
    
    # Create worker tasks
    worker_tasks = [
        asyncio.create_task(worker.run(max_tasks=3))
        for worker in workers
    ]
    
    # Progress monitoring task
    async def monitor_progress():
        while True:
            progress = await store.get_progress()
            print(f"\r   Progress: {progress['completed']}/{progress['total']} "
                  f"tasks (In Progress: {progress.get('in_progress', 0)}, "
                  f"Failed: {progress.get('failed', 0)})", end='')
            
            # Check if all tasks are done
            if progress['completed'] + progress.get('failed', 0) >= progress['total']:
                print()  # New line
                break
            
            await asyncio.sleep(0.5)
    
    # Run workers and monitor
    monitor_task = asyncio.create_task(monitor_progress())
    await asyncio.gather(*worker_tasks)
    await monitor_task
    
    print("\n6. All workers completed!\n")
    
    # Show final statistics
    print("=" * 60)
    print("Final Statistics")
    print("=" * 60)
    final_stats = await store.get_progress()
    print(f"Total tasks:     {final_stats['total']}")
    print(f"Completed:       {final_stats['completed']}")
    print(f"Failed:          {final_stats.get('failed', 0)}")
    print(f"Success rate:    {final_stats['completed']/final_stats['total']*100:.1f}%")
    print()
    
    # Show sample results
    print("Sample Results:")
    print("-" * 60)
    for i, task_id in enumerate(task_ids[:3]):
        result = store.get_result(task_id)
        if result:
            if result['error']:
                print(f"Task {i+1}: ERROR - {result['error']}")
            else:
                skill_name = result['result'].get('meta', {}).get('name', 'Unknown')
                duration = result['metrics'].get('duration_seconds', 0)
                print(f"Task {i+1}: {skill_name} (parsed in {duration:.2f}s)")
    print()


async def sequential_vs_parallel_comparison():
    """
    Compare sequential (old way) vs parallel (new way) processing.
    """
    print("\n" + "=" * 60)
    print("Sequential vs Parallel Comparison")
    print("=" * 60)
    print()
    
    data_dir = Path(__file__).parent.parent / 'data' / 'parsed'
    skill_files = list(data_dir.glob('*.json'))[:8]
    
    # Sequential processing (old way)
    print("Sequential Processing (Old Way):")
    print("-" * 60)
    import time
    start_time = time.time()
    
    parser = AdvancedSkillParser()
    for skill_file in skill_files:
        try:
            await parser.parse(str(skill_file))
        except Exception as e:
            pass
    
    sequential_time = time.time() - start_time
    print(f"Time taken: {sequential_time:.2f}s")
    print()
    
    # Parallel processing (new way)
    print("Parallel Processing (New Way with 4 Workers):")
    print("-" * 60)
    start_time = time.time()
    
    store = SkillStore(db_path="db/coordination_comparison.db")
    
    # Enqueue tasks
    for skill_file in skill_files:
        await store.enqueue_parse_task(str(skill_file))
    
    # Create workers
    workers = [
        SkillWorker(f"worker-{i}", store, parser)
        for i in range(4)
    ]
    
    # Run workers
    worker_tasks = [
        asyncio.create_task(worker.run(max_tasks=2))
        for worker in workers
    ]
    await asyncio.gather(*worker_tasks)
    
    parallel_time = time.time() - start_time
    print(f"Time taken: {parallel_time:.2f}s")
    print()
    
    # Show speedup
    speedup = sequential_time / parallel_time if parallel_time > 0 else 0
    print(f"Speedup: {speedup:.2f}x faster with parallel processing!")
    print()


async def main():
    """Main entry point."""
    try:
        # Run distributed parsing example
        await distributed_parse_example()
        
        # Run comparison
        # await sequential_vs_parallel_comparison()
        
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    asyncio.run(main())
