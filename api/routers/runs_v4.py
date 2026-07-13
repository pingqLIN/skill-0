"""Integration skeleton only.

Codex must adapt imports, auth dependencies, rate limiting, logging, and error
models to the current repository discovered in Phase 0 before registering this router.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from runtime.executor import RuntimeExecutor
from runtime.ledger import RuntimeLedger

router = APIRouter(prefix="/api/runs", tags=["runtime-v4"])


class CreateRunRequest(BaseModel):
    contract: dict[str, Any]
    parameters: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)
    dry_run: bool = True


@router.get("/{run_id}")
def get_run(run_id: str) -> dict[str, Any]:
    with RuntimeLedger(Path("runtime.db")) as ledger:
        try:
            return ledger.get_run(run_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Run not found") from exc


@router.get("/{run_id}/events")
def get_events(run_id: str) -> list[dict[str, Any]]:
    with RuntimeLedger(Path("runtime.db")) as ledger:
        try:
            ledger.get_run(run_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Run not found") from exc
        return [event.to_dict() for event in ledger.list_events(run_id)]


# POST is intentionally not wired to a real adapter in the scaffold.
# Phase 0 must identify the repository's dependency-injection and auth conventions.
