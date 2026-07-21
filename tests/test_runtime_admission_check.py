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
from jsonschema import Draft202012Validator, FormatChecker

from tools.runtime_admission_check import (
    AdmissionVerificationError,
    main,
    verify_admission_package,
)
from tools.verify_production_external_controls import (
    TRUSTED_KEYRING_DIGEST_ENV,
    canonical_signed_payload,
)


NOW = datetime(2026, 7, 21, 8, 0, tzinfo=timezone.utc)
ADMISSION_ID = "123e4567-e89b-42d3-a456-426614174001"
EXTERNAL_EVIDENCE_ID = "123e4567-e89b-42d3-a456-426614174002"
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


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _public_key_base64(private_key: Ed25519PrivateKey) -> str:
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return base64.b64encode(public_key).decode()


def _sign(payload: dict, private_key: Ed25519PrivateKey) -> None:
    signature = private_key.sign(canonical_signed_payload(payload))
    payload["signature"]["value_base64"] = base64.b64encode(signature).decode()


def _git(repo: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _build_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    repo = tmp_path / "release-checkout"
    repo.mkdir()
    compose_path = repo / "docker-compose.prod.yml"
    policy_path = repo / "production-security-policy-v1.json"
    compose_path.write_text("services: {}\n", encoding="utf-8")
    policy = {"required_external_controls": CONTROL_IDS}
    _write_json(policy_path, policy)
    (repo / "tracked.txt").write_text("release source\n", encoding="utf-8")
    _git(repo, "init", "--quiet")
    _git(repo, "config", "user.email", "synthetic@example.invalid")
    _git(repo, "config", "user.name", "Synthetic Admission Test")
    _git(repo, "add", ".")
    _git(repo, "commit", "--quiet", "-m", "synthetic release")

    evidence_root = tmp_path / "protected-evidence"
    evidence_root.mkdir()
    controls = []
    for index, control_id in enumerate(CONTROL_IDS):
        path = evidence_root / "external" / f"control-{index}.json"
        content = f'{{"synthetic_control":"{control_id}"}}\n'.encode()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        controls.append(
            {
                "control_id": control_id,
                "status": "verified",
                "artifact_refs": [
                    {
                        "path": f"external/control-{index}.json",
                        "sha256": _digest(content),
                    }
                ],
            }
        )

    evidence_refs = {}
    for category in ("security", "regression", "rehearsal"):
        path = evidence_root / category / "result.json"
        content = f'{{"synthetic_{category}":"PASS"}}\n'.encode()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        evidence_refs[category] = {
            "path": f"{category}/result.json",
            "sha256": _digest(content),
            "observed_at": (NOW - timedelta(hours=2)).isoformat(),
            "expires_at": (NOW + timedelta(hours=22)).isoformat(),
        }

    external_private_key = Ed25519PrivateKey.generate()
    admission_private_key = Ed25519PrivateKey.generate()
    keyring = {
        "schema_version": "1.0.0",
        "keys": [
            {
                "key_id": "external-key-1",
                "operator_id": "external-operator",
                "roles": ["release-security"],
                "environments": ["production-primary"],
                "public_key_base64": _public_key_base64(external_private_key),
                "revoked": False,
            },
            {
                "key_id": "admission-key-1",
                "operator_id": "admission-operator",
                "roles": ["production-admission-approver"],
                "environments": ["production-primary"],
                "public_key_base64": _public_key_base64(admission_private_key),
                "revoked": False,
            },
        ],
        "revoked_evidence_ids": [],
    }
    keyring_path = tmp_path / "protected-keyring" / "keyring.json"

    release_binding = {
        "git_commit": _git(repo, "rev-parse", "HEAD"),
        "git_tree": _git(repo, "rev-parse", "HEAD^{tree}"),
        "compose_sha256": _digest(compose_path.read_bytes()),
        "policy_sha256": _digest(policy_path.read_bytes()),
        "trusted_keyring_sha256": "sha256:" + "0" * 64,
        "model_artifact_digest": "sha256:" + "5" * 64,
        "image_digests": {
            "api": "sha256:" + "6" * 64,
            "dashboard": "sha256:" + "7" * 64,
            "web": "sha256:" + "8" * 64,
        },
    }
    external_evidence = {
        "schema_version": "1.0.0",
        "evidence_id": EXTERNAL_EVIDENCE_ID,
        "environment": {
            "name": "production-primary",
            "topology": "single-host-docker-compose",
        },
        "actor": {"operator_id": "external-operator", "role": "release-security"},
        "observed_at": (NOW - timedelta(hours=2)).isoformat(),
        "expires_at": (NOW + timedelta(hours=22)).isoformat(),
        "release_binding": deepcopy(release_binding),
        "controls": controls,
        "signature": {
            "algorithm": "Ed25519",
            "key_id": "external-key-1",
            "value_base64": "pending",
        },
    }
    package = {
        "schema_version": "1.0.0",
        "admission_id": ADMISSION_ID,
        "release": {
            "release_id": "runtime-asset-v1-test",
            "created_at": (NOW - timedelta(hours=3)).isoformat(),
        },
        "environment": {
            "name": "production-primary",
            "identity": "synthetic-environment-for-tests-only",
            "topology": "single-host-docker-compose",
        },
        "release_binding": deepcopy(release_binding),
        "evidence": {
            "external_controls": {
                "evidence_id": EXTERNAL_EVIDENCE_ID,
                "path": "external/bundle.json",
                "sha256": "sha256:" + "0" * 64,
            },
            "security_scan": [evidence_refs["security"]],
            "regression_test": [evidence_refs["regression"]],
            "rehearsal": [evidence_refs["rehearsal"]],
        },
        "approval": {
            "operator_id": "admission-operator",
            "role": "production-admission-approver",
            "approved_at": (NOW - timedelta(minutes=30)).isoformat(),
            "expires_at": (NOW + timedelta(hours=23)).isoformat(),
            "signature_reference": "#/signature",
        },
        "signature": {
            "algorithm": "Ed25519",
            "key_id": "admission-key-1",
            "value_base64": "pending",
        },
    }
    fixture = {
        "repo": repo,
        "compose_path": compose_path,
        "policy": policy,
        "policy_path": policy_path,
        "evidence_root": evidence_root,
        "keyring": keyring,
        "keyring_path": keyring_path,
        "external_private_key": external_private_key,
        "admission_private_key": admission_private_key,
        "external_evidence": external_evidence,
        "external_bundle_path": evidence_root / "external" / "bundle.json",
        "package": package,
        "package_path": evidence_root / "production-admission-package.json",
        "monkeypatch": monkeypatch,
    }
    _refresh_fixture(fixture)
    return fixture


def _refresh_fixture(fixture: dict) -> None:
    _write_json(fixture["keyring_path"], fixture["keyring"])
    trusted_keyring_digest = _digest(fixture["keyring_path"].read_bytes())
    fixture["monkeypatch"].setenv(
        TRUSTED_KEYRING_DIGEST_ENV, trusted_keyring_digest
    )
    fixture["external_evidence"]["release_binding"][
        "trusted_keyring_sha256"
    ] = trusted_keyring_digest
    fixture["package"]["release_binding"][
        "trusted_keyring_sha256"
    ] = trusted_keyring_digest

    _sign(fixture["external_evidence"], fixture["external_private_key"])
    _write_json(fixture["external_bundle_path"], fixture["external_evidence"])
    fixture["package"]["evidence"]["external_controls"]["sha256"] = _digest(
        fixture["external_bundle_path"].read_bytes()
    )
    _sign(fixture["package"], fixture["admission_private_key"])
    _write_json(fixture["package_path"], fixture["package"])


def _resign_package(fixture: dict) -> None:
    _sign(fixture["package"], fixture["admission_private_key"])
    _write_json(fixture["package_path"], fixture["package"])


def _verify(fixture: dict) -> dict:
    return verify_admission_package(
        package=fixture["package"],
        keyring_path=fixture["keyring_path"],
        repo_root=fixture["repo"],
        compose_path=fixture["compose_path"],
        policy_path=fixture["policy_path"],
        evidence_root=fixture["evidence_root"],
        now=NOW,
    )


def _assert_reason(reason: str, callback) -> None:
    with pytest.raises(AdmissionVerificationError) as captured:
        callback()
    assert captured.value.reason_code == reason


def test_production_admission_schema_is_valid_and_strict(root):
    schema = json.loads(
        (root / "schema/production-admission-package.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator.check_schema(schema)
    assert schema["additionalProperties"] is False
    assert set(schema["$defs"]["image_digests"]["required"]) == {
        "api",
        "dashboard",
        "web",
    }


def test_admission_release_binding_matches_external_control_contract(root):
    admission_schema = json.loads(
        (root / "schema/production-admission-package.schema.json").read_text(
            encoding="utf-8"
        )
    )
    external_schema = json.loads(
        (root / "schema/production-external-control-evidence.schema.json").read_text(
            encoding="utf-8"
        )
    )
    admission_binding = admission_schema["$defs"]["release_binding"]
    external_binding = external_schema["properties"]["release_binding"]

    assert admission_binding["required"] == external_binding["required"]
    assert set(admission_binding["properties"]) == set(external_binding["properties"])
    assert set(admission_schema["$defs"]["image_digests"]["required"]) == set(
        external_binding["properties"]["image_digests"]["required"]
    )


def test_public_docs_expose_production_admission_boundary(root):
    readme = (root / "README.md").read_text(encoding="utf-8")
    docs_index = (root / "docs/README.md").read_text(encoding="utf-8")

    assert "Production Admission Status" in readme
    assert "Repository Gate: `GO`" in readme
    assert "Production Admission: `WAITING_FOR_OPERATOR_EVIDENCE`" in readme
    for path in (
        "contracts/runtime-production-admission-v1.md",
        "production-operator-handoff.md",
        "production-admission-recovery.md",
    ):
        assert path in docs_index


def test_valid_signed_admission_package_passes(tmp_path, monkeypatch):
    fixture = _build_fixture(tmp_path, monkeypatch)

    report = _verify(fixture)

    assert report["status"] == "PASS"
    assert report["release_gate"] == "PRODUCTION_ADMISSION_VERIFIED"
    assert {check["name"] for check in report["checks"]} >= {
        "commit_binding",
        "image_digest_binding",
        "model_artifact_binding",
        "operator_signature",
        "revocation_state",
        "external_control_evidence",
    }
    schema = json.loads(
        Path("schema/production-admission-package.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(
        fixture["package"]
    )


def test_wrong_commit_sha_fails_closed(tmp_path, monkeypatch):
    fixture = _build_fixture(tmp_path, monkeypatch)
    fixture["package"]["release_binding"]["git_commit"] = "9" * 40
    _resign_package(fixture)

    _assert_reason("commit_binding_mismatch", lambda: _verify(fixture))


def test_wrong_image_digest_fails_closed(tmp_path, monkeypatch):
    fixture = _build_fixture(tmp_path, monkeypatch)
    fixture["package"]["release_binding"]["image_digests"]["api"] = (
        "sha256:" + "9" * 64
    )
    _resign_package(fixture)

    _assert_reason("image_digest_binding_mismatch", lambda: _verify(fixture))


def test_missing_operator_signature_fails_closed(tmp_path, monkeypatch):
    fixture = _build_fixture(tmp_path, monkeypatch)
    fixture["package"].pop("signature")

    _assert_reason("operator_signature_missing", lambda: _verify(fixture))


def test_expired_evidence_fails_closed(tmp_path, monkeypatch):
    fixture = _build_fixture(tmp_path, monkeypatch)
    fixture["package"]["evidence"]["security_scan"][0]["expires_at"] = (
        NOW.isoformat()
    )
    _resign_package(fixture)

    _assert_reason("evidence_expired", lambda: _verify(fixture))


def test_revoked_approval_fails_closed(tmp_path, monkeypatch):
    fixture = _build_fixture(tmp_path, monkeypatch)
    fixture["keyring"]["revoked_evidence_ids"].append(ADMISSION_ID)
    _refresh_fixture(fixture)

    _assert_reason("approval_revoked", lambda: _verify(fixture))


def test_external_control_signer_cannot_approve_package(tmp_path, monkeypatch):
    fixture = _build_fixture(tmp_path, monkeypatch)
    fixture["package"]["approval"]["operator_id"] = "external-operator"
    fixture["package"]["approval"]["role"] = "release-security"
    fixture["package"]["signature"]["key_id"] = "external-key-1"
    _sign(fixture["package"], fixture["external_private_key"])

    _assert_reason(
        "admission_approver_role_required", lambda: _verify(fixture)
    )


def test_keyring_contents_are_loaded_from_anchored_path(tmp_path, monkeypatch):
    fixture = _build_fixture(tmp_path, monkeypatch)
    fixture["keyring"]["keys"][1]["public_key_base64"] = _public_key_base64(
        Ed25519PrivateKey.generate()
    )

    report = _verify(fixture)

    assert report["status"] == "PASS"


def test_policy_contents_are_loaded_from_bound_path(tmp_path, monkeypatch):
    fixture = _build_fixture(tmp_path, monkeypatch)
    fixture["policy"]["required_external_controls"] = CONTROL_IDS[:-1]

    report = _verify(fixture)

    assert report["status"] == "PASS"


def test_same_evidence_digest_cannot_fill_two_categories(tmp_path, monkeypatch):
    fixture = _build_fixture(tmp_path, monkeypatch)
    duplicated = deepcopy(fixture["package"]["evidence"]["security_scan"][0])
    fixture["package"]["evidence"]["regression_test"] = [duplicated]
    _resign_package(fixture)

    _assert_reason("evidence_reference_duplicated", lambda: _verify(fixture))


def test_same_evidence_path_cannot_fill_two_categories(tmp_path, monkeypatch):
    fixture = _build_fixture(tmp_path, monkeypatch)
    duplicated = deepcopy(fixture["package"]["evidence"]["security_scan"][0])
    duplicated["sha256"] = "sha256:" + "1" * 64
    fixture["package"]["evidence"]["regression_test"] = [duplicated]
    _resign_package(fixture)

    _assert_reason("evidence_reference_duplicated", lambda: _verify(fixture))


def test_model_digest_mismatch_fails_closed(tmp_path, monkeypatch):
    fixture = _build_fixture(tmp_path, monkeypatch)
    fixture["package"]["release_binding"]["model_artifact_digest"] = (
        "sha256:" + "9" * 64
    )
    _resign_package(fixture)

    _assert_reason("model_artifact_binding_mismatch", lambda: _verify(fixture))


def test_cli_failure_is_machine_readable(tmp_path, monkeypatch, capsys):
    fixture = _build_fixture(tmp_path, monkeypatch)
    fixture["package"].pop("signature")
    _write_json(fixture["package_path"], fixture["package"])

    exit_code = main(
        [
            str(fixture["package_path"]),
            "--keyring",
            str(fixture["keyring_path"]),
            "--evidence-root",
            str(fixture["evidence_root"]),
            "--repo-root",
            str(fixture["repo"]),
            "--policy",
            str(fixture["policy_path"]),
            "--compose-file",
            str(fixture["compose_path"]),
        ]
    )

    report = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert report["status"] == "FAIL"
    assert report["release_gate"] == "BLOCKED"
    assert report["reason_codes"] == ["operator_signature_missing"]
