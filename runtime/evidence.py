from __future__ import annotations

from collections import defaultdict
from datetime import datetime
import re
from typing import Iterable

from .ledger import projected_status_for_event, validate_event_type_sequence
from .models import RuntimeEvent, RuntimeEventType


_SAFE_REASON_CODE = re.compile(r"^[A-Z][A-Z0-9_]{1,63}$")
_TERMINAL_EVENT_TYPES = {
    RuntimeEventType.RUN_SUCCEEDED,
    RuntimeEventType.RUN_FAILED,
    RuntimeEventType.RUN_COMPENSATED,
    RuntimeEventType.RUN_RECOVERY_FAILED,
    RuntimeEventType.RUN_CANCELLED,
}


def _failure_pattern(event: RuntimeEvent) -> str:
    reason_code = event.payload.get("reason_code")
    if isinstance(reason_code, str) and _SAFE_REASON_CODE.fullmatch(reason_code):
        return f"{event.event_type.value}:{reason_code}"
    return event.event_type.value


def validate_run_event_stream(
    events: Iterable[RuntimeEvent],
    *,
    run: dict[str, object],
) -> list[RuntimeEvent]:
    ordered = sorted(events, key=lambda event: event.sequence)
    if not ordered:
        raise ValueError("runtime Evidence requires at least one event")
    expected_sequences = list(range(1, len(ordered) + 1))
    if [event.sequence for event in ordered] != expected_sequences:
        raise ValueError("runtime event sequence is not contiguous")
    if ordered[0].event_type != RuntimeEventType.RUN_CREATED:
        raise ValueError("runtime event stream must begin with run_created")
    validate_event_type_sequence(event.event_type for event in ordered)

    terminal_counts: dict[RuntimeEventType, int] = defaultdict(int)
    projected_status: str | None = None
    for event in ordered:
        if event.run_id != run["run_id"]:
            raise ValueError("runtime event run identity mismatch")
        if event.skill_name != run["skill_name"] or event.skill_version != run["skill_version"]:
            raise ValueError("runtime event skill identity mismatch")
        if event.schema_version != "4.0.0":
            raise ValueError("unsupported runtime event schema version")
        try:
            datetime.fromisoformat(event.occurred_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("invalid runtime event timestamp") from exc
        if event.event_type in _TERMINAL_EVENT_TYPES:
            terminal_counts[event.event_type] += 1
        status = projected_status_for_event(event.event_type)
        if status is not None:
            projected_status = status.value
    if any(count > 1 for count in terminal_counts.values()):
        raise ValueError("duplicate runtime terminal event")
    if projected_status != run["status"]:
        raise ValueError("runtime run status projection mismatch")
    return ordered


def build_evidence_summary(
    events: Iterable[RuntimeEvent],
    *,
    skill_name: str,
    skill_version: str,
    minimum_confident_sample: int = 10,
) -> dict[str, object]:
    """Build a reproducible Evidence projection from immutable runtime events.

    Evidence is deliberately derived and does not mutate the ARD decomposition.
    """
    ordered = sorted(events, key=lambda event: (event.occurred_at, event.run_id, event.sequence))
    by_run: dict[str, list[RuntimeEvent]] = defaultdict(list)
    element_refs: set[str] = set()
    failure_patterns: set[str] = set()
    for event in ordered:
        by_run[event.run_id].append(event)
        if event.action_id:
            element_refs.add(event.action_id)
        reason = event.payload.get("reason")
        if reason and event.event_type in {
            RuntimeEventType.RUN_FAILED,
            RuntimeEventType.RUN_RECOVERY_FAILED,
            RuntimeEventType.RUN_SUSPENDED,
            RuntimeEventType.RECONCILIATION_REQUIRED,
        }:
            failure_patterns.add(_failure_pattern(event))

    counts = {
        "succeeded": 0,
        "failed": 0,
        "compensated": 0,
        "recovery_failed": 0,
        "awaiting_approval": 0,
        "hitl_required": 0,
        "reconciliation_required": 0,
        "recovery_pending": 0,
        "denied": 0,
        "cancelled": 0,
    }
    for run_events in by_run.values():
        types = {event.event_type for event in run_events}
        if RuntimeEventType.RUN_COMPENSATED in types:
            counts["compensated"] += 1
        elif RuntimeEventType.RUN_RECOVERY_FAILED in types:
            counts["recovery_failed"] += 1
        elif RuntimeEventType.RECONCILIATION_REQUIRED in types:
            counts["reconciliation_required"] += 1
        elif RuntimeEventType.RUN_SUSPENDED in types:
            counts["hitl_required"] += 1
        elif RuntimeEventType.RUN_CANCELLED in types:
            counts["cancelled"] += 1
        elif RuntimeEventType.COMPENSATION_QUEUED in types and RuntimeEventType.RUN_SUCCEEDED not in types:
            counts["recovery_pending"] += 1
        elif RuntimeEventType.RUN_SUCCEEDED in types:
            counts["succeeded"] += 1
        elif RuntimeEventType.RUN_FAILED in types:
            counts["failed"] += 1
        elif RuntimeEventType.POLICY_DENIED in types:
            counts["denied"] += 1
        elif (
            RuntimeEventType.APPROVAL_REQUIRED in types
            and RuntimeEventType.APPROVAL_GRANTED not in types
        ):
            counts["awaiting_approval"] += 1

    sample_size = sum(
        counts[name]
        for name in ("succeeded", "failed", "compensated", "recovery_failed")
    )
    success_rate = counts["succeeded"] / sample_size if sample_size else None
    confidence = min(1.0, sample_size / max(1, minimum_confident_sample))
    return {
        "projection_version": "1.0.0",
        "skill_ref": {"name": skill_name, "version": skill_version},
        "generated_at": (
            ordered[-1].occurred_at if ordered else "1970-01-01T00:00:00+00:00"
        ),
        "source_event_watermark": len(ordered),
        "counts": counts,
        "sample_size": sample_size,
        "success_rate": success_rate,
        "confidence": confidence,
        "known_failure_patterns": sorted(failure_patterns),
        "element_refs": sorted(element_refs),
        "provenance": [
            {
                "kind": "runtime_event_ledger",
                "ref": f"append-only SQLite ledger#events={len(ordered)}",
                "version": "4.0.0",
            }
        ],
    }


def build_run_evidence(
    events: Iterable[RuntimeEvent],
    *,
    run: dict[str, object],
) -> dict[str, object]:
    ordered = validate_run_event_stream(events, run=run)
    summary = build_evidence_summary(
        ordered,
        skill_name=str(run["skill_name"]),
        skill_version=str(run["skill_version"]),
        minimum_confident_sample=1,
    )
    summary["run_ref"] = {
        "run_id": str(run["run_id"]),
        "status": str(run["status"]),
    }
    summary["event_count"] = len(ordered)
    summary["source_event_watermark"] = ordered[-1].sequence
    summary["last_event_type"] = ordered[-1].event_type.value if ordered else None
    summary["generated_at"] = ordered[-1].occurred_at
    return summary
