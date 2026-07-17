from __future__ import annotations

import asyncio
from threading import Event
from threading import Lock, RLock
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager, nullcontext

import numpy as np

import pytest

from asset_registry.search import BoundedSearchExecutor, SearchOverloadedError
import api.main as api_module
from vector_db.search import SemanticSearch


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


def test_api_search_similar_cluster_and_index_share_operation_lock(monkeypatch):
    class Tracker:
        def __init__(self):
            self.guard = Lock()
            self.active = 0
            self.maximum = 0

        @contextmanager
        def operation(self):
            with self.guard:
                self.active += 1
                self.maximum = max(self.maximum, self.active)
            time.sleep(0.02)
            try:
                yield
            finally:
                with self.guard:
                    self.active -= 1

    tracker = Tracker()
    skills = [
        {"id": 1, "name": "one", "_filename": "one.json"},
        {"id": 2, "name": "two", "_filename": "two.json"},
    ]

    class FakeEmbedder:
        dimension = 384

        def embed_query(self, query):
            del query
            with tracker.operation():
                return np.zeros(384, dtype=np.float32)

        def load_skills_from_dir(self, parsed_dir):
            del parsed_dir
            with tracker.operation():
                return skills

        def embed_skills(self, items, show_progress=True):
            del show_progress
            with tracker.operation():
                return [np.zeros(384, dtype=np.float32) for _ in items]

    class FakeStore:
        dimension = 384

        def search(self, embedding, limit=5):
            del embedding
            with tracker.operation():
                return [
                    {"id": item["id"], "name": item["name"], "distance": 0.0}
                    for item in skills[:limit]
                ]

        def get_all_skills(self):
            with tracker.operation():
                return skills

        def get_embedding(self, skill_id):
            del skill_id
            with tracker.operation():
                return np.zeros(384, dtype=np.float32)

        def has_asset_index_state(self):
            return False

        def insert_skills_batch(self, items, embeddings):
            del embeddings
            with tracker.operation():
                return list(range(1, len(items) + 1))

    engine = object.__new__(SemanticSearch)
    engine.model_name = "fixture"
    engine.dimension = 384
    engine._embedder = FakeEmbedder()
    engine._operation_lock = RLock()
    engine.store = FakeStore()
    engine.open_unit_of_work = lambda: nullcontext(engine)
    monkeypatch.setattr(api_module, "search_engine", engine)

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [
            pool.submit(api_module._search_sync, "one", 2),
            pool.submit(api_module._similar_sync, "one", 1),
            pool.submit(api_module._cluster_sync, 2),
            pool.submit(api_module._index_sync, "parsed"),
        ]
        for future in futures:
            future.result(timeout=30)

    assert tracker.maximum == 1
