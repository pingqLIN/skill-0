"""Runtime governance run read API."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Iterator

from fastapi import APIRouter, Depends, HTTPException

from runtime.ledger import RuntimeLedger

RUNTIME_DB_PATH_ENV = "SKILL0_RUNTIME_DB_PATH"
DEFAULT_RUNTIME_DB_PATH = Path("governance/db/runtime.db")

router = APIRouter(prefix="/api/runs", tags=["runtime-v4"])


def get_runtime_db_path() -> Path:
    return Path(os.getenv(RUNTIME_DB_PATH_ENV, str(DEFAULT_RUNTIME_DB_PATH)))


def get_runtime_ledger() -> Iterator[RuntimeLedger]:
    with RuntimeLedger(get_runtime_db_path()) as ledger:
        yield ledger


@router.get("/{run_id}")
def get_run(run_id: str, ledger: RuntimeLedger = Depends(get_runtime_ledger)) -> dict[str, object]:
    try:
        return ledger.get_run(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc


@router.get("/{run_id}/events")
def get_events(
    run_id: str,
    ledger: RuntimeLedger = Depends(get_runtime_ledger),
) -> list[dict[str, object]]:
    try:
        ledger.get_run(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc
    return [event.to_dict() for event in ledger.list_events(run_id)]
