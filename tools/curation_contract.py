#!/usr/bin/env python3
"""Validation helpers for SkillOS-inspired curation sidecar contracts."""

from __future__ import annotations

import copy
import json
import math
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft7Validator, FormatChecker

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTRACT_VERSION = "1.0.0"
CONTRACT_SCHEMA_PATHS = {
    "trajectory": REPO_ROOT / "schema" / "execution-trajectory.schema.json",
    "proposal": REPO_ROOT / "schema" / "curation-proposal.schema.json",
    "evaluation": REPO_ROOT / "schema" / "evaluation-result.schema.json",
    "curator_context": REPO_ROOT / "schema" / "offline-curator-context.schema.json",
    "curator_decision": REPO_ROOT / "schema" / "offline-curator-decision.schema.json",
}

_SENSITIVE_KEYS = {
    "access_token",
    "apikey",
    "api_key",
    "authorization",
    "client_secret",
    "cookie",
    "cookies",
    "password",
    "passwd",
    "private_key",
    "refresh_token",
    "session_cookie",
}
_SENSITIVE_VALUE_PATTERNS = (
    (
        "private-key marker",
        re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"),
    ),
    ("bearer token", re.compile(r"\bBearer\s+[A-Za-z0-9._~-]{20,}\b", re.IGNORECASE)),
    ("OpenAI-style key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("GitHub-style token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("AWS access key", re.compile(r"\bAKIA[A-Z0-9]{16}\b")),
)


@dataclass(frozen=True)
class SensitiveFinding:
    """A high-confidence sensitive value or sensitive field location."""

    path: str
    reason: str


def load_contract_schema(contract_type: str) -> dict[str, Any]:
    """Load one curation contract schema by its stable type name."""
    try:
        schema_path = CONTRACT_SCHEMA_PATHS[contract_type]
    except KeyError as exc:
        valid_types = ", ".join(sorted(CONTRACT_SCHEMA_PATHS))
        raise ValueError(f"Unknown curation contract type {contract_type!r}; expected {valid_types}") from exc
    return json.loads(schema_path.read_text(encoding="utf-8"))


def build_contract_validator(contract_type: str) -> Draft7Validator:
    """Build a Draft-07 validator with date-time format checks enabled."""
    return Draft7Validator(load_contract_schema(contract_type), format_checker=FormatChecker())


def iter_contract_validation_errors(
    document: dict[str, Any],
    contract_type: str,
) -> list[Any]:
    """Return deterministically ordered JSON Schema errors."""
    validator = build_contract_validator(contract_type)
    return sorted(validator.iter_errors(document), key=lambda error: list(error.absolute_path))


def format_contract_validation_errors(errors: Iterable[Any]) -> list[str]:
    """Convert jsonschema errors to stable JSON-pointer-like messages."""
    formatted: list[str] = []
    for error in errors:
        path = "/" + "/".join(_escape_pointer_token(str(part)) for part in error.absolute_path)
        formatted.append(f"{path or '/'}: {error.message}")
    return formatted


def normalize_contract_document(
    document: dict[str, Any],
    contract_type: str,
) -> dict[str, Any]:
    """Backfill only non-sensitive structural defaults without mutating input."""
    if contract_type not in CONTRACT_SCHEMA_PATHS:
        load_contract_schema(contract_type)

    normalized = copy.deepcopy(document)
    normalized.setdefault("contract_version", CONTRACT_VERSION)

    if contract_type == "trajectory":
        normalized.setdefault("retrieved_skills", [])
        normalized.setdefault("steps", [])
        task = normalized.setdefault("task", {})
        if isinstance(task, dict):
            task.setdefault("attributes", [])
        redaction = normalized.setdefault("redaction", {})
        if isinstance(redaction, dict):
            redaction.setdefault("removed_fields", [])
    elif contract_type == "proposal":
        normalized.setdefault("retrieval_context", [])
        normalized.setdefault("supporting_trajectories", [])

    return normalized


def find_sensitive_content(value: Any, path: str = "") -> list[SensitiveFinding]:
    """Find high-confidence secret material without flagging generic security wording."""
    findings: list[SensitiveFinding] = []

    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}/{_escape_pointer_token(str(key))}"
            normalized_key = re.sub(r"[^a-z0-9]+", "_", str(key).lower()).strip("_")
            if normalized_key in _SENSITIVE_KEYS:
                findings.append(SensitiveFinding(child_path or "/", "sensitive field name"))
                continue
            findings.extend(find_sensitive_content(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(find_sensitive_content(child, f"{path}/{index}"))
    elif isinstance(value, str):
        for reason, pattern in _SENSITIVE_VALUE_PATTERNS:
            if pattern.search(value):
                findings.append(SensitiveFinding(path or "/", reason))
                break

    return findings


def validate_trajectory_semantics(document: dict[str, Any]) -> list[str]:
    """Validate ordering, timing, retrieval ranks, and redaction invariants."""
    issues: list[str] = []
    steps = document.get("steps")
    if isinstance(steps, list):
        issues.extend(_validate_contiguous_indexes(steps, "index", "steps"))
        issues.extend(_validate_monotonic_timestamps(steps, "timestamp", "steps"))

    retrieved_skills = document.get("retrieved_skills")
    if isinstance(retrieved_skills, list) and retrieved_skills:
        issues.extend(_validate_contiguous_indexes(retrieved_skills, "rank", "retrieved skill ranks"))

    run = document.get("run")
    if isinstance(run, dict):
        started_at = _parse_datetime(run.get("started_at"))
        completed_at = _parse_datetime(run.get("completed_at"))
        if started_at and completed_at and completed_at < started_at:
            issues.append("run.completed_at must not be earlier than run.started_at")
        if started_at and completed_at and isinstance(steps, list):
            for step in steps:
                if not isinstance(step, dict):
                    continue
                timestamp = _parse_datetime(step.get("timestamp"))
                if timestamp and not started_at <= timestamp <= completed_at:
                    issues.append("step timestamps must fall within the run time window")
                    break

    redaction = document.get("redaction")
    if isinstance(redaction, dict):
        if redaction.get("raw_content_ref") and redaction.get("status") != "quarantined":
            issues.append("redaction.raw_content_ref requires redaction.status='quarantined'")

    for finding in find_sensitive_content(document):
        issues.append(f"sensitive content detected at {finding.path}: {finding.reason}")

    return issues


def validate_proposal_semantics(document: dict[str, Any]) -> list[str]:
    """Validate proposal identity, promotion, and retrieval invariants."""
    issues: list[str] = []
    operation = document.get("operation")
    target = document.get("target")
    candidate = document.get("candidate")

    if operation == "insert" and target is not None:
        issues.append("insert proposals must not identify an existing target revision")
    if operation == "update" and isinstance(target, dict) and isinstance(candidate, dict):
        if target.get("skill_id") != candidate.get("proposed_skill_id"):
            issues.append("update candidate skill_id must match target skill_id")
        if target.get("base_revision_checksum") == candidate.get("artifact_checksum"):
            issues.append("update candidate checksum must differ from the base revision")

    trajectory_refs = document.get("supporting_trajectories")
    if isinstance(trajectory_refs, list):
        issues.extend(_validate_unique_pairs(trajectory_refs, "trajectory_id", "task_id", "supporting trajectories"))

    retrieval_context = document.get("retrieval_context")
    if isinstance(retrieval_context, list) and retrieval_context:
        issues.extend(_validate_contiguous_indexes(retrieval_context, "rank", "retrieval context ranks"))

    governance = document.get("governance")
    if isinstance(governance, dict) and governance.get("state") == "approved":
        validations = document.get("validations")
        if not isinstance(validations, dict):
            issues.append("approved proposals require validation results")
        else:
            non_passing = sorted(
                name
                for name, result in validations.items()
                if not isinstance(result, dict) or result.get("status") != "pass"
            )
            if non_passing:
                issues.append("approved proposals require pass status for: " + ", ".join(non_passing))

    return issues


def validate_proposal_base_revision(
    proposal: dict[str, Any],
    *,
    current_revision_id: str | None,
    current_revision_checksum: str | None = None,
) -> list[str]:
    """Reject an update/delete proposal whose base revision is no longer current."""
    if proposal.get("operation") == "insert":
        return []

    target = proposal.get("target")
    if not isinstance(target, dict):
        return ["update/delete proposals require a target revision"]

    issues: list[str] = []
    if target.get("base_revision_id") != current_revision_id:
        issues.append("proposal base_revision_id does not match the current revision")
    if current_revision_checksum is not None:
        if target.get("base_revision_checksum") != current_revision_checksum:
            issues.append("proposal base_revision_checksum does not match the current revision")
    return issues


def validate_evaluation_semantics(document: dict[str, Any]) -> list[str]:
    """Validate internal evaluation chronology, task positions, and metric counts."""
    issues: list[str] = []
    protocol = document.get("protocol")
    protocol_started: datetime | None = None
    if isinstance(protocol, dict):
        protocol_started = _parse_datetime(protocol.get("started_at"))
        completed_at = _parse_datetime(protocol.get("completed_at"))
        if protocol_started and completed_at and completed_at < protocol_started:
            issues.append("protocol.completed_at must not be earlier than protocol.started_at")

    task_group = document.get("task_group")
    tasks = task_group.get("tasks") if isinstance(task_group, dict) else None
    if isinstance(tasks, list):
        issues.extend(_validate_contiguous_indexes(tasks, "position", "evaluation task positions"))
        task_ids = [task.get("task_id") for task in tasks if isinstance(task, dict)]
        if len(task_ids) != len(set(task_ids)):
            issues.append("evaluation task IDs must be unique")

        metrics = document.get("metrics")
        if isinstance(metrics, dict):
            for label in ("baseline", "candidate"):
                metric_set = metrics.get(label)
                if isinstance(metric_set, dict) and metric_set.get("task_count") != len(tasks):
                    issues.append(f"metrics.{label}.task_count must equal the holdout task count")
            issues.extend(_validate_metric_deltas(metrics))

    snapshots = document.get("snapshots")
    if isinstance(snapshots, dict):
        baseline = snapshots.get("baseline")
        candidate = snapshots.get("candidate")
        if isinstance(baseline, dict) and isinstance(candidate, dict):
            if baseline.get("snapshot_id") == candidate.get("snapshot_id"):
                issues.append("baseline and candidate snapshot IDs must be distinct")
            if baseline.get("checksum") == candidate.get("checksum"):
                issues.append("baseline and candidate snapshot checksums must be distinct")

    temporal = document.get("temporal_holdout")
    if isinstance(temporal, dict):
        cutoff = _parse_datetime(temporal.get("curator_cutoff_at"))
        first_evaluation = _parse_datetime(temporal.get("first_evaluation_task_at"))
        if cutoff and first_evaluation and first_evaluation <= cutoff:
            issues.append("first evaluation task must occur after the curator cutoff")
        if protocol_started and first_evaluation and first_evaluation < protocol_started:
            issues.append("first evaluation task must not be earlier than protocol.started_at")

    return issues


def validate_temporal_holdout(
    proposal: dict[str, Any],
    evaluation: dict[str, Any],
) -> list[str]:
    """Verify that a proposal did not observe any task used for later evaluation."""
    issues: list[str] = []
    if evaluation.get("proposal_id") != proposal.get("proposal_id"):
        issues.append("evaluation proposal_id does not match the proposal")

    supporting = proposal.get("supporting_trajectories")
    observed_task_ids = {
        ref.get("task_id")
        for ref in supporting
        if isinstance(ref, dict) and ref.get("task_id")
    } if isinstance(supporting, list) else set()

    task_group = evaluation.get("task_group")
    tasks = task_group.get("tasks") if isinstance(task_group, dict) else []
    evaluation_task_ids = {
        task.get("task_id")
        for task in tasks
        if isinstance(task, dict) and task.get("task_id")
    } if isinstance(tasks, list) else set()

    overlap = sorted(observed_task_ids & evaluation_task_ids)
    if overlap:
        issues.append("evaluation reuses curator-observed task IDs: " + ", ".join(overlap))

    temporal = evaluation.get("temporal_holdout")
    if isinstance(temporal, dict):
        cutoff = _parse_datetime(temporal.get("curator_cutoff_at"))
        first_evaluation = _parse_datetime(temporal.get("first_evaluation_task_at"))
        proposal_created = _parse_datetime(proposal.get("created_at"))
        observed_times = [
            parsed
            for ref in supporting or []
            if isinstance(ref, dict)
            for parsed in [_parse_datetime(ref.get("observed_at"))]
            if parsed is not None
        ]

        if cutoff and proposal_created and cutoff < proposal_created:
            issues.append("curator cutoff must not be earlier than proposal creation")
        if proposal_created and observed_times and proposal_created < max(observed_times):
            issues.append("proposal creation must not precede a supporting trajectory")
        if cutoff and observed_times and cutoff < max(observed_times):
            issues.append("curator cutoff must include all supporting trajectories")
        if cutoff and first_evaluation and first_evaluation <= cutoff:
            issues.append("temporal holdout begins before or at the curator cutoff")

    return issues


def validate_contract_document(document: dict[str, Any], contract_type: str) -> list[str]:
    """Run schema and single-document semantic validation."""
    issues = format_contract_validation_errors(iter_contract_validation_errors(document, contract_type))
    if contract_type == "trajectory":
        issues.extend(validate_trajectory_semantics(document))
    elif contract_type == "proposal":
        issues.extend(validate_proposal_semantics(document))
    elif contract_type == "evaluation":
        issues.extend(validate_evaluation_semantics(document))
    return issues


def _escape_pointer_token(token: str) -> str:
    return token.replace("~", "~0").replace("/", "~1")


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _validate_contiguous_indexes(
    items: list[Any],
    field: str,
    label: str,
) -> list[str]:
    values = [item.get(field) for item in items if isinstance(item, dict)]
    expected = list(range(1, len(items) + 1))
    return [] if values == expected else [f"{label} must be contiguous and ordered from 1"]


def _validate_monotonic_timestamps(
    items: list[Any],
    field: str,
    label: str,
) -> list[str]:
    timestamps = [
        parsed
        for item in items
        if isinstance(item, dict)
        for parsed in [_parse_datetime(item.get(field))]
        if parsed is not None
    ]
    return [] if timestamps == sorted(timestamps) else [f"{label} timestamps must be monotonic"]


def _validate_unique_pairs(
    items: list[Any],
    first_field: str,
    second_field: str,
    label: str,
) -> list[str]:
    pairs = [
        (item.get(first_field), item.get(second_field))
        for item in items
        if isinstance(item, dict)
    ]
    return [] if len(pairs) == len(set(pairs)) else [f"{label} must not contain duplicate references"]


def _validate_metric_deltas(metrics: dict[str, Any]) -> list[str]:
    baseline = metrics.get("baseline")
    candidate = metrics.get("candidate")
    delta = metrics.get("delta")
    if not all(isinstance(value, dict) for value in (baseline, candidate, delta)):
        return []

    issues: list[str] = []
    for field in ("success_rate", "average_steps", "average_tokens", "average_latency_ms"):
        baseline_value = baseline.get(field)
        candidate_value = candidate.get(field)
        delta_value = delta.get(field)
        if not all(isinstance(value, (int, float)) for value in (baseline_value, candidate_value, delta_value)):
            continue
        expected = float(candidate_value) - float(baseline_value)
        if not math.isclose(float(delta_value), expected, rel_tol=1e-9, abs_tol=1e-9):
            issues.append(f"metrics.delta.{field} must equal candidate minus baseline")
    return issues
