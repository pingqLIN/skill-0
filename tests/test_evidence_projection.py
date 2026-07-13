from __future__ import annotations

from jsonschema import Draft202012Validator, FormatChecker

from runtime.evidence import build_evidence_summary
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
