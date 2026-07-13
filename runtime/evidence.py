from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Iterable

from .models import RuntimeEvent, RuntimeEventType


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
            failure_patterns.add(str(reason)[:240])

    counts = {
        "succeeded": 0,
        "failed": 0,
        "compensated": 0,
        "recovery_failed": 0,
    }
    for run_events in by_run.values():
        types = {event.event_type for event in run_events}
        if RuntimeEventType.RUN_COMPENSATED in types:
            counts["compensated"] += 1
        elif RuntimeEventType.RUN_RECOVERY_FAILED in types:
            counts["recovery_failed"] += 1
        elif RuntimeEventType.RUN_FAILED in types:
            counts["failed"] += 1
        elif RuntimeEventType.RUN_SUCCEEDED in types:
            counts["succeeded"] += 1

    sample_size = sum(counts.values())
    success_rate = counts["succeeded"] / sample_size if sample_size else None
    confidence = min(1.0, sample_size / max(1, minimum_confident_sample))
    return {
        "projection_version": "1.0.0",
        "skill_ref": {"name": skill_name, "version": skill_version},
        "generated_at": datetime.now(timezone.utc).isoformat(),
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
                "ref": "append-only SQLite ledger",
                "version": "4.0.0",
            }
        ],
    }
