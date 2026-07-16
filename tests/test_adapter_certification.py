from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys

from runtime.adapters.local_pdf import LocalPdfFilesystemAdapter
from runtime.certification import (
    SignedProductionApprovalGate,
    build_production_approval,
    build_production_revocation,
    load_certification_manifest,
)
from runtime.digest import canonical_digest
from runtime.executor import RuntimeExecutor
from runtime.ledger import RuntimeLedger
from runtime.models import PolicyDecision, RunStatus, RuntimeEventType
from tools.certify_adapter import TEST_APPROVAL_KEY, parameters, run_certification


MANIFEST_PATH = (
    Path(__file__).resolve().parents[1]
    / "adapters"
    / "local-pdf-filesystem"
    / "adapter-certification.json"
)
PREFLIGHT = {
    "schema_validated": True,
    "skill_schema_validated": True,
    "cross_references_validated": True,
    "skill_identity_validated": True,
    "governance_validated": True,
    "precondition_rule_ids": [],
}


class AllowPolicy:
    def evaluate(self, action_binding, context):
        del action_binding, context
        return PolicyDecision("allow", "certification test policy")


def production_contract() -> dict:
    return {
        "schema_version": "4.0.0",
        "skill_ref": {"name": "pdf", "version": "2.4.0"},
        "action_bindings": [
            {
                "action_id": "a_006",
                "role": "primary",
                "adapter": {
                    "kind": "python",
                    "target": "runtime.adapters.local_pdf:LocalPdfFilesystemAdapter",
                },
                "effect": {
                    "classification": "bounded_write",
                    "resource_kind": "filesystem",
                    "resource_name": "configured_pdf_output_root",
                    "operation": "create_pdf",
                    "external_id_pointer": "/outputs/resource_id",
                    "primary_idempotency_key_template": "pdf-create:{input.relative_path}",
                    "resource_lock_key_template": "pdf:{input.relative_path}",
                },
                "risk": {
                    "level": "medium",
                    "approval_required": True,
                    "data_sensitivity": "internal",
                },
                "compensation": {
                    "strategy": "human_intervention",
                    "escalation_queue": "runtime-recovery",
                    "operator_instructions": "Use the certified adapter compensation primitive after reconciling the file receipt.",
                },
            }
        ],
        "governance": {"default_decision": "deny", "rule_policy_bindings": []},
        "directive_manifest": {"include": [], "exclude": [], "token_budget": 0},
        "feature_flags": {"real_execution": True},
    }


def approval_gate(adapter, evidence):
    manifest = load_certification_manifest(MANIFEST_PATH)
    approval = build_production_approval(
        manifest,
        evidence,
        environment="test-production",
        approved_by="test-reviewer",
        approved_at="2026-07-17T00:00:00+00:00",
        expires_at="2026-07-18T00:00:00+00:00",
        key=TEST_APPROVAL_KEY,
    )
    gate = SignedProductionApprovalGate(
        approval,
        key=TEST_APPROVAL_KEY,
        environment="test-production",
        now=lambda: datetime(2026, 7, 17, 12, tzinfo=timezone.utc),
    )
    decision = gate.evaluate(adapter, production_contract()["action_bindings"])
    assert decision.allowed is True
    return gate, decision.attestation


def create_production_run(ledger: RuntimeLedger, preflight: dict) -> tuple[str, str]:
    execution_digest = "test-production-execution-digest"
    run_id = ledger.create_run(
        skill_name="pdf",
        skill_version="2.4.0",
        execution_basis={
            "skill_id": "claude__anthropic__pdf",
            "governance_revision_id": "test-revision",
            "skill_source_digest": "sha256:" + "a" * 64,
            "contract_digest": canonical_digest(production_contract()),
            "input_digest": "sha256:" + "b" * 64,
            "preflight_digest": canonical_digest(preflight),
            "execution_digest": execution_digest,
            "dry_run": False,
        },
    )
    return run_id, execution_digest


def test_single_adapter_certification_probes_pass():
    evidence = run_certification(MANIFEST_PATH)
    assert evidence["overall_status"] == "passed"
    assert evidence["approval_status"] == "pending_human_approval"
    assert all(probe["status"] == "passed" for probe in evidence["probes"])


def test_real_execution_fails_closed_without_adapter_approval(tmp_path):
    output = tmp_path / "output"
    state = tmp_path / "state"
    output.mkdir()
    state.mkdir()
    with LocalPdfFilesystemAdapter(output, state / "adapter.db") as adapter:
        with RuntimeLedger(tmp_path / "runtime.db") as ledger:
            run_id, execution_digest = create_production_run(ledger, PREFLIGHT)
            result = RuntimeExecutor(ledger, adapter, policy=AllowPolicy()).run(
                production_contract(),
                parameters=parameters("denied.pdf", "denied"),
                dry_run=False,
                preflight=PREFLIGHT,
                existing_run_id=run_id,
                execution_basis_digest=execution_digest,
            )
            assert result.status == RunStatus.DENIED
            assert result.reason == "production adapter approval gate is unavailable"
            assert not (output / "denied.pdf").exists()


def test_real_execution_requires_durable_execution_basis(tmp_path):
    output = tmp_path / "output"
    state = tmp_path / "state"
    output.mkdir()
    state.mkdir()
    with LocalPdfFilesystemAdapter(output, state / "adapter.db") as adapter:
        with RuntimeLedger(tmp_path / "runtime.db") as ledger:
            result = RuntimeExecutor(ledger, adapter, policy=AllowPolicy()).run(
                production_contract(),
                parameters=parameters("unbound.pdf", "unbound"),
                dry_run=False,
                preflight=PREFLIGHT,
            )
            assert result.status == RunStatus.DENIED
            assert result.reason == "real execution requires a matching durable execution basis"
            assert not (output / "unbound.pdf").exists()


def test_real_execution_binds_certification_approval_and_idempotency(tmp_path):
    evidence = run_certification(MANIFEST_PATH)
    output = tmp_path / "output"
    state = tmp_path / "state"
    output.mkdir()
    state.mkdir()
    with LocalPdfFilesystemAdapter(output, state / "adapter.db") as adapter:
        gate, attestation = approval_gate(adapter, evidence)
        preflight = {**PREFLIGHT, "adapter_production_approval": attestation}
        with RuntimeLedger(tmp_path / "runtime.db") as ledger:
            run_id, execution_digest = create_production_run(ledger, preflight)
            result = RuntimeExecutor(
                ledger,
                adapter,
                policy=AllowPolicy(),
                production_approval_gate=gate,
            ).run(
                production_contract(),
                parameters=parameters("approved.pdf", "approved"),
                dry_run=False,
                preflight=preflight,
                existing_run_id=run_id,
                execution_basis_digest=execution_digest,
            )
            assert result.status == RunStatus.SUCCEEDED
            assert (output / "approved.pdf").is_file()
            assert ledger.count_events(
                result.run_id, RuntimeEventType.ADAPTER_APPROVAL_VALIDATED
            ) == 1
            event = next(
                item
                for item in ledger.list_events(result.run_id)
                if item.event_type == RuntimeEventType.ACTION_PREPARED
            )
            assert event.idempotency_key == "pdf-create:approved.pdf"


def test_expired_or_operation_drift_approval_is_denied(tmp_path):
    evidence = run_certification(MANIFEST_PATH)
    output = tmp_path / "output"
    state = tmp_path / "state"
    output.mkdir()
    state.mkdir()
    manifest = load_certification_manifest(MANIFEST_PATH)
    approval = build_production_approval(
        manifest,
        evidence,
        environment="test-production",
        approved_by="test-reviewer",
        approved_at="2026-07-17T00:00:00+00:00",
        expires_at="2026-07-18T00:00:00+00:00",
        key=TEST_APPROVAL_KEY,
    )
    with LocalPdfFilesystemAdapter(output, state / "adapter.db") as adapter:
        expired = SignedProductionApprovalGate(
            approval,
            key=TEST_APPROVAL_KEY,
            environment="test-production",
            now=lambda: datetime(2026, 7, 18, tzinfo=timezone.utc),
        ).evaluate(adapter, production_contract()["action_bindings"])
        drifted_contract = production_contract()
        drifted_contract["action_bindings"][0]["effect"]["operation"] = "overwrite_pdf"
        drifted = SignedProductionApprovalGate(
            approval,
            key=TEST_APPROVAL_KEY,
            environment="test-production",
            now=lambda: datetime(2026, 7, 17, 12, tzinfo=timezone.utc),
        ).evaluate(adapter, drifted_contract["action_bindings"])
        revoked_record = build_production_revocation(
            approval,
            revoked_by="test-reviewer",
            revoked_at="2026-07-17T13:00:00+00:00",
            key=TEST_APPROVAL_KEY,
        )
        revoked = SignedProductionApprovalGate(
            revoked_record,
            key=TEST_APPROVAL_KEY,
            environment="test-production",
            now=lambda: datetime(2026, 7, 17, 14, tzinfo=timezone.utc),
        ).evaluate(adapter, production_contract()["action_bindings"])
        assert expired.allowed is False
        assert expired.reason == "adapter approval has expired"
        assert drifted.allowed is False
        assert drifted.reason == "runtime operation is outside adapter approval scope"
        assert revoked.allowed is False
        assert revoked.reason == "adapter approval is not active"


def test_approval_cli_issue_verify_and_revoke(tmp_path, monkeypatch):
    evidence_path = tmp_path / "evidence.json"
    evidence_path.write_text(
        json.dumps(run_certification(MANIFEST_PATH)), encoding="utf-8"
    )
    approval_path = tmp_path / "approval.json"
    revocation_path = tmp_path / "revocation.json"
    monkeypatch.setenv("SKILL0_ADAPTER_APPROVAL_KEY", TEST_APPROVAL_KEY)
    expires_at = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    tool = Path(__file__).resolve().parents[1] / "tools" / "adapter_approval.py"
    issue = subprocess.run(
        [
            sys.executable,
            str(tool),
            "issue",
            "--manifest",
            str(MANIFEST_PATH),
            "--evidence",
            str(evidence_path),
            "--environment",
            "cli-certification-test",
            "--approved-by",
            "test-reviewer",
            "--expires-at",
            expires_at,
            "--output",
            str(approval_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert issue.returncode == 0, issue.stderr
    verify = subprocess.run(
        [
            sys.executable,
            str(tool),
            "verify",
            "--approval",
            str(approval_path),
            "--manifest",
            str(MANIFEST_PATH),
            "--environment",
            "cli-certification-test",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert verify.returncode == 0, verify.stderr
    revoke = subprocess.run(
        [
            sys.executable,
            str(tool),
            "revoke",
            "--approval",
            str(approval_path),
            "--revoked-by",
            "test-reviewer",
            "--output",
            str(revocation_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert revoke.returncode == 0, revoke.stderr
    verify_revoked = subprocess.run(
        [
            sys.executable,
            str(tool),
            "verify",
            "--approval",
            str(revocation_path),
            "--manifest",
            str(MANIFEST_PATH),
            "--environment",
            "cli-certification-test",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert verify_revoked.returncode == 1
