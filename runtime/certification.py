from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any, Callable, Protocol
from uuid import uuid4

from .digest import canonical_digest
from .validators import load_json, validate_schema


REPO_ROOT = Path(__file__).resolve().parents[1]
CERTIFICATION_SCHEMA_PATH = REPO_ROOT / "schema" / "adapter-certification.schema.json"
CERTIFICATION_EVIDENCE_SCHEMA_PATH = (
    REPO_ROOT / "schema" / "adapter-certification-evidence.schema.json"
)
PRODUCTION_APPROVAL_SCHEMA_PATH = (
    REPO_ROOT / "schema" / "adapter-production-approval.schema.json"
)

REQUIRED_CERTIFICATION_PROBES = frozenset(
    {
        "credential_boundary",
        "idempotency_replay",
        "idempotency_conflict",
        "reconciliation_after_ambiguous_outcome",
        "compensation_evidence",
        "rate_limit",
        "production_approval_gate",
    }
)


class AdapterCertificationError(ValueError):
    pass


class ReconciliationStatus(StrEnum):
    NOT_FOUND = "not_found"
    APPLIED = "applied"
    COMPENSATED = "compensated"
    DIVERGED = "diverged"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ReconciliationResult:
    status: ReconciliationStatus
    external_resource_id: str | None = None
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AdapterAdmissionDecision:
    allowed: bool
    reason: str
    attestation: dict[str, Any] = field(default_factory=dict)


class ProductionAdapterApprovalGate(Protocol):
    def evaluate(
        self,
        adapter: Any,
        action_bindings: list[dict[str, Any]],
    ) -> AdapterAdmissionDecision: ...


def file_digest(path: str | Path) -> str:
    digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    return f"sha256:{digest}"


def load_certification_manifest(path: str | Path) -> dict[str, Any]:
    document = load_json(path)
    validate_schema(document, load_json(CERTIFICATION_SCHEMA_PATH))
    repo_root = REPO_ROOT.resolve()
    artifact_path = (repo_root / document["adapter"]["artifact_path"]).resolve()
    if not artifact_path.is_relative_to(repo_root):
        raise AdapterCertificationError("adapter artifact path escapes the repository")
    if file_digest(artifact_path) != document["adapter"]["artifact_digest"]:
        raise AdapterCertificationError("adapter artifact digest does not match the manifest")
    return document


def load_certification_evidence(path: str | Path) -> dict[str, Any]:
    document = load_json(path)
    validate_schema(document, load_json(CERTIFICATION_EVIDENCE_SCHEMA_PATH))
    return document


def validate_certification_pair(
    manifest: dict[str, Any], evidence: dict[str, Any]
) -> None:
    validate_schema(manifest, load_json(CERTIFICATION_SCHEMA_PATH))
    validate_schema(evidence, load_json(CERTIFICATION_EVIDENCE_SCHEMA_PATH))
    if evidence["adapter"] != {
        name: manifest["adapter"][name]
        for name in ("id", "version", "kind", "target", "artifact_digest")
    }:
        raise AdapterCertificationError("certification evidence adapter identity drift")
    if evidence["manifest_digest"] != canonical_digest(manifest):
        raise AdapterCertificationError("certification evidence manifest digest drift")
    if evidence["overall_status"] != "passed":
        raise AdapterCertificationError("adapter certification evidence has not passed")
    probe_names = [probe["name"] for probe in evidence["probes"]]
    if len(probe_names) != len(set(probe_names)):
        raise AdapterCertificationError("certification evidence contains duplicate probes")
    probe_results = {probe["name"]: probe["status"] for probe in evidence["probes"]}
    missing = sorted(REQUIRED_CERTIFICATION_PROBES - set(probe_results))
    failed = sorted(
        name
        for name in REQUIRED_CERTIFICATION_PROBES
        if probe_results.get(name) != "passed"
    )
    if missing or failed:
        raise AdapterCertificationError(
            f"adapter certification probes are incomplete: missing={missing}, failed={failed}"
        )


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise AdapterCertificationError("approval timestamps must include a timezone")
    return parsed.astimezone(timezone.utc)


def _signature_payload(record: dict[str, Any]) -> bytes:
    unsigned = {key: value for key, value in record.items() if key != "signature"}
    return json.dumps(
        unsigned,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def sign_production_approval(record: dict[str, Any], *, key: str) -> dict[str, Any]:
    if len(key) < 32:
        raise AdapterCertificationError(
            "adapter approval signing key must contain at least 32 characters"
        )
    signed = dict(record)
    signed["signature"] = {
        "algorithm": "hmac-sha256",
        "value": hmac.new(
            key.encode("utf-8"), _signature_payload(signed), hashlib.sha256
        ).hexdigest(),
    }
    validate_schema(signed, load_json(PRODUCTION_APPROVAL_SCHEMA_PATH))
    return signed


def verify_production_approval_signature(record: dict[str, Any], *, key: str) -> bool:
    if len(key) < 32:
        return False
    signature = record.get("signature", {})
    if signature.get("algorithm") != "hmac-sha256":
        return False
    expected = hmac.new(
        key.encode("utf-8"), _signature_payload(record), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(str(signature.get("value", "")), expected)


def build_production_approval(
    manifest: dict[str, Any],
    evidence: dict[str, Any],
    *,
    environment: str,
    approved_by: str,
    expires_at: str,
    key: str,
    approved_at: str | None = None,
) -> dict[str, Any]:
    validate_certification_pair(manifest, evidence)
    approved_at = approved_at or datetime.now(timezone.utc).isoformat()
    if _parse_utc(expires_at) <= _parse_utc(approved_at):
        raise AdapterCertificationError("adapter approval must expire after approval time")
    record = {
        "schema_version": "1.0.0",
        "approval_id": str(uuid4()),
        "decision": "approved",
        "adapter": {
            name: manifest["adapter"][name]
            for name in (
                "id",
                "version",
                "kind",
                "target",
                "artifact_digest",
            )
        },
        "manifest_digest": canonical_digest(manifest),
        "certification_evidence_digest": canonical_digest(evidence),
        "environment": environment,
        "allowed_operations": manifest["production_approval"]["allowed_operations"],
        "approved_by": approved_by,
        "approved_at": approved_at,
        "expires_at": expires_at,
    }
    return sign_production_approval(record, key=key)


def build_production_revocation(
    approval: dict[str, Any],
    *,
    revoked_by: str,
    key: str,
    revoked_at: str | None = None,
) -> dict[str, Any]:
    validate_schema(approval, load_json(PRODUCTION_APPROVAL_SCHEMA_PATH))
    if not verify_production_approval_signature(approval, key=key):
        raise AdapterCertificationError("cannot revoke an approval with an invalid signature")
    if approval["decision"] != "approved":
        raise AdapterCertificationError("only an active approval record can be revoked")
    record = {name: value for name, value in approval.items() if name != "signature"}
    record["decision"] = "revoked"
    record["revoked_by"] = revoked_by
    record["revoked_at"] = revoked_at or datetime.now(timezone.utc).isoformat()
    return sign_production_approval(record, key=key)


class SignedProductionApprovalGate:
    """Fail-closed per-adapter, per-environment production admission."""

    def __init__(
        self,
        approval: dict[str, Any],
        *,
        key: str,
        environment: str,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.approval = approval
        self.key = key
        self.environment = environment
        self.now = now or (lambda: datetime.now(timezone.utc))

    def evaluate(
        self,
        adapter: Any,
        action_bindings: list[dict[str, Any]],
    ) -> AdapterAdmissionDecision:
        try:
            validate_schema(
                self.approval, load_json(PRODUCTION_APPROVAL_SCHEMA_PATH)
            )
        except Exception:
            return AdapterAdmissionDecision(False, "adapter approval schema validation failed")
        if not verify_production_approval_signature(self.approval, key=self.key):
            return AdapterAdmissionDecision(False, "adapter approval signature is invalid")
        if self.approval["decision"] != "approved":
            return AdapterAdmissionDecision(False, "adapter approval is not active")
        if self.approval["environment"] != self.environment:
            return AdapterAdmissionDecision(False, "adapter approval environment mismatch")
        try:
            now = self.now().astimezone(timezone.utc)
            approved_at = _parse_utc(self.approval["approved_at"])
            expires_at = _parse_utc(self.approval["expires_at"])
        except (TypeError, ValueError, AdapterCertificationError):
            return AdapterAdmissionDecision(False, "adapter approval timestamps are invalid")
        if now < approved_at:
            return AdapterAdmissionDecision(False, "adapter approval is not yet active")
        if now >= expires_at:
            return AdapterAdmissionDecision(False, "adapter approval has expired")

        expected_identity = {
            "id": getattr(adapter, "adapter_id", None),
            "version": getattr(adapter, "adapter_version", None),
            "kind": getattr(adapter, "adapter_kind", None),
            "target": getattr(adapter, "adapter_target", None),
            "artifact_digest": getattr(adapter, "adapter_artifact_digest", None),
        }
        if self.approval["adapter"] != expected_identity:
            return AdapterAdmissionDecision(False, "runtime adapter identity drift")
        if self.approval["manifest_digest"] != getattr(
            adapter, "certification_manifest_digest", None
        ):
            return AdapterAdmissionDecision(False, "runtime adapter manifest drift")

        allowed = {
            (item["action_id"], item["resource_kind"], item["operation"])
            for item in self.approval["allowed_operations"]
        }
        requested = {
            (
                binding["action_id"],
                binding["effect"]["resource_kind"],
                binding["effect"]["operation"],
            )
            for binding in action_bindings
            if binding.get("role", "primary") == "primary"
        }
        if not requested or not requested.issubset(allowed):
            return AdapterAdmissionDecision(False, "runtime operation is outside adapter approval scope")
        if any(
            binding.get("adapter", {}).get("kind") != expected_identity["kind"]
            or binding.get("adapter", {}).get("target") != expected_identity["target"]
            for binding in action_bindings
        ):
            return AdapterAdmissionDecision(False, "runtime binding does not match approved adapter")

        attestation = {
            "approved": True,
            "approval_id": self.approval["approval_id"],
            "approval_digest": canonical_digest(self.approval),
            "adapter_id": expected_identity["id"],
            "adapter_version": expected_identity["version"],
            "artifact_digest": expected_identity["artifact_digest"],
            "manifest_digest": self.approval["manifest_digest"],
            "certification_evidence_digest": self.approval[
                "certification_evidence_digest"
            ],
            "environment": self.environment,
            "approved_by": self.approval["approved_by"],
            "approved_at": self.approval["approved_at"],
            "expires_at": self.approval["expires_at"],
        }
        return AdapterAdmissionDecision(True, "adapter production approval verified", attestation)
