"""Generic Asset search projections and bounded async execution."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from functools import partial
from typing import Any, Callable, TypeVar


T = TypeVar("T")


@dataclass(frozen=True)
class AssetSearchResult:
    asset_id: str
    revision_id: str
    asset_type: str
    name: str
    description: str | None
    source_path: str
    distance: float
    similarity: float


class SearchOverloadedError(RuntimeError):
    code = "search_capacity_exhausted"


class BoundedSearchExecutor:
    """Two workers plus a bounded queue; capacity follows actual thread lifetime."""

    def __init__(
        self,
        *,
        max_workers: int = 2,
        queue_capacity: int = 4,
        acquire_timeout_seconds: float = 0.2,
    ):
        self.max_workers = max_workers
        self.queue_capacity = queue_capacity
        self.acquire_timeout_seconds = acquire_timeout_seconds
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="skill0-search",
        )
        self._capacity: asyncio.Semaphore | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    def _semaphore(self) -> asyncio.Semaphore:
        loop = asyncio.get_running_loop()
        if self._capacity is None or self._loop is not loop:
            self._loop = loop
            self._capacity = asyncio.Semaphore(self.max_workers + self.queue_capacity)
        return self._capacity

    async def run(self, function: Callable[..., T], /, *args: Any, **kwargs: Any) -> T:
        semaphore = self._semaphore()
        try:
            await asyncio.wait_for(
                semaphore.acquire(), timeout=self.acquire_timeout_seconds
            )
        except TimeoutError as exc:
            raise SearchOverloadedError(SearchOverloadedError.code) from exc

        loop = asyncio.get_running_loop()
        future = loop.run_in_executor(self._executor, partial(function, *args, **kwargs))

        def release_capacity(_future) -> None:
            loop.call_soon_threadsafe(semaphore.release)

        future.add_done_callback(release_capacity)
        return await asyncio.shield(future)

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)
