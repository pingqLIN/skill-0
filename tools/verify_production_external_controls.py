"""Fail-closed verifier for externally supplied production-control evidence."""

from __future__ import annotations

import argparse
import base64
import binascii
import copy
import hashlib
import hmac
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_SCHEMA_PATH = (
    ROOT / "schema" / "production-external-control-evidence.schema.json"
)
KEYRING_SCHEMA_PATH = (
    ROOT / "schema" / "production-external-control-keyring.schema.json"
)
DEFAULT_POLICY_PATH = ROOT / "docs" / "contracts" / "production-security-policy-v1.json"
DEFAULT_COMPOSE_PATH = ROOT / "docker-compose.prod.yml"
EXPECTED_IMAGE_NAMES = {"api", "dashboard", "web"}
TRUSTED_KEYRING_DIGEST_ENV = "SKILL0_EXTERNAL_CONTROL_TRUSTED_KEYRING_SHA256"


class EvidenceVerificationError(Exception):
    """A stable, non-sensitive reason that blocks the release gate."""

    def __init__(self, reason_code: str):
        super().__init__(reason_code)
        self.reason_code = reason_code


def canonical_signed_payload(evidence: dict[str, Any]) -> bytes:
    payload = copy.deepcopy(evidence)
    payload.pop("signature", None)
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise EvidenceVerificationError("artifact_unavailable") from exc
    return f"sha256:{digest.hexdigest()}"


def _validated_sha256(value: str | None, reason_code: str) -> str:
    if value is None or not value.startswith("sha256:"):
        raise EvidenceVerificationError(reason_code)
    digest_value = value.removeprefix("sha256:")
    if len(digest_value) != 64:
        raise EvidenceVerificationError(reason_code)
    try:
        int(digest_value, 16)
    except ValueError as exc:
        raise EvidenceVerificationError(reason_code) from exc
    if value != value.lower():
        raise EvidenceVerificationError(reason_code)
    return value


def _verify_keyring_trust_anchor(keyring_path: Path) -> str:
    trusted_digest = _validated_sha256(
        os.getenv(TRUSTED_KEYRING_DIGEST_ENV),
        "keyring_trust_anchor_missing_or_invalid",
    )
    observed_digest = _sha256_file(keyring_path)
    if not hmac.compare_digest(observed_digest, trusted_digest):
        raise EvidenceVerificationError("keyring_trust_anchor_mismatch")
    return trusted_digest


def _parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EvidenceVerificationError("timestamp_invalid") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise EvidenceVerificationError("timestamp_invalid")
    return parsed.astimezone(timezone.utc)


def _validate_schema(instance: Any, schema_path: Path, reason_code: str) -> None:
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        Draft202012Validator(schema).validate(instance)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        raise EvidenceVerificationError(reason_code) from exc


def _decode_base64(value: str, reason_code: str) -> bytes:
    try:
        return base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise EvidenceVerificationError(reason_code) from exc


def _resolve_artifact(evidence_root: Path, reference: str) -> Path:
    relative = PurePosixPath(reference)
    if relative.is_absolute() or not relative.parts or any(
        part in {"", ".", ".."} for part in relative.parts
    ):
        raise EvidenceVerificationError("artifact_reference_invalid")

    root = evidence_root.resolve()
    candidate = root.joinpath(*relative.parts).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise EvidenceVerificationError("artifact_reference_invalid") from exc
    if not candidate.is_file():
        raise EvidenceVerificationError("artifact_unavailable")
    return candidate


def _select_key(
    evidence: dict[str, Any],
    keyring: dict[str, Any],
    expected_environment: str,
) -> dict[str, Any]:
    key_id = evidence["signature"]["key_id"]
    matching_keys = [key for key in keyring["keys"] if key["key_id"] == key_id]
    if len(matching_keys) != 1:
        raise EvidenceVerificationError("signing_key_unknown_or_duplicated")

    key = matching_keys[0]
    if key["revoked"]:
        raise EvidenceVerificationError("signing_key_revoked")
    if evidence["evidence_id"] in keyring["revoked_evidence_ids"]:
        raise EvidenceVerificationError("evidence_revoked")
    actor = evidence["actor"]
    if key["operator_id"] != actor["operator_id"]:
        raise EvidenceVerificationError("signer_actor_mismatch")
    if actor["role"] not in key["roles"]:
        raise EvidenceVerificationError("signer_role_not_authorized")
    if expected_environment not in key["environments"]:
        raise EvidenceVerificationError("signer_environment_not_authorized")
    return key


def _verify_signature(evidence: dict[str, Any], key: dict[str, Any]) -> None:
    public_key_bytes = _decode_base64(
        key["public_key_base64"], "public_key_encoding_invalid"
    )
    signature_bytes = _decode_base64(
        evidence["signature"]["value_base64"], "signature_encoding_invalid"
    )
    try:
        public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
        public_key.verify(signature_bytes, canonical_signed_payload(evidence))
    except (ValueError, InvalidSignature) as exc:
        raise EvidenceVerificationError("signature_invalid") from exc


def _verify_time_window(
    evidence: dict[str, Any],
    current_time: datetime,
    max_age_hours: int,
    max_validity_hours: int,
) -> None:
    observed_at = _parse_timestamp(evidence["observed_at"])
    expires_at = _parse_timestamp(evidence["expires_at"])
    if observed_at > current_time:
        raise EvidenceVerificationError("evidence_observed_in_future")
    if current_time - observed_at > timedelta(hours=max_age_hours):
        raise EvidenceVerificationError("evidence_stale")
    if expires_at <= current_time:
        raise EvidenceVerificationError("evidence_expired")
    if expires_at <= observed_at:
        raise EvidenceVerificationError("evidence_validity_invalid")
    if expires_at - observed_at > timedelta(hours=max_validity_hours):
        raise EvidenceVerificationError("evidence_validity_too_long")


def _verify_control_set(
    evidence: dict[str, Any], policy: dict[str, Any]
) -> list[str]:
    required_controls = policy.get("required_external_controls")
    if not isinstance(required_controls, list) or not all(
        isinstance(control, str) for control in required_controls
    ):
        raise EvidenceVerificationError("policy_controls_invalid")
    control_ids = [control["control_id"] for control in evidence["controls"]]
    if len(control_ids) != len(set(control_ids)):
        raise EvidenceVerificationError("control_id_duplicated")
    if set(control_ids) != set(required_controls):
        raise EvidenceVerificationError("control_set_mismatch")
    return control_ids


def _verify_attachments(evidence: dict[str, Any], evidence_root: Path) -> int:
    attachment_count = 0
    for control in evidence["controls"]:
        for attachment in control["artifact_refs"]:
            artifact_path = _resolve_artifact(evidence_root, attachment["path"])
            if _sha256_file(artifact_path) != attachment["sha256"]:
                raise EvidenceVerificationError("artifact_digest_mismatch")
            attachment_count += 1
    return attachment_count


def verify_external_control_evidence(
    *,
    evidence: dict[str, Any],
    keyring: dict[str, Any],
    policy: dict[str, Any],
    expected_binding: dict[str, Any],
    expected_environment: str,
    evidence_root: Path,
    now: datetime | None = None,
    max_age_hours: int = 24,
    max_validity_hours: int = 168,
) -> dict[str, Any]:
    """Verify signature, freshness, release scope, controls, and attachments."""

    _validate_schema(evidence, EVIDENCE_SCHEMA_PATH, "evidence_schema_invalid")
    _validate_schema(keyring, KEYRING_SCHEMA_PATH, "keyring_schema_invalid")

    current_time = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    _verify_time_window(evidence, current_time, max_age_hours, max_validity_hours)

    if evidence["environment"]["name"] != expected_environment:
        raise EvidenceVerificationError("environment_mismatch")
    if evidence["release_binding"] != expected_binding:
        raise EvidenceVerificationError("release_binding_mismatch")

    control_ids = _verify_control_set(evidence, policy)
    key = _select_key(evidence, keyring, expected_environment)
    _verify_signature(evidence, key)
    attachment_count = _verify_attachments(evidence, evidence_root)

    return {
        "status": "VERIFIED",
        "release_gate": "ELIGIBLE_FOR_REMAINING_GATES",
        "conclusion": "external_evidence_integrity_and_scope_verified",
        "evidence_id": evidence["evidence_id"],
        "environment": expected_environment,
        "verified_controls": sorted(control_ids),
        "verified_attachment_count": attachment_count,
        "limitations": ["physical_control_state_not_independently_observed"],
    }


def _load_json(path: Path, reason_code: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvidenceVerificationError(reason_code) from exc
    if not isinstance(payload, dict):
        raise EvidenceVerificationError(reason_code)
    return payload


def _git_value(repo_root: Path, *arguments: str) -> str:
    try:
        result = subprocess.run(
            ["git", *arguments],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise EvidenceVerificationError("git_state_unavailable") from exc
    return result.stdout.strip()


def _current_git_binding(repo_root: Path) -> dict[str, str]:
    if _git_value(
        repo_root,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
    ):
        raise EvidenceVerificationError("source_tree_dirty")
    return {
        "git_commit": _git_value(repo_root, "rev-parse", "HEAD"),
        "git_tree": _git_value(repo_root, "rev-parse", "HEAD^{tree}"),
    }


def _parse_image_digests(values: list[str]) -> dict[str, str]:
    image_digests: dict[str, str] = {}
    for value in values:
        name, separator, digest = value.partition("=")
        if not separator or name in image_digests:
            raise EvidenceVerificationError("image_digest_argument_invalid")
        if not digest.startswith("sha256:") or len(digest) != 71:
            raise EvidenceVerificationError("image_digest_argument_invalid")
        try:
            int(digest.removeprefix("sha256:"), 16)
        except ValueError as exc:
            raise EvidenceVerificationError("image_digest_argument_invalid") from exc
        image_digests[name] = digest
    if set(image_digests) != EXPECTED_IMAGE_NAMES:
        raise EvidenceVerificationError("image_digest_set_invalid")
    return image_digests


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Verify signed, release-bound external production-control evidence. "
            "UNKNOWN exits non-zero and blocks release."
        )
    )
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--keyring", type=Path, required=True)
    parser.add_argument("--evidence-root", type=Path)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY_PATH)
    parser.add_argument("--compose-file", type=Path, default=DEFAULT_COMPOSE_PATH)
    parser.add_argument("--environment", required=True)
    parser.add_argument(
        "--image-digest",
        action="append",
        required=True,
        metavar="SERVICE=SHA256",
    )
    parser.add_argument("--model-artifact-digest", required=True)
    parser.add_argument("--max-age-hours", type=int, default=24)
    parser.add_argument("--max-validity-hours", type=int, default=168)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.max_age_hours <= 0 or args.max_validity_hours <= 0:
            raise EvidenceVerificationError("validity_argument_invalid")
        model_artifact_digest = _validated_sha256(
            args.model_artifact_digest,
            "model_digest_argument_invalid",
        )

        repo_root = args.repo_root.resolve()
        policy_path = args.policy.resolve()
        compose_path = args.compose_file.resolve()
        keyring_path = args.keyring.resolve()
        trusted_keyring_digest = _verify_keyring_trust_anchor(keyring_path)
        binding = {
            **_current_git_binding(repo_root),
            "compose_sha256": _sha256_file(compose_path),
            "policy_sha256": _sha256_file(policy_path),
            "trusted_keyring_sha256": trusted_keyring_digest,
            "model_artifact_digest": model_artifact_digest,
            "image_digests": _parse_image_digests(args.image_digest),
        }
        evidence = _load_json(args.bundle.resolve(), "evidence_bundle_unavailable")
        keyring = _load_json(keyring_path, "keyring_unavailable")
        policy = _load_json(policy_path, "policy_unavailable")
        report = verify_external_control_evidence(
            evidence=evidence,
            keyring=keyring,
            policy=policy,
            expected_binding=binding,
            expected_environment=args.environment,
            evidence_root=(args.evidence_root or args.bundle.parent).resolve(),
            max_age_hours=args.max_age_hours,
            max_validity_hours=args.max_validity_hours,
        )
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 0
    except EvidenceVerificationError as exc:
        report = {
            "status": "UNKNOWN",
            "release_gate": "BLOCKED",
            "reason_codes": [exc.reason_code],
        }
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 2


if __name__ == "__main__":
    sys.exit(main())
