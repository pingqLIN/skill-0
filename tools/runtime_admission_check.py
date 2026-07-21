"""Fail-closed production admission verifier for Runtime Asset releases."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError

from tools.verify_production_external_controls import (
    DEFAULT_COMPOSE_PATH,
    DEFAULT_POLICY_PATH,
    KEYRING_SCHEMA_PATH,
    TRUSTED_KEYRING_DIGEST_ENV,
    EvidenceVerificationError,
    _current_git_binding,
    _parse_timestamp,
    _resolve_artifact,
    _select_key,
    _sha256_file,
    _verify_signature,
    _validated_sha256,
    verify_external_control_evidence,
)


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_SCHEMA_PATH = ROOT / "schema" / "production-admission-package.schema.json"
APPROVAL_MAX_AGE_HOURS = 24
EVIDENCE_MAX_AGE_HOURS = 168
MAX_VALIDITY_HOURS = 168
ADMISSION_APPROVER_ROLE = "production-admission-approver"


class AdmissionVerificationError(Exception):
    """A stable, non-sensitive reason that blocks production admission."""

    def __init__(self, check_name: str, reason_code: str):
        super().__init__(reason_code)
        self.check_name = check_name
        self.reason_code = reason_code


def _raise(check_name: str, reason_code: str) -> None:
    raise AdmissionVerificationError(check_name, reason_code)


def _validate_schema(instance: Any, schema_path: Path, reason_code: str) -> None:
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        Draft202012Validator(
            schema,
            format_checker=FormatChecker(),
        ).validate(instance)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        raise AdmissionVerificationError("schema_validation", reason_code) from exc


def _read_json_once(
    path: Path, reason_code: str
) -> tuple[dict[str, Any], str]:
    try:
        payload_bytes = path.read_bytes()
        payload = json.loads(payload_bytes)
    except (OSError, json.JSONDecodeError) as exc:
        raise EvidenceVerificationError(reason_code) from exc
    if not isinstance(payload, dict):
        raise EvidenceVerificationError(reason_code)
    digest = f"sha256:{hashlib.sha256(payload_bytes).hexdigest()}"
    return payload, digest


def _load_trusted_keyring(keyring_path: Path) -> tuple[dict[str, Any], str]:
    keyring, observed_digest = _read_json_once(
        keyring_path, "keyring_unavailable"
    )
    try:
        trusted_digest = _validated_sha256(
            os.getenv(TRUSTED_KEYRING_DIGEST_ENV),
            "keyring_trust_anchor_missing_or_invalid",
        )
    except EvidenceVerificationError as exc:
        raise AdmissionVerificationError(
            "keyring_trust_anchor", exc.reason_code
        ) from exc
    if not hmac.compare_digest(observed_digest, trusted_digest):
        _raise("keyring_trust_anchor", "keyring_trust_anchor_mismatch")
    return keyring, trusted_digest


def _verify_window(
    *,
    observed_at: str,
    expires_at: str,
    current_time: datetime,
    max_age_hours: int,
    approved_at: datetime | None = None,
) -> None:
    try:
        observed = _parse_timestamp(observed_at)
        expires = _parse_timestamp(expires_at)
    except EvidenceVerificationError as exc:
        raise AdmissionVerificationError(
            "evidence_freshness", exc.reason_code
        ) from exc

    if observed > current_time:
        _raise("evidence_freshness", "evidence_observed_in_future")
    if current_time - observed > timedelta(hours=max_age_hours):
        _raise("evidence_freshness", "evidence_stale")
    if expires <= current_time:
        _raise("evidence_freshness", "evidence_expired")
    if expires <= observed:
        _raise("evidence_freshness", "evidence_validity_invalid")
    if expires - observed > timedelta(hours=MAX_VALIDITY_HOURS):
        _raise("evidence_freshness", "evidence_validity_too_long")
    if approved_at is not None and observed > approved_at:
        _raise("evidence_freshness", "evidence_postdates_approval")


def _verify_approval_window(
    package: dict[str, Any], current_time: datetime
) -> datetime:
    approval = package["approval"]
    try:
        approved_at = _parse_timestamp(approval["approved_at"])
        expires_at = _parse_timestamp(approval["expires_at"])
        release_created_at = _parse_timestamp(package["release"]["created_at"])
    except EvidenceVerificationError as exc:
        raise AdmissionVerificationError(
            "approval_freshness", exc.reason_code
        ) from exc

    if release_created_at > approved_at:
        _raise("approval_freshness", "approval_predates_release")
    if approved_at > current_time:
        _raise("approval_freshness", "approval_in_future")
    if current_time - approved_at > timedelta(hours=APPROVAL_MAX_AGE_HOURS):
        _raise("approval_freshness", "approval_stale")
    if expires_at <= current_time:
        _raise("approval_freshness", "approval_expired")
    if expires_at <= approved_at:
        _raise("approval_freshness", "approval_validity_invalid")
    if expires_at - approved_at > timedelta(hours=MAX_VALIDITY_HOURS):
        _raise("approval_freshness", "approval_validity_too_long")
    return approved_at


def _verify_operator_signature(
    package: dict[str, Any], keyring: dict[str, Any]
) -> None:
    approval = package["approval"]
    if approval["role"] != ADMISSION_APPROVER_ROLE:
        _raise("operator_authorization", "admission_approver_role_required")
    selection_subject = {
        "evidence_id": package["admission_id"],
        "actor": {
            "operator_id": approval["operator_id"],
            "role": approval["role"],
        },
        "signature": package["signature"],
    }
    try:
        key = _select_key(
            selection_subject,
            keyring,
            package["environment"]["name"],
        )
        _verify_signature(package, key)
    except EvidenceVerificationError as exc:
        reason_code = (
            "approval_revoked"
            if exc.reason_code == "evidence_revoked"
            else f"operator_{exc.reason_code}"
        )
        raise AdmissionVerificationError(
            "operator_signature", reason_code
        ) from exc


def _verify_local_release_binding(
    *,
    package: dict[str, Any],
    repo_root: Path,
    compose_digest: str,
    policy_digest: str,
    trusted_keyring_digest: str,
) -> None:
    binding = package["release_binding"]
    try:
        git_binding = _current_git_binding(repo_root)
    except EvidenceVerificationError as exc:
        raise AdmissionVerificationError("commit_binding", exc.reason_code) from exc

    if binding["git_commit"] != git_binding["git_commit"]:
        _raise("commit_binding", "commit_binding_mismatch")
    if binding["git_tree"] != git_binding["git_tree"]:
        _raise("commit_binding", "git_tree_binding_mismatch")

    local_binding = {
        "compose_sha256": compose_digest,
        "policy_sha256": policy_digest,
        "trusted_keyring_sha256": trusted_keyring_digest,
    }
    for field, observed in local_binding.items():
        if binding[field] != observed:
            _raise("release_binding", f"{field}_mismatch")


def _verify_evidence_references(
    *,
    package: dict[str, Any],
    evidence_root: Path,
    current_time: datetime,
    approved_at: datetime,
) -> dict[str, Any]:
    references: list[dict[str, Any]] = []
    for category in ("security_scan", "regression_test", "rehearsal"):
        references.extend(package["evidence"][category])

    declared_paths = [reference["path"] for reference in references]
    digests = [reference["sha256"] for reference in references]
    if (
        len(declared_paths) != len(set(declared_paths))
        or len(digests) != len(set(digests))
    ):
        _raise("evidence_references", "evidence_reference_duplicated")

    resolved_paths: set[Path] = set()
    for reference in references:
        try:
            artifact_path = _resolve_artifact(evidence_root, reference["path"])
            observed_digest = _sha256_file(artifact_path)
        except EvidenceVerificationError as exc:
            raise AdmissionVerificationError(
                "evidence_references", exc.reason_code
            ) from exc
        if artifact_path in resolved_paths:
            _raise("evidence_references", "evidence_reference_duplicated")
        resolved_paths.add(artifact_path)
        if observed_digest != reference["sha256"]:
            _raise("evidence_references", "evidence_artifact_digest_mismatch")
        _verify_window(
            observed_at=reference["observed_at"],
            expires_at=reference["expires_at"],
            current_time=current_time,
            max_age_hours=EVIDENCE_MAX_AGE_HOURS,
            approved_at=approved_at,
        )

    external_reference = package["evidence"]["external_controls"]
    try:
        bundle_path = _resolve_artifact(evidence_root, external_reference["path"])
        external_evidence, bundle_digest = _read_json_once(
            bundle_path, "external_evidence_bundle_unavailable"
        )
    except EvidenceVerificationError as exc:
        raise AdmissionVerificationError(
            "external_control_evidence", exc.reason_code
        ) from exc
    if bundle_digest != external_reference["sha256"]:
        _raise("external_control_evidence", "external_bundle_digest_mismatch")
    return external_evidence


def _verify_external_bundle_binding(
    *,
    package: dict[str, Any],
    external_evidence: dict[str, Any],
    approved_at: datetime,
) -> None:
    reference = package["evidence"]["external_controls"]
    if external_evidence.get("evidence_id") != reference["evidence_id"]:
        _raise("external_control_evidence", "external_evidence_id_mismatch")
    if external_evidence.get("environment") != {
        "name": package["environment"]["name"],
        "topology": package["environment"]["topology"],
    }:
        _raise("external_control_evidence", "external_environment_mismatch")

    external_binding = external_evidence.get("release_binding")
    if not isinstance(external_binding, dict):
        _raise("external_control_evidence", "external_release_binding_missing")
    package_binding = package["release_binding"]
    if external_binding.get("git_commit") != package_binding["git_commit"]:
        _raise("commit_binding", "external_commit_binding_mismatch")
    if external_binding.get("git_tree") != package_binding["git_tree"]:
        _raise("commit_binding", "external_git_tree_binding_mismatch")
    if external_binding.get("image_digests") != package_binding["image_digests"]:
        _raise("image_digest_binding", "image_digest_binding_mismatch")
    if (
        external_binding.get("model_artifact_digest")
        != package_binding["model_artifact_digest"]
    ):
        _raise("model_artifact_binding", "model_artifact_binding_mismatch")
    if external_binding != package_binding:
        _raise("release_binding", "external_release_binding_mismatch")

    try:
        external_observed_at = _parse_timestamp(external_evidence["observed_at"])
    except (KeyError, EvidenceVerificationError) as exc:
        raise AdmissionVerificationError(
            "external_control_evidence", "external_timestamp_invalid"
        ) from exc
    if external_observed_at > approved_at:
        _raise("external_control_evidence", "external_evidence_postdates_approval")


def verify_admission_package(
    *,
    package: dict[str, Any],
    keyring_path: Path,
    repo_root: Path,
    compose_path: Path,
    policy_path: Path,
    evidence_root: Path,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Verify one exact, signed admission package and all referenced evidence."""

    checks: list[dict[str, str]] = []
    if not isinstance(package.get("signature"), dict) or not package["signature"].get(
        "value_base64"
    ):
        _raise("operator_signature", "operator_signature_missing")
    if package.get("approval", {}).get("role") != ADMISSION_APPROVER_ROLE:
        _raise("operator_authorization", "admission_approver_role_required")

    _validate_schema(package, PACKAGE_SCHEMA_PATH, "admission_schema_invalid")
    try:
        keyring, trusted_keyring_digest = _load_trusted_keyring(keyring_path)
        policy, policy_digest = _read_json_once(policy_path, "policy_unavailable")
        compose_digest = _sha256_file(compose_path)
    except AdmissionVerificationError:
        raise
    except EvidenceVerificationError as exc:
        raise AdmissionVerificationError("input_loading", exc.reason_code) from exc
    _validate_schema(keyring, KEYRING_SCHEMA_PATH, "keyring_schema_invalid")
    checks.append({"name": "schema_validation", "result": "PASS"})
    checks.append({"name": "keyring_trust_anchor", "result": "PASS"})

    current_time = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    approved_at = _verify_approval_window(package, current_time)
    checks.append({"name": "approval_freshness", "result": "PASS"})

    _verify_operator_signature(package, keyring)
    checks.append({"name": "operator_signature", "result": "PASS"})
    checks.append({"name": "revocation_state", "result": "PASS"})

    _verify_local_release_binding(
        package=package,
        repo_root=repo_root,
        compose_digest=compose_digest,
        policy_digest=policy_digest,
        trusted_keyring_digest=trusted_keyring_digest,
    )
    checks.append({"name": "commit_binding", "result": "PASS"})
    checks.append({"name": "release_binding", "result": "PASS"})

    external_evidence = _verify_evidence_references(
        package=package,
        evidence_root=evidence_root,
        current_time=current_time,
        approved_at=approved_at,
    )
    checks.append({"name": "evidence_references", "result": "PASS"})
    checks.append({"name": "evidence_freshness", "result": "PASS"})

    _verify_external_bundle_binding(
        package=package,
        external_evidence=external_evidence,
        approved_at=approved_at,
    )
    checks.append({"name": "image_digest_binding", "result": "PASS"})
    checks.append({"name": "model_artifact_binding", "result": "PASS"})

    try:
        external_report = verify_external_control_evidence(
            evidence=external_evidence,
            keyring=keyring,
            policy=policy,
            expected_binding=package["release_binding"],
            expected_environment=package["environment"]["name"],
            evidence_root=evidence_root,
            now=current_time,
        )
    except EvidenceVerificationError as exc:
        reason_code = (
            "external_evidence_revoked"
            if exc.reason_code == "evidence_revoked"
            else f"external_{exc.reason_code}"
        )
        raise AdmissionVerificationError(
            "external_control_evidence", reason_code
        ) from exc
    if external_report.get("status") != "VERIFIED":
        _raise("external_control_evidence", "external_evidence_not_verified")
    checks.append({"name": "external_control_evidence", "result": "PASS"})

    return {
        "status": "PASS",
        "release_gate": "PRODUCTION_ADMISSION_VERIFIED",
        "release": package["release"]["release_id"],
        "admission_id": package["admission_id"],
        "checks": checks,
        "limitations": [
            "operator_attestation_not_independent_live_deployment_observation",
            "admission_does_not_expand_dry_run_only_runtime_authority",
        ],
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Verify a signed Runtime Asset production admission package. "
            "Any failed or unknown check exits non-zero and blocks admission."
        )
    )
    parser.add_argument("package", type=Path)
    parser.add_argument("--keyring", type=Path, required=True)
    parser.add_argument("--evidence-root", type=Path)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY_PATH)
    parser.add_argument("--compose-file", type=Path, default=DEFAULT_COMPOSE_PATH)
    return parser


def _failure_report(
    *,
    release: str | None,
    admission_id: str | None,
    error: AdmissionVerificationError,
) -> dict[str, Any]:
    return {
        "status": "FAIL",
        "release_gate": "BLOCKED",
        "release": release,
        "admission_id": admission_id,
        "checks": [
            {
                "name": error.check_name,
                "result": "FAIL",
                "reason_code": error.reason_code,
            }
        ],
        "reason_codes": [error.reason_code],
    }


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    package: dict[str, Any] = {}
    try:
        package, _ = _read_json_once(
            args.package.resolve(), "admission_package_unavailable"
        )
        keyring_path = args.keyring.resolve()
        policy_path = args.policy.resolve()
        report = verify_admission_package(
            package=package,
            keyring_path=keyring_path,
            repo_root=args.repo_root.resolve(),
            compose_path=args.compose_file.resolve(),
            policy_path=policy_path,
            evidence_root=(args.evidence_root or args.package.parent).resolve(),
        )
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 0
    except AdmissionVerificationError as exc:
        report = _failure_report(
            release=package.get("release", {}).get("release_id"),
            admission_id=package.get("admission_id"),
            error=exc,
        )
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 2
    except EvidenceVerificationError as exc:
        error = AdmissionVerificationError("input_loading", exc.reason_code)
        report = _failure_report(
            release=package.get("release", {}).get("release_id"),
            admission_id=package.get("admission_id"),
            error=error,
        )
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 2
    except Exception:
        error = AdmissionVerificationError(
            "verifier_execution", "internal_verifier_error"
        )
        report = _failure_report(
            release=package.get("release", {}).get("release_id"),
            admission_id=package.get("admission_id"),
            error=error,
        )
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 2


if __name__ == "__main__":
    sys.exit(main())
