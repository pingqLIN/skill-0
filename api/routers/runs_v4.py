"""Runtime governance run read API."""
from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3
from typing import Any, Iterator, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from runtime.evidence import build_run_evidence
from runtime.executor import ActionResult
from runtime.governance import (
    RuntimeGovernanceGate,
    SQLiteRuntimeGovernanceGate,
)
from runtime.ledger import RuntimeLedger
from runtime.models import RunStatus, RuntimeEventType
from runtime.orchestrator import RuntimeOrchestrator
from runtime.recovery import RecoveryCoordinator
from runtime.rules import UnavailableRuleEvaluator
from runtime.validators import RuntimeContractValidationError, load_json, validate_schema

RUNTIME_DB_PATH_ENV = "SKILL0_RUNTIME_DB_PATH"
RUNTIME_BINDING_KEY_ENV = "SKILL0_RUNTIME_BINDING_KEY"
RUNTIME_DECISION_ACTORS_ENV = "SKILL0_RUNTIME_DECISION_ACTORS"
GOVERNANCE_DB_PATH_ENV = "SKILL0_GOVERNANCE_DB_PATH"
DEFAULT_RUNTIME_DB_PATH = Path("governance/db/runtime.db")
DEFAULT_GOVERNANCE_DB_PATH = Path("governance/db/governance.db")
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
    hitl_item_id: str | None = None


class ResumeRunRequest(BaseModel):
    """Candidate material is accepted only to recompute the stored keyed basis."""

    model_config = ConfigDict(extra="forbid")

    runtime_contract: dict[str, Any]
    parameters: dict[str, Any] = Field(default_factory=dict)
    dry_run: Literal[True] = True


class HitlDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["approve", "reject", "confirm_recovered"]
    reason_code: str = Field(pattern=r"^[A-Z][A-Z0-9_]{1,63}$")


class RecoverRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dry_run: Literal[True] = True


class RecoverRunResponse(BaseModel):
    run_id: str
    status: str
    hitl_item_id: str | None = None


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

    def compensate(
        self,
        action_id: str,
        parameters: dict[str, Any],
        *,
        idempotency_key: str,
        dry_run: bool,
    ) -> ActionResult:
        del parameters, idempotency_key
        if not dry_run:
            raise RuntimeError("simulation adapter refuses real compensation")
        return ActionResult(
            success=True,
            outputs={"action_id": action_id, "compensated": True, "dry_run": True},
        )


def get_runtime_db_path() -> Path:
    return Path(os.getenv(RUNTIME_DB_PATH_ENV, str(DEFAULT_RUNTIME_DB_PATH)))


def get_runtime_binding_key() -> str:
    key = os.getenv(RUNTIME_BINDING_KEY_ENV, "")
    issue = runtime_binding_key_configuration_issue(
        key,
        jwt_secret_key=os.getenv("JWT_SECRET_KEY", ""),
    )
    if issue is not None:
        raise HTTPException(
            status_code=503,
            detail="Runtime approval binding is not configured",
        )
    return key


def runtime_binding_key_configuration_issue(
    key: str | None,
    *,
    jwt_secret_key: str | None,
) -> str | None:
    value = key or ""
    normalized = value.strip().lower()
    if len(value) < 32:
        return "SKILL0_RUNTIME_BINDING_KEY must contain at least 32 characters"
    if normalized.startswith(("change_me", "change-me")):
        return "SKILL0_RUNTIME_BINDING_KEY must not use a placeholder"
    if jwt_secret_key and value == jwt_secret_key:
        return "SKILL0_RUNTIME_BINDING_KEY must be independent from JWT_SECRET_KEY"
    return None


def authorize_runtime_decision_actor(actor: str) -> None:
    allowed = {
        value.strip()
        for value in os.getenv(RUNTIME_DECISION_ACTORS_ENV, "").split(",")
        if value.strip()
    }
    if not allowed:
        raise HTTPException(
            status_code=503,
            detail="Runtime decision authorization is not configured",
        )
    if actor not in allowed:
        raise HTTPException(
            status_code=403,
            detail="Authenticated principal cannot decide Runtime HITL items",
        )


def get_runtime_ledger() -> Iterator[RuntimeLedger]:
    with RuntimeLedger(get_runtime_db_path()) as ledger:
        yield ledger


def get_runtime_governance_gate() -> RuntimeGovernanceGate:
    return SQLiteRuntimeGovernanceGate(
        Path(
            os.getenv(
                GOVERNANCE_DB_PATH_ENV,
                str(DEFAULT_GOVERNANCE_DB_PATH),
            )
        )
    )


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


def _public_hitl_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        key: item[key]
        for key in (
            "item_id",
            "run_id",
            "skill_id",
            "action_id",
            "kind",
            "status",
            "request_summary",
            "created_at",
            "updated_at",
        )
    }


def _pending_hitl_item(ledger: RuntimeLedger, run_id: str) -> dict[str, Any] | None:
    items = ledger.list_hitl_items(status="pending", run_id=run_id)
    return items[-1] if items else None


def _response_from_result(ledger: RuntimeLedger, result: Any) -> CreateRunResponse:
    pending = _pending_hitl_item(ledger, result.run_id)
    return CreateRunResponse(
        run_id=result.run_id,
        status=result.status.value,
        reason=result.reason,
        output_summary={
            action_id: sorted(value)
            for action_id, value in result.outputs.items()
        },
        hitl_item_id=pending["item_id"] if pending else None,
    )


@router.post("", response_model=CreateRunResponse, status_code=201)
def create_run(
    request: CreateRunRequest,
    ledger: RuntimeLedger = Depends(get_runtime_ledger),
    governance_gate: RuntimeGovernanceGate = Depends(get_runtime_governance_gate),
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
        binding_key=get_runtime_binding_key(),
        governance_gate=governance_gate,
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

    return _response_from_result(ledger, result)


@router.get("/hitl/items")
def list_hitl_items(
    status: Literal["pending", "approved", "rejected", "confirmed"] | None = Query(
        default=None
    ),
    run_id: str | None = Query(default=None, min_length=1),
    limit: int = Query(default=100, ge=1, le=500),
    ledger: RuntimeLedger = Depends(get_runtime_reader),
) -> list[dict[str, Any]]:
    return [
        _public_hitl_item(item)
        for item in ledger.list_hitl_items(
            status=status, run_id=run_id, limit=limit
        )
    ]


@router.get("/hitl/items/{item_id}/decisions")
def list_hitl_decisions(
    item_id: str,
    ledger: RuntimeLedger = Depends(get_runtime_reader),
) -> list[dict[str, Any]]:
    try:
        ledger.get_hitl_item(item_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="HITL item not found") from exc
    return ledger.list_hitl_decisions(item_id)


@router.post("/hitl/items/{item_id}/decision")
def decide_hitl_item(
    item_id: str,
    decision: HitlDecisionRequest,
    request: Request,
    ledger: RuntimeLedger = Depends(get_runtime_ledger),
) -> dict[str, Any]:
    principal = getattr(request.state, "auth_user", None)
    actor = principal.get("sub") if isinstance(principal, dict) else None
    if not isinstance(actor, str) or not actor:
        raise HTTPException(status_code=401, detail="Authenticated principal is unavailable")
    authorize_runtime_decision_actor(actor)
    try:
        item = ledger.decide_hitl_item(
            item_id=item_id,
            decision=decision.decision,
            actor=actor,
            reason_code=decision.reason_code,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="HITL item not found") from exc
    except (sqlite3.IntegrityError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _public_hitl_item(item)


@router.post("/hitl/items/{item_id}/resume", response_model=CreateRunResponse)
def resume_hitl_run(
    item_id: str,
    request: ResumeRunRequest,
    ledger: RuntimeLedger = Depends(get_runtime_ledger),
    governance_gate: RuntimeGovernanceGate = Depends(get_runtime_governance_gate),
) -> CreateRunResponse:
    try:
        item = ledger.get_hitl_item(item_id)
        run = ledger.get_run(item["run_id"])
        basis = ledger.get_execution_basis(item["run_id"])
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="HITL item or run not found") from exc
    if item["kind"] != "action_approval" or item["status"] != "approved":
        raise HTTPException(status_code=409, detail="HITL item is not an approved action")
    if run["status"] != RunStatus.READY.value:
        raise HTTPException(status_code=409, detail="Runtime run is not ready to resume")
    if item["basis_digest"] != basis["execution_digest"]:
        raise HTTPException(status_code=409, detail="HITL item basis does not match run")

    skill_document = load_canonical_skill(item["skill_id"])
    orchestrator = RuntimeOrchestrator(
        ledger,
        SimulationAdapter(),
        UnavailableRuleEvaluator(),
        binding_key=get_runtime_binding_key(),
        governance_gate=governance_gate,
    )
    try:
        result = orchestrator.run(
            request.runtime_contract,
            skill_document,
            parameters=request.parameters,
            context={},
            dry_run=True,
            existing_run_id=item["run_id"],
            resume_item_id=item_id,
        )
    except (RuntimeContractValidationError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _response_from_result(ledger, result)


@router.post("/{run_id}/recover", response_model=RecoverRunResponse)
def recover_run(
    run_id: str,
    request: RecoverRunRequest,
    ledger: RuntimeLedger = Depends(get_runtime_ledger),
) -> RecoverRunResponse:
    del request
    try:
        status = RecoveryCoordinator(ledger, SimulationAdapter()).recover(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    item: dict[str, Any] | None = None
    if status == RunStatus.HITL_REQUIRED:
        item = _pending_hitl_item(ledger, run_id)
    return RecoverRunResponse(
        run_id=run_id,
        status=status.value,
        hitl_item_id=item["item_id"] if item else None,
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
        idempotency_key = data.pop("idempotency_key", None)
        data["idempotency_key_present"] = idempotency_key is not None
        source_payload = dict(data.get("payload", {}))
        allowed_keys = {
            "dry_run",
            "action_count",
            "contract_schema_version",
            "schema_validated",
            "skill_schema_validated",
            "cross_references_validated",
            "skill_identity_validated",
            "governance_validated",
            "precondition_rule_ids",
            "effect_classification",
            "resource_kind",
            "operation",
            "output_keys",
            "error_code",
            "error_message_present",
            "rule_id",
            "validated_rule_ids",
            "failed_action_id",
            "source_action_id",
            "attempt",
            "max_attempts",
            "acceptable_error",
            "completed_attempt",
            "next_attempt",
            "strategy",
            "decision",
            "actor",
            "reason_code",
            "hitl_item_id",
        }
        payload = {
            key: source_payload[key]
            for key in allowed_keys
            if key in source_payload
        }
        compensation = source_payload.get("compensation")
        if isinstance(compensation, dict) and isinstance(
            compensation.get("strategy"), str
        ):
            payload["compensation_strategy"] = compensation["strategy"]
        governance = source_payload.get("governance_attestation")
        if isinstance(governance, dict):
            payload["governance_revision_id"] = governance.get("revision_id")
            payload["governance_policy"] = governance.get("policy")
        recovery_parameters = source_payload.get("resolved_compensation_parameters")
        if isinstance(recovery_parameters, dict):
            payload["resolved_compensation_parameter_keys"] = sorted(
                recovery_parameters
            )
        data["payload"] = payload
        public_events.append(data)
    return public_events
