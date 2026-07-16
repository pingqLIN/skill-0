from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
from typing import Any, Callable
from uuid import uuid4

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from runtime.adapters.local_pdf import (
    AdapterOutcomeUnknown,
    AdapterRateLimitExceeded,
    IdempotencyConflict,
    InvalidAdapterInput,
    LocalPdfFilesystemAdapter,
)
from runtime.certification import (
    REQUIRED_CERTIFICATION_PROBES,
    SignedProductionApprovalGate,
    build_production_approval,
    load_certification_manifest,
    validate_certification_pair,
)
from runtime.digest import canonical_digest


DEFAULT_MANIFEST = (
    REPO_ROOT
    / "adapters"
    / "local-pdf-filesystem"
    / "adapter-certification.json"
)
TEST_APPROVAL_KEY = "adapter-certification-test-key-0123456789abcdef"


def minimal_pdf(label: str) -> bytes:
    safe_label = "".join(character for character in label if character.isalnum())[:32]
    stream = f"BT /F1 12 Tf 20 100 Td ({safe_label}) Tj ET\n".encode("ascii")
    objects = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>\nendobj\n",
        b"4 0 obj\n<< /Length "
        + str(len(stream)).encode("ascii")
        + b" >>\nstream\n"
        + stream
        + b"endstream\nendobj\n",
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
    ]
    document = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for item in objects:
        offsets.append(len(document))
        document.extend(item)
    xref_offset = len(document)
    document.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    document.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        document.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    document.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(document)


def parameters(name: str, label: str) -> dict[str, str]:
    return {
        "relative_path": name,
        "pdf_base64": base64.b64encode(minimal_pdf(label)).decode("ascii"),
    }


def _sandbox_adapter(
    sandbox: Path,
    manifest_path: Path,
    **kwargs: Any,
) -> LocalPdfFilesystemAdapter:
    output = sandbox / "output"
    state = sandbox / "state"
    output.mkdir()
    state.mkdir()
    return LocalPdfFilesystemAdapter(
        output,
        state / "adapter.db",
        manifest_path=manifest_path,
        **kwargs,
    )


def _probe(
    name: str, operation: Callable[[], dict[str, Any]]
) -> dict[str, Any]:
    try:
        evidence = operation()
    except Exception as exc:
        return {
            "name": name,
            "status": "failed",
            "summary": f"probe failed with {type(exc).__name__}",
            "evidence": {"exception_type": type(exc).__name__},
        }
    return {
        "name": name,
        "status": "passed",
        "summary": f"{name.replace('_', ' ')} passed",
        "evidence": evidence,
    }


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _evidence_document(
    manifest: dict[str, Any], probes: list[dict[str, Any]]
) -> dict[str, Any]:
    overall = "passed" if all(probe["status"] == "passed" for probe in probes) else "failed"
    return {
        "schema_version": "1.0.0",
        "evidence_id": str(uuid4()),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "adapter": {
            name: manifest["adapter"][name]
            for name in ("id", "version", "kind", "target", "artifact_digest")
        },
        "manifest_digest": canonical_digest(manifest),
        "scope": {
            "environment": "isolated_local_sandbox",
            "external_credentials_used": False,
            "external_network_used": False,
            "side_effect_boundary": "temporary_directory_only",
        },
        "probes": probes,
        "overall_status": overall,
        "approval_status": "pending_human_approval",
    }


def run_certification(manifest_path: str | Path = DEFAULT_MANIFEST) -> dict[str, Any]:
    manifest_path = Path(manifest_path)
    manifest = load_certification_manifest(manifest_path)
    probes: list[dict[str, Any]] = []

    def credential_boundary() -> dict[str, Any]:
        with tempfile.TemporaryDirectory(prefix="skill0-adapter-cert-") as temp:
            sandbox = Path(temp)
            with _sandbox_adapter(sandbox, manifest_path) as adapter:
                try:
                    adapter.execute(
                        "a_006",
                        parameters("../outside.pdf", "escape"),
                        idempotency_key="credential-boundary",
                        dry_run=False,
                    )
                except InvalidAdapterInput:
                    rejected = True
                else:
                    rejected = False
                outside_effect = (sandbox / "outside.pdf").exists()
                unowned_path = sandbox / "output" / "unowned.pdf"
                unowned_content = minimal_pdf("unowned")
                unowned_path.write_bytes(unowned_content)
                try:
                    adapter.execute(
                        "a_006",
                        parameters("unowned.pdf", "replacement"),
                        idempotency_key="unowned-boundary",
                        dry_run=False,
                    )
                except AdapterOutcomeUnknown:
                    unowned_rejected = True
                else:
                    unowned_rejected = False
                unowned_unchanged = unowned_path.read_bytes() == unowned_content
                _require(manifest["credential_profile"]["mode"] == "none", "credential mode drift")
                _require(
                    not manifest["credential_profile"]["secret_references"],
                    "secret references are not allowed for this adapter",
                )
                _require(rejected, "path traversal was not rejected")
                _require(not outside_effect, "an effect escaped the output root")
                _require(unowned_rejected, "an unowned file overwrite was accepted")
                _require(unowned_unchanged, "an unowned file was modified")
                return {
                    "credential_mode": manifest["credential_profile"]["mode"],
                    "secret_reference_count": len(
                        manifest["credential_profile"]["secret_references"]
                    ),
                    "path_traversal_rejected": rejected,
                    "outside_effect_observed": outside_effect,
                    "unowned_overwrite_rejected": unowned_rejected,
                    "unowned_artifact_unchanged": unowned_unchanged,
                }

    probes.append(_probe("credential_boundary", credential_boundary))

    def idempotency_replay() -> dict[str, Any]:
        with tempfile.TemporaryDirectory(prefix="skill0-adapter-cert-") as temp:
            sandbox = Path(temp)
            with _sandbox_adapter(sandbox, manifest_path) as adapter:
                request = parameters("replay.pdf", "replay")
                first = adapter.execute(
                    "a_006", request, idempotency_key="replay-key", dry_run=False
                )
                second = adapter.execute(
                    "a_006", request, idempotency_key="replay-key", dry_run=False
                )
                effect_count = len(list((sandbox / "output").glob("*.pdf")))
                raw_key_persisted = any(
                    b"replay-key" in path.read_bytes()
                    for path in sandbox.rglob("*")
                    if path.is_file()
                )
                _require(first.outputs["replayed"] is False, "first execution was marked replayed")
                _require(second.outputs["replayed"] is True, "second execution was not a replay")
                _require(effect_count == 1, "idempotent replay created duplicate effects")
                _require(not raw_key_persisted, "raw idempotency key was persisted")
                _require(
                    first.outputs["content_digest"] == second.outputs["content_digest"],
                    "idempotent replay changed the content digest",
                )
                return {
                    "first_replayed": first.outputs["replayed"],
                    "second_replayed": second.outputs["replayed"],
                    "pdf_effect_count": effect_count,
                    "content_digest_stable": first.outputs["content_digest"]
                    == second.outputs["content_digest"],
                    "raw_idempotency_key_persisted": raw_key_persisted,
                }

    probes.append(_probe("idempotency_replay", idempotency_replay))

    def idempotency_conflict() -> dict[str, Any]:
        with tempfile.TemporaryDirectory(prefix="skill0-adapter-cert-") as temp:
            sandbox = Path(temp)
            with _sandbox_adapter(sandbox, manifest_path) as adapter:
                first = parameters("conflict.pdf", "first")
                adapter.execute(
                    "a_006", first, idempotency_key="conflict-key", dry_run=False
                )
                original = (sandbox / "output" / "conflict.pdf").read_bytes()
                try:
                    adapter.execute(
                        "a_006",
                        parameters("conflict.pdf", "second"),
                        idempotency_key="conflict-key",
                        dry_run=False,
                    )
                except IdempotencyConflict:
                    rejected = True
                else:
                    rejected = False
                unchanged = original == (sandbox / "output" / "conflict.pdf").read_bytes()
                effect_count = len(list((sandbox / "output").glob("*.pdf")))
                _require(rejected, "conflicting idempotency request was accepted")
                _require(unchanged, "conflicting request changed the original artifact")
                _require(effect_count == 1, "conflicting request created another effect")
                return {
                    "conflict_rejected": rejected,
                    "original_artifact_unchanged": unchanged,
                    "pdf_effect_count": effect_count,
                }

    probes.append(_probe("idempotency_conflict", idempotency_conflict))

    def reconciliation_probe() -> dict[str, Any]:
        def fault(stage: str) -> None:
            if stage == "after_effect_commit":
                raise TimeoutError("simulated post-commit timeout")

        with tempfile.TemporaryDirectory(prefix="skill0-adapter-cert-") as temp:
            sandbox = Path(temp)
            with _sandbox_adapter(
                sandbox, manifest_path, fault_injector=fault
            ) as adapter:
                request = parameters("ambiguous.pdf", "ambiguous")
                try:
                    adapter.execute(
                        "a_006",
                        request,
                        idempotency_key="ambiguous-key",
                        dry_run=False,
                    )
                except TimeoutError:
                    ambiguous = True
                else:
                    ambiguous = False
                result = adapter.reconcile(
                    "a_006", request, idempotency_key="ambiguous-key"
                )
                _require(ambiguous, "post-commit ambiguity was not injected")
                _require(result.status.value == "applied", "reconciliation did not prove the effect")
                _require(result.evidence.get("effect_count") == 1, "reconciliation found duplicate effects")
                return {
                    "ambiguous_exception_observed": ambiguous,
                    "reconciliation_status": result.status.value,
                    "effect_count": result.evidence.get("effect_count"),
                    "automatic_retry_count": 0,
                }

    probes.append(
        _probe("reconciliation_after_ambiguous_outcome", reconciliation_probe)
    )

    def compensation_evidence() -> dict[str, Any]:
        with tempfile.TemporaryDirectory(prefix="skill0-adapter-cert-") as temp:
            sandbox = Path(temp)
            with _sandbox_adapter(sandbox, manifest_path) as adapter:
                request = parameters("compensate.pdf", "compensate")
                created = adapter.execute(
                    "a_006", request, idempotency_key="create-key", dry_run=False
                )
                first = adapter.compensate(
                    "a_006",
                    {"resource_id": created.external_resource_id},
                    idempotency_key="compensate-key",
                    dry_run=False,
                )
                second = adapter.compensate(
                    "a_006",
                    {"resource_id": created.external_resource_id},
                    idempotency_key="compensate-key",
                    dry_run=False,
                )
                original_absent = not (sandbox / "output" / "compensate.pdf").exists()
                recoverable_copy = bool(
                    list((sandbox / "output" / ".del").glob("compensate.pdf.*"))
                )
                required_fields = {
                    "original_resource_id",
                    "content_digest",
                    "quarantine_resource_id",
                    "compensation_key_digest",
                    "completed_at",
                }
                _require(original_absent, "compensation left the original effect active")
                _require(recoverable_copy, "compensation did not preserve a recoverable artifact")
                _require(required_fields.issubset(first.outputs), "compensation evidence is incomplete")
                _require(second.outputs["replayed"] is True, "compensation replay was not idempotent")
                _require(
                    first.outputs["content_digest"] == created.outputs["content_digest"],
                    "compensation evidence content digest drifted",
                )
                return {
                    "original_absent": original_absent,
                    "recoverable_copy_present": recoverable_copy,
                    "evidence_fields": sorted(
                        key
                        for key in first.outputs
                        if key not in {"replayed"}
                    ),
                    "second_compensation_replayed": second.outputs["replayed"],
                    "content_digest_stable": first.outputs["content_digest"]
                    == created.outputs["content_digest"],
                }

    probes.append(_probe("compensation_evidence", compensation_evidence))

    def rate_limit() -> dict[str, Any]:
        clock = [0.0]
        with tempfile.TemporaryDirectory(prefix="skill0-adapter-cert-") as temp:
            sandbox = Path(temp)
            with _sandbox_adapter(
                sandbox, manifest_path, clock=lambda: clock[0]
            ) as adapter:
                for index in range(2):
                    adapter.execute(
                        "a_006",
                        parameters(f"rate-{index}.pdf", f"rate{index}"),
                        idempotency_key=f"rate-{index}",
                        dry_run=False,
                    )
                try:
                    adapter.execute(
                        "a_006",
                        parameters("rate-blocked.pdf", "blocked"),
                        idempotency_key="rate-blocked",
                        dry_run=False,
                    )
                except AdapterRateLimitExceeded as exc:
                    blocked = True
                    retry_after = exc.retry_after_seconds
                else:
                    blocked = False
                    retry_after = 0.0
                clock[0] = 61.0
                after_window = adapter.execute(
                    "a_006",
                    parameters("rate-after-window.pdf", "afterwindow"),
                    idempotency_key="rate-after-window",
                    dry_run=False,
                )
                _require(blocked, "configured request limit did not block the third request")
                _require(retry_after > 0, "rate limit did not expose retry-after evidence")
                _require(after_window.success, "rate limit did not reset after the configured window")
                return {
                    "third_request_blocked": blocked,
                    "retry_after_seconds": retry_after,
                    "request_after_window_succeeded": after_window.success,
                    "configured_max_requests": adapter.max_requests,
                    "configured_window_seconds": adapter.window_seconds,
                }

    probes.append(_probe("rate_limit", rate_limit))

    def production_approval_gate() -> dict[str, Any]:
        placeholder_probes = list(probes)
        placeholder_probes.append(
            {
                "name": "production_approval_gate",
                "status": "passed",
                "summary": "ephemeral gate fixture",
                "evidence": {"fixture": True},
            }
        )
        names = {probe["name"] for probe in placeholder_probes}
        for missing in sorted(REQUIRED_CERTIFICATION_PROBES - names):
            placeholder_probes.append(
                {
                    "name": missing,
                    "status": "passed",
                    "summary": "ephemeral gate fixture",
                    "evidence": {"fixture": True},
                }
            )
        technical_evidence = _evidence_document(manifest, placeholder_probes)
        approval = build_production_approval(
            manifest,
            technical_evidence,
            environment="certification-test",
            approved_by="certification-test",
            approved_at="2026-07-17T00:00:00+00:00",
            expires_at="2026-07-18T00:00:00+00:00",
            key=TEST_APPROVAL_KEY,
        )
        with tempfile.TemporaryDirectory(prefix="skill0-adapter-cert-") as temp:
            sandbox = Path(temp)
            with _sandbox_adapter(sandbox, manifest_path) as adapter:
                gate = SignedProductionApprovalGate(
                    approval,
                    key=TEST_APPROVAL_KEY,
                    environment="certification-test",
                    now=lambda: datetime(2026, 7, 17, 12, tzinfo=timezone.utc),
                )
                binding = {
                    "action_id": "a_006",
                    "role": "primary",
                    "adapter": {
                        "kind": adapter.adapter_kind,
                        "target": adapter.adapter_target,
                    },
                    "effect": {
                        "resource_kind": "filesystem",
                        "operation": "create_pdf",
                    },
                }
                accepted = gate.evaluate(adapter, [binding])
                drifted = json.loads(json.dumps(binding))
                drifted["effect"]["operation"] = "overwrite_pdf"
                rejected = gate.evaluate(adapter, [drifted])
                _require(accepted.allowed, "exact signed production approval was rejected")
                _require(
                    bool(accepted.attestation.get("approval_digest")),
                    "approval attestation was not digest-bound",
                )
                _require(not rejected.allowed, "operation drift escaped approval scope")
                return {
                    "exact_scope_accepted": accepted.allowed,
                    "approval_attestation_bound": bool(
                        accepted.attestation.get("approval_digest")
                    ),
                    "operation_drift_rejected": not rejected.allowed,
                    "approval_persisted": False,
                }

    probes.append(_probe("production_approval_gate", production_approval_gate))
    evidence = _evidence_document(manifest, probes)
    if evidence["overall_status"] == "passed":
        validate_certification_pair(manifest, evidence)
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the isolated certification probes for one adapter."
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    evidence = run_certification(args.manifest)
    rendered = json.dumps(evidence, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if args.output is None:
        print(rendered, end="")
    else:
        if not args.output.parent.is_dir():
            raise SystemExit("output parent must already exist")
        args.output.write_text(rendered, encoding="utf-8", newline="\n")
    return 0 if evidence["overall_status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
