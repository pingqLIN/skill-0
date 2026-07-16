from __future__ import annotations

from jsonschema import Draft202012Validator, FormatChecker
import pytest

from runtime.evidence import build_evidence_summary, build_run_evidence
from runtime.ledger import RuntimeLedger
from runtime.models import RuntimeEvent, RuntimeEventType


def _event(run_id, event_type, *, reason=None):
    return RuntimeEvent(
        run_id=run_id,
        event_type=event_type,
        skill_name="demo",
        skill_version="1",
        action_id="a_001",
        payload={} if reason is None else {"reason": reason},
    )


def test_evidence_is_a_derived_projection_not_skill_mutation(tmp_path, read_json):
    with RuntimeLedger(tmp_path / "ledger.db") as ledger:
        success = ledger.create_run(skill_name="demo", skill_version="1")
        ledger.append_event(_event(success, RuntimeEventType.RUN_SUCCEEDED))
        failed = ledger.create_run(skill_name="demo", skill_version="1")
        ledger.append_event(
            _event(failed, RuntimeEventType.RUN_FAILED, reason="validation mismatch")
        )
        summary = build_evidence_summary(
            ledger.list_events_for_skill("demo", "1"),
            skill_name="demo",
            skill_version="1",
            minimum_confident_sample=2,
        )
        assert summary["counts"] == {
            "succeeded": 1,
            "failed": 1,
            "compensated": 0,
            "recovery_failed": 0,
            "awaiting_approval": 0,
            "hitl_required": 0,
            "reconciliation_required": 0,
            "recovery_pending": 0,
            "denied": 0,
            "cancelled": 0,
        }
        assert summary["success_rate"] == 0.5
        assert summary["confidence"] == 1.0
        schema = read_json("schema/evidence-summary.schema.json")
        assert list(
            Draft202012Validator(
                schema, format_checker=FormatChecker()
            ).iter_errors(summary)
        ) == []


def test_compensated_terminal_state_overrides_prior_success(tmp_path):
    with RuntimeLedger(tmp_path / "ledger.db") as ledger:
        run_id = ledger.create_run(skill_name="demo", skill_version="1")
        ledger.append_event(_event(run_id, RuntimeEventType.RUN_SUCCEEDED))
        ledger.append_event(_event(run_id, RuntimeEventType.RUN_COMPENSATED))
        summary = build_evidence_summary(
            ledger.list_events_for_skill("demo", "1"),
            skill_name="demo",
            skill_version="1",
        )
        assert summary["counts"]["compensated"] == 1
        assert summary["counts"]["succeeded"] == 0
        assert summary["source_event_watermark"] == 3


def test_run_evidence_is_deterministic_and_reports_latest_state(tmp_path, read_json):
    with RuntimeLedger(tmp_path / "ledger.db") as ledger:
        run_id = ledger.create_run(skill_name="demo", skill_version="1")
        ledger.append_event(_event(run_id, RuntimeEventType.RUN_FAILED, reason="secret-value"))
        ledger.append_event(_event(run_id, RuntimeEventType.RUN_COMPENSATED))
        run = ledger.get_run(run_id)
        first = build_run_evidence(ledger.list_events(run_id), run=run)
        second = build_run_evidence(ledger.list_events(run_id), run=run)
        assert first == second
        assert first["run_ref"] == {"run_id": run_id, "status": "compensated"}
        assert first["event_count"] == 3
        assert first["last_event_type"] == "run_compensated"
        assert first["counts"]["compensated"] == 1
        assert "secret-value" not in str(first)
        assert first["known_failure_patterns"] == ["run_failed"]
        base_schema = read_json("schema/evidence-summary.schema.json")
        run_schema = read_json("schema/runtime-run-evidence.schema.json")
        assert list(Draft202012Validator(base_schema).iter_errors(first)) == []
        assert list(Draft202012Validator(run_schema).iter_errors(first)) == []


def test_control_plane_states_are_counted_without_inflating_outcome_sample(tmp_path):
    with RuntimeLedger(tmp_path / "ledger.db") as ledger:
        awaiting = ledger.create_run(skill_name="demo", skill_version="1")
        ledger.append_event(_event(awaiting, RuntimeEventType.APPROVAL_REQUIRED))
        hitl = ledger.create_run(skill_name="demo", skill_version="1")
        ledger.append_event(_event(hitl, RuntimeEventType.RUN_SUSPENDED))
        reconciliation = ledger.create_run(skill_name="demo", skill_version="1")
        ledger.append_event(
            _event(reconciliation, RuntimeEventType.RECONCILIATION_REQUIRED)
        )
        summary = build_evidence_summary(
            ledger.list_events_for_skill("demo", "1"),
            skill_name="demo",
            skill_version="1",
        )
        assert summary["counts"]["awaiting_approval"] == 1
        assert summary["counts"]["hitl_required"] == 1
        assert summary["counts"]["reconciliation_required"] == 1
        assert summary["sample_size"] == 0
        assert summary["confidence"] == 0


def test_terminal_outcome_overrides_historical_approval_gate(tmp_path):
    with RuntimeLedger(tmp_path / "ledger.db") as ledger:
        run_id = ledger.create_run(skill_name="demo", skill_version="1")
        ledger.append_event(_event(run_id, RuntimeEventType.APPROVAL_REQUIRED))
        ledger.append_event(_event(run_id, RuntimeEventType.APPROVAL_GRANTED))
        ledger.append_event(_event(run_id, RuntimeEventType.RUN_SUCCEEDED))
        summary = build_evidence_summary(
            ledger.list_events_for_skill("demo", "1"),
            skill_name="demo",
            skill_version="1",
        )
        assert summary["counts"]["succeeded"] == 1
        assert summary["counts"]["awaiting_approval"] == 0


@pytest.mark.parametrize(
    ("events", "count_key"),
    [
        ([RuntimeEventType.POLICY_DENIED], "denied"),
        ([RuntimeEventType.RUN_CANCELLED], "cancelled"),
        (
            [RuntimeEventType.RUN_FAILED, RuntimeEventType.COMPENSATION_QUEUED],
            "recovery_pending",
        ),
    ],
)
def test_additional_control_plane_states_are_counted(tmp_path, events, count_key):
    with RuntimeLedger(tmp_path / f"{count_key}.db") as ledger:
        run_id = ledger.create_run(skill_name="demo", skill_version="1")
        for event_type in events:
            ledger.append_event(_event(run_id, event_type))
        summary = build_evidence_summary(
            ledger.list_events_for_skill("demo", "1"),
            skill_name="demo",
            skill_version="1",
        )
        assert summary["counts"][count_key] == 1
        assert summary["sample_size"] == 0


def test_run_evidence_rejects_sequence_gap():
    run = {
        "run_id": "run-gap",
        "skill_name": "demo",
        "skill_version": "1",
        "status": "failed",
    }
    events = [
        RuntimeEvent(
            run_id="run-gap",
            event_type=RuntimeEventType.RUN_CREATED,
            skill_name="demo",
            skill_version="1",
            sequence=1,
        ),
        RuntimeEvent(
            run_id="run-gap",
            event_type=RuntimeEventType.RUN_FAILED,
            skill_name="demo",
            skill_version="1",
            sequence=3,
        ),
    ]
    with pytest.raises(ValueError, match="not contiguous"):
        build_run_evidence(events, run=run)


def test_run_evidence_rejects_status_projection_drift():
    run = {
        "run_id": "run-status",
        "skill_name": "demo",
        "skill_version": "1",
        "status": "succeeded",
    }
    events = [
        RuntimeEvent(
            run_id="run-status",
            event_type=RuntimeEventType.RUN_CREATED,
            skill_name="demo",
            skill_version="1",
            sequence=1,
        ),
        RuntimeEvent(
            run_id="run-status",
            event_type=RuntimeEventType.RUN_FAILED,
            skill_name="demo",
            skill_version="1",
            sequence=2,
        ),
    ]
    with pytest.raises(ValueError, match="status projection mismatch"):
        build_run_evidence(events, run=run)


def test_run_evidence_rejects_identity_drift_and_duplicate_terminal_event():
    run = {
        "run_id": "run-drift",
        "skill_name": "demo",
        "skill_version": "1",
        "status": "failed",
    }
    identity_drift = [
        RuntimeEvent(
            run_id="run-drift",
            event_type=RuntimeEventType.RUN_CREATED,
            skill_name="different",
            skill_version="1",
            sequence=1,
        )
    ]
    with pytest.raises(ValueError, match="skill identity mismatch"):
        build_run_evidence(identity_drift, run=run)

    duplicate_terminal = [
        RuntimeEvent(
            run_id="run-drift",
            event_type=RuntimeEventType.RUN_CREATED,
            skill_name="demo",
            skill_version="1",
            sequence=1,
        ),
        RuntimeEvent(
            run_id="run-drift",
            event_type=RuntimeEventType.RUN_FAILED,
            skill_name="demo",
            skill_version="1",
            sequence=2,
        ),
        RuntimeEvent(
            run_id="run-drift",
            event_type=RuntimeEventType.RUN_FAILED,
            skill_name="demo",
            skill_version="1",
            sequence=3,
        ),
    ]
    with pytest.raises(ValueError, match="invalid after outcome"):
        build_run_evidence(duplicate_terminal, run=run)


def test_run_evidence_uses_sequence_order_for_snapshot_timestamp():
    run = {
        "run_id": "run-time",
        "skill_name": "demo",
        "skill_version": "1",
        "status": "succeeded",
    }
    events = [
        RuntimeEvent(
            run_id="run-time",
            event_type=RuntimeEventType.RUN_CREATED,
            skill_name="demo",
            skill_version="1",
            sequence=1,
            occurred_at="2026-07-16T12:00:00+00:00",
        ),
        RuntimeEvent(
            run_id="run-time",
            event_type=RuntimeEventType.RUN_SUCCEEDED,
            skill_name="demo",
            skill_version="1",
            sequence=2,
            occurred_at="2026-07-16T11:00:00+00:00",
        ),
    ]
    summary = build_run_evidence(events, run=run)
    assert summary["generated_at"] == "2026-07-16T11:00:00+00:00"
    assert summary["source_event_watermark"] == 2


def test_run_evidence_rejects_event_after_final_terminal():
    run = {
        "run_id": "run-terminal",
        "skill_name": "demo",
        "skill_version": "1",
        "status": "planned",
    }
    event_types = [
        RuntimeEventType.RUN_CREATED,
        RuntimeEventType.RUN_FAILED,
        RuntimeEventType.RUN_CANCELLED,
        RuntimeEventType.PLAN_CREATED,
    ]
    events = [
        RuntimeEvent(
            run_id="run-terminal",
            event_type=event_type,
            skill_name="demo",
            skill_version="1",
            sequence=index,
        )
        for index, event_type in enumerate(event_types, start=1)
    ]
    with pytest.raises(ValueError, match="after final terminal"):
        build_run_evidence(events, run=run)
