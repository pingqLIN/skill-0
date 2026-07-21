from __future__ import annotations

import base64
import hashlib
import json
import subprocess
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from tools.verify_production_external_controls import (
    EvidenceVerificationError,
    TRUSTED_KEYRING_DIGEST_ENV,
    _current_git_binding,
    _verify_keyring_trust_anchor,
    canonical_signed_payload,
    verify_external_control_evidence,
)


NOW = datetime(2026, 7, 21, 8, 0, tzinfo=timezone.utc)
EVIDENCE_ID = "123e4567-e89b-42d3-a456-426614174000"
CONTROL_IDS = [
    "tls-termination",
    "network-acl",
    "secret-manager",
    "unique-high-entropy-credentials",
    "volume-encryption-and-file-permissions",
    "encrypted-separated-backups",
    "host-and-container-admin-restriction",
    "central-log-retention-and-access-control",
]


def _digest(data: bytes) -> str:
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def _fixture(tmp_path: Path):
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    expected_binding = {
        "git_commit": "1" * 40,
        "git_tree": "2" * 40,
        "compose_sha256": "sha256:" + "3" * 64,
        "policy_sha256": "sha256:" + "4" * 64,
        "trusted_keyring_sha256": "sha256:" + "a" * 64,
        "model_artifact_digest": "sha256:" + "5" * 64,
        "image_digests": {
            "api": "sha256:" + "6" * 64,
            "dashboard": "sha256:" + "7" * 64,
            "web": "sha256:" + "8" * 64,
        },
    }
    controls = []
    for index, control_id in enumerate(CONTROL_IDS):
        artifact_path = tmp_path / "artifacts" / f"control-{index}.json"
        artifact_path.parent.mkdir(exist_ok=True)
        artifact_bytes = f'{{"synthetic_control":"{control_id}"}}\n'.encode()
        artifact_path.write_bytes(artifact_bytes)
        controls.append(
            {
                "control_id": control_id,
                "status": "verified",
                "artifact_refs": [
                    {
                        "path": f"artifacts/control-{index}.json",
                        "sha256": _digest(artifact_bytes),
                    }
                ],
            }
        )

    evidence = {
        "schema_version": "1.0.0",
        "evidence_id": EVIDENCE_ID,
        "environment": {
            "name": "production-primary",
            "topology": "single-host-docker-compose",
        },
        "actor": {"operator_id": "operator-1", "role": "release-security"},
        "observed_at": (NOW - timedelta(hours=1)).isoformat(),
        "expires_at": (NOW + timedelta(hours=23)).isoformat(),
        "release_binding": deepcopy(expected_binding),
        "controls": controls,
        "signature": {
            "algorithm": "Ed25519",
            "key_id": "release-key-1",
            "value_base64": "pending",
        },
    }
    keyring = {
        "schema_version": "1.0.0",
        "keys": [
            {
                "key_id": "release-key-1",
                "operator_id": "operator-1",
                "roles": ["release-security"],
                "environments": ["production-primary"],
                "public_key_base64": base64.b64encode(public_key).decode(),
                "revoked": False,
            }
        ],
        "revoked_evidence_ids": [],
    }
    policy = {"required_external_controls": CONTROL_IDS}
    _resign(evidence, private_key)
    return evidence, keyring, policy, expected_binding, private_key


def _resign(evidence: dict, private_key: Ed25519PrivateKey) -> None:
    signature = private_key.sign(canonical_signed_payload(evidence))
    evidence["signature"]["value_base64"] = base64.b64encode(signature).decode()


def _verify(tmp_path: Path, evidence, keyring, policy, expected_binding):
    return verify_external_control_evidence(
        evidence=evidence,
        keyring=keyring,
        policy=policy,
        expected_binding=expected_binding,
        expected_environment="production-primary",
        evidence_root=tmp_path,
        now=NOW,
    )


def _assert_reason(reason: str, callback) -> None:
    with pytest.raises(EvidenceVerificationError) as captured:
        callback()
    assert captured.value.reason_code == reason


def test_valid_signed_release_bound_external_evidence_passes(tmp_path):
    evidence, keyring, policy, binding, _ = _fixture(tmp_path)

    report = _verify(tmp_path, evidence, keyring, policy, binding)

    assert report["status"] == "VERIFIED"
    assert report["release_gate"] == "ELIGIBLE_FOR_REMAINING_GATES"
    assert report["verified_controls"] == sorted(CONTROL_IDS)
    assert report["verified_attachment_count"] == len(CONTROL_IDS)
    assert report["limitations"] == [
        "physical_control_state_not_independently_observed"
    ]


def test_missing_required_control_fails_closed(tmp_path):
    evidence, keyring, policy, binding, private_key = _fixture(tmp_path)
    evidence["controls"].pop()
    _resign(evidence, private_key)

    _assert_reason(
        "control_set_mismatch",
        lambda: _verify(tmp_path, evidence, keyring, policy, binding),
    )


def test_duplicate_control_fails_closed(tmp_path):
    evidence, keyring, policy, binding, private_key = _fixture(tmp_path)
    evidence["controls"][-1] = deepcopy(evidence["controls"][0])
    _resign(evidence, private_key)

    _assert_reason(
        "control_id_duplicated",
        lambda: _verify(tmp_path, evidence, keyring, policy, binding),
    )


def test_stale_evidence_fails_closed(tmp_path):
    evidence, keyring, policy, binding, private_key = _fixture(tmp_path)
    evidence["observed_at"] = (NOW - timedelta(hours=25)).isoformat()
    evidence["expires_at"] = (NOW + timedelta(hours=1)).isoformat()
    _resign(evidence, private_key)

    _assert_reason(
        "evidence_stale",
        lambda: _verify(tmp_path, evidence, keyring, policy, binding),
    )


def test_expired_evidence_fails_closed(tmp_path):
    evidence, keyring, policy, binding, private_key = _fixture(tmp_path)
    evidence["expires_at"] = NOW.isoformat()
    _resign(evidence, private_key)

    _assert_reason(
        "evidence_expired",
        lambda: _verify(tmp_path, evidence, keyring, policy, binding),
    )


def test_wrong_release_binding_fails_closed(tmp_path):
    evidence, keyring, policy, binding, private_key = _fixture(tmp_path)
    evidence["release_binding"]["git_commit"] = "9" * 40
    _resign(evidence, private_key)

    _assert_reason(
        "release_binding_mismatch",
        lambda: _verify(tmp_path, evidence, keyring, policy, binding),
    )


def test_unknown_or_revoked_key_fails_closed(tmp_path):
    evidence, keyring, policy, binding, private_key = _fixture(tmp_path)
    evidence["signature"]["key_id"] = "unknown-key"
    _resign(evidence, private_key)
    _assert_reason(
        "signing_key_unknown_or_duplicated",
        lambda: _verify(tmp_path, evidence, keyring, policy, binding),
    )

    evidence, keyring, policy, binding, _ = _fixture(tmp_path)
    keyring["keys"][0]["revoked"] = True
    _assert_reason(
        "signing_key_revoked",
        lambda: _verify(tmp_path, evidence, keyring, policy, binding),
    )


def test_tampered_signature_fails_closed(tmp_path):
    evidence, keyring, policy, binding, _ = _fixture(tmp_path)
    evidence["signature"]["value_base64"] = base64.b64encode(b"x" * 64).decode()

    _assert_reason(
        "signature_invalid",
        lambda: _verify(tmp_path, evidence, keyring, policy, binding),
    )


def test_tampered_attachment_fails_closed(tmp_path):
    evidence, keyring, policy, binding, _ = _fixture(tmp_path)
    (tmp_path / "artifacts" / "control-0.json").write_text(
        "tampered\n", encoding="utf-8"
    )

    _assert_reason(
        "artifact_digest_mismatch",
        lambda: _verify(tmp_path, evidence, keyring, policy, binding),
    )


def test_attachment_path_escape_fails_closed(tmp_path):
    evidence, keyring, policy, binding, private_key = _fixture(tmp_path)
    evidence["controls"][0]["artifact_refs"][0]["path"] = "../outside.json"
    _resign(evidence, private_key)

    _assert_reason(
        "artifact_reference_invalid",
        lambda: _verify(tmp_path, evidence, keyring, policy, binding),
    )


def test_keyring_requires_independently_injected_digest_anchor(tmp_path, monkeypatch):
    keyring_path = tmp_path / "keyring.json"
    keyring_path.write_text(json.dumps({"synthetic": True}), encoding="utf-8")
    observed_digest = _digest(keyring_path.read_bytes())

    monkeypatch.delenv(TRUSTED_KEYRING_DIGEST_ENV, raising=False)
    _assert_reason(
        "keyring_trust_anchor_missing_or_invalid",
        lambda: _verify_keyring_trust_anchor(keyring_path),
    )

    monkeypatch.setenv(TRUSTED_KEYRING_DIGEST_ENV, "sha256:" + "0" * 64)
    _assert_reason(
        "keyring_trust_anchor_mismatch",
        lambda: _verify_keyring_trust_anchor(keyring_path),
    )

    monkeypatch.setenv(TRUSTED_KEYRING_DIGEST_ENV, observed_digest)
    assert _verify_keyring_trust_anchor(keyring_path) == observed_digest


def test_git_binding_rejects_untracked_source(tmp_path):
    subprocess.run(["git", "init", "--quiet"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "config", "user.email", "synthetic@example.invalid"],
        cwd=tmp_path,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Synthetic Test"],
        cwd=tmp_path,
        check=True,
    )
    (tmp_path / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "--quiet", "-m", "synthetic fixture"],
        cwd=tmp_path,
        check=True,
    )

    binding = _current_git_binding(tmp_path)
    assert len(binding["git_commit"]) == 40
    assert len(binding["git_tree"]) == 40

    (tmp_path / "untracked.py").write_text("print('drift')\n", encoding="utf-8")
    _assert_reason(
        "source_tree_dirty",
        lambda: _current_git_binding(tmp_path),
    )
