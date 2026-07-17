from __future__ import annotations

import asyncio
from threading import Event
import time

import pytest

from asset_registry.search import BoundedSearchExecutor, SearchOverloadedError


def test_bounded_executor_keeps_loop_responsive_and_fails_fast_when_full():
    async def scenario():
        executor = BoundedSearchExecutor(
            max_workers=2,
            queue_capacity=4,
            acquire_timeout_seconds=0.2,
        )
        release = Event()

        def blocked_search():
            release.wait(timeout=2)
            return "done"

        tasks = [asyncio.create_task(executor.run(blocked_search)) for _ in range(6)]
        await asyncio.sleep(0.05)

        latencies = []
        for _ in range(10):
            started = time.perf_counter()
            await asyncio.sleep(0)
            latencies.append(time.perf_counter() - started)
        assert sum(latency < 0.25 for latency in latencies) >= 9

        started = time.perf_counter()
        with pytest.raises(SearchOverloadedError, match="search_capacity_exhausted"):
            await executor.run(blocked_search)
        assert time.perf_counter() - started < 0.25

        tasks[0].cancel()
        await asyncio.sleep(0)
        with pytest.raises(SearchOverloadedError):
            await executor.run(blocked_search)

        release.set()
        await asyncio.gather(*tasks, return_exceptions=True)
        executor.shutdown()

    asyncio.run(scenario())
