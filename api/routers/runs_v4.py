"""Runtime governance run read API."""
from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3
from typing import Any, Iterator, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from runtime.evidence import build_run_evidence
from runtime.executor import ActionResult
from runtime.ledger import RuntimeLedger
from runtime.orchestrator import RuntimeOrchestrator
from runtime.rules import UnavailableRuleEvaluator
from runtime.validators import RuntimeContractValidationError, load_json, validate_schema

RUNTIME_DB_PATH_ENV = "SKILL0_RUNTIME_DB_PATH"
DEFAULT_RUNTIME_DB_PATH = Path("governance/db/runtime.db")
EVIDENCE_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schema" / "evidence-summary.schema.json"
RUN_EVIDENCE_SCHEMA_PATH = (
    Path(__file__).resolve().parents[2] / "schema" / "runtime-run-evidence.schema.json"
)

router = APIRouter(prefix="/api/runs", tags=["runtime-v4"])


class CreateRunRequest(BaseModel):
    """A deterministic dry-run request; external adapters are never loaded."""

    model_config = ConfigDict(extra="forbid")

    skill_id: str = Field(min_length=1, max_length=200)
    runtime_contract: dict[str, Any]
    parameters: dict[str, Any] = Field(default_factory=dict)
    dry_run: Literal[True] = True


class CreateRunResponse(BaseModel):
    run_id: str
    status: str
    reason: str | None = None
    output_summary: dict[str, list[str]] = Field(default_factory=dict)


class SimulationAdapter:
    """Non-I/O adapter used by the first write surface."""

    supports_dry_run = True

    def execute(
        self,
        action_id: str,
        parameters: dict[str, Any],
        *,
        dry_run: bool,
    ) -> ActionResult:
        del parameters
        if not dry_run:
            raise RuntimeError("simulation adapter refuses real execution")
        resource_id = f"dry-run-{action_id}"
        return ActionResult(
            success=True,
            outputs={"action_id": action_id, "dry_run": True, "id": resource_id},
            external_resource_id=resource_id,
        )


def get_runtime_db_path() -> Path:
    return Path(os.getenv(RUNTIME_DB_PATH_ENV, str(DEFAULT_RUNTIME_DB_PATH)))


def get_runtime_ledger() -> Iterator[RuntimeLedger]:
    with RuntimeLedger(get_runtime_db_path()) as ledger:
        yield ledger


def get_runtime_reader() -> Iterator[RuntimeLedger]:
    path = get_runtime_db_path()
    if not path.exists():
        raise HTTPException(status_code=404, detail="Run not found")
    try:
        with RuntimeLedger(path, read_only=True) as ledger:
            yield ledger
    except sqlite3.DatabaseError as exc:
        raise HTTPException(status_code=500, detail="Runtime ledger unavailable") from exc


def get_parsed_dir() -> Path:
    return Path(os.getenv("SKILL0_PARSED_DIR", "parsed"))


def load_canonical_skill(skill_id: str) -> dict[str, Any]:
    matches: list[dict[str, Any]] = []
    parsed_dir = get_parsed_dir()
    for path in sorted(parsed_dir.glob("*.json")):
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if document.get("meta", {}).get("skill_id") == skill_id:
            matches.append(document)
    if not matches:
        raise HTTPException(status_code=404, detail="Canonical skill not found")
    if len(matches) > 1:
        raise HTTPException(status_code=409, detail="Canonical skill identity is ambiguous")
    return matches[0]


@router.post("", response_model=CreateRunResponse, status_code=201)
def create_run(
    request: CreateRunRequest,
    ledger: RuntimeLedger = Depends(get_runtime_ledger),
) -> CreateRunResponse:
    raw_bindings = request.runtime_contract.get("action_bindings", [])
    action_bindings = raw_bindings if isinstance(raw_bindings, list) else []
    adapter_kinds: set[str] = set()
    for binding in action_bindings:
        if not isinstance(binding, dict):
            adapter_kinds.add("<malformed>")
            continue
        adapter = binding.get("adapter")
        if not isinstance(adapter, dict):
            adapter_kinds.add("<malformed>")
            continue
        if adapter.get("kind") != "test":
            adapter_kinds.add(str(adapter.get("kind")))
    disallowed_adapters = sorted(adapter_kinds)
    if disallowed_adapters:
        raise HTTPException(
            status_code=422,
            detail="Batch A accepts only test adapters for deterministic dry-run execution",
        )

    skill_document = load_canonical_skill(request.skill_id)
    orchestrator = RuntimeOrchestrator(
        ledger,
        SimulationAdapter(),
        UnavailableRuleEvaluator(),
    )
    try:
        result = orchestrator.run(
            request.runtime_contract,
            skill_document,
            parameters=request.parameters,
            context={},
            dry_run=True,
        )
    except RuntimeContractValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return CreateRunResponse(
        run_id=result.run_id,
        status=result.status.value,
        reason=result.reason,
        output_summary={
            action_id: sorted(value)
            for action_id, value in result.outputs.items()
        },
    )


@router.get("/{run_id}/evidence")
def get_evidence(
    run_id: str,
    ledger: RuntimeLedger = Depends(get_runtime_reader),
) -> dict[str, object]:
    try:
        run = ledger.get_run(run_id)
        summary = build_run_evidence(ledger.list_events(run_id), run=run)
        validate_schema(summary, load_json(EVIDENCE_SCHEMA_PATH))
        validate_schema(summary, load_json(RUN_EVIDENCE_SCHEMA_PATH))
        return summary
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc
    except (sqlite3.DatabaseError, RuntimeContractValidationError, ValueError) as exc:
        raise HTTPException(status_code=500, detail="Runtime Evidence unavailable") from exc


@router.get("/{run_id}")
def get_run(run_id: str, ledger: RuntimeLedger = Depends(get_runtime_reader)) -> dict[str, object]:
    try:
        return ledger.get_run(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc


@router.get("/{run_id}/events")
def get_events(
    run_id: str,
    ledger: RuntimeLedger = Depends(get_runtime_reader),
) -> list[dict[str, object]]:
    try:
        ledger.get_run(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc
    public_events: list[dict[str, object]] = []
    for event in ledger.list_events(run_id):
        data = event.to_dict()
        external_resource_id = data.pop("external_resource_id", None)
        data["external_resource_id_present"] = external_resource_id is not None
        payload = dict(data.get("payload", {}))
        recovery_parameters = payload.pop("resolved_compensation_parameters", None)
        if isinstance(recovery_parameters, dict):
            payload["resolved_compensation_parameter_keys"] = sorted(
                recovery_parameters
            )
        data["payload"] = payload
        public_events.append(data)
    return public_events
