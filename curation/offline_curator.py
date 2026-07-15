"""Deterministic, proposal-only boundary for the offline Skill-0 Curator."""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from tools.curation_contract import (
    find_sensitive_content,
    validate_contract_document,
    validate_proposal_base_revision,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST_PATH = REPO_ROOT / "curation" / "manifests" / "offline-curator-v1.json"
DRY_OUTPUT_ROOT = REPO_ROOT / "output" / "curation"
PACKAGE_VERSION = "1.0.0"
_PROMPT_PACKAGE_KEYS = {
    "package_version",
    "manifest",
    "curator",
    "prompt",
    "trajectory",
    "skill_context",
    "package_checksum",
}
_CURATOR_KEYS = {"curator_id", "mode", "model_id", "config_checksum"}


class CuratorBoundaryError(ValueError):
    """Raised when offline Curator input fails a fail-closed boundary check."""


@dataclass(frozen=True)
class CuratorResources:
    """Verified static resources that define one deterministic Curator configuration."""

    manifest: dict[str, Any]
    manifest_checksum: str
    prompt_text: str
    prompt_checksum: str


def canonical_json_bytes(value: Any) -> bytes:
    """Encode JSON deterministically for IDs and integrity checks."""
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    """Return a lower-case SHA-256 digest without a scheme prefix."""
    return hashlib.sha256(value).hexdigest()


def load_json_object(path: Path) -> dict[str, Any]:
    """Load a JSON object from disk without accepting non-object roots."""
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise CuratorBoundaryError(f"{path} must contain a JSON object")
    return value


def load_curator_resources(manifest_path: Path = DEFAULT_MANIFEST_PATH) -> CuratorResources:
    """Load and verify the manifest, prompt path, and pinned prompt checksum."""
    manifest = load_json_object(manifest_path)
    if manifest.get("manifest_version") != PACKAGE_VERSION:
        raise CuratorBoundaryError("unsupported offline Curator manifest version")
    if manifest.get("output_mode") != "dry_proposal_only":
        raise CuratorBoundaryError("offline Curator manifest must use dry_proposal_only")
    if manifest.get("allowed_operations") != ["insert", "update", "delete"]:
        raise CuratorBoundaryError("offline Curator manifest operations are not canonical")

    prompt_path = _resolve_repo_reference(manifest.get("prompt_template"), "prompt_template")
    prompt_text = (
        prompt_path.read_text(encoding="utf-8")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
    )
    prompt_checksum = sha256_bytes(prompt_text.encode("utf-8"))
    if prompt_checksum != manifest.get("prompt_template_sha256"):
        raise CuratorBoundaryError("offline Curator prompt checksum does not match the manifest")

    for key in ("context_schema", "decision_schema", "proposal_schema"):
        _resolve_repo_reference(manifest.get(key), key)

    return CuratorResources(
        manifest=manifest,
        manifest_checksum=sha256_bytes(canonical_json_bytes(manifest)),
        prompt_text=prompt_text,
        prompt_checksum=prompt_checksum,
    )


def validate_skill_context(context: dict[str, Any]) -> list[str]:
    """Validate a read-only skill snapshot and reject duplicate or sensitive entries."""
    issues = validate_contract_document(context, "curator_context")
    skills = context.get("skills")
    if isinstance(skills, list):
        identities = [
            (skill.get("skill_id"), skill.get("revision_id"))
            for skill in skills
            if isinstance(skill, dict)
        ]
        if len(identities) != len(set(identities)):
            issues.append("curator skill context contains duplicate skill revisions")
        skill_ids = [identity[0] for identity in identities]
        if len(skill_ids) != len(set(skill_ids)):
            issues.append("curator skill context must contain at most one revision per skill")

    issues.extend(
        f"sensitive content detected at {finding.path}: {finding.reason}"
        for finding in find_sensitive_content(context)
    )
    return issues


def validate_context_alignment(
    trajectory: dict[str, Any],
    context: dict[str, Any],
) -> list[str]:
    """Require the supplied context to match the trajectory retrieval result exactly."""
    retrieved = trajectory.get("retrieved_skills")
    skills = context.get("skills")
    if not isinstance(retrieved, list) or not isinstance(skills, list):
        return ["trajectory retrieval and curator skill context must be arrays"]

    expected = [
        (item.get("skill_id"), item.get("revision_id"))
        for item in retrieved
        if isinstance(item, dict)
    ]
    actual = [
        (item.get("skill_id"), item.get("revision_id"))
        for item in skills
        if isinstance(item, dict)
    ]
    if expected != actual:
        return ["curator skill context must exactly match trajectory retrieval order and revisions"]
    return []


def build_prompt_package(
    trajectory: dict[str, Any],
    skill_context: dict[str, Any],
    *,
    model_id: str,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
) -> dict[str, Any]:
    """Build a deterministic offline prompt package after validating all input."""
    if not model_id.strip():
        raise CuratorBoundaryError("model_id must not be empty")
    if find_sensitive_content(model_id):
        raise CuratorBoundaryError("model_id contains sensitive content")

    _raise_for_issues("trajectory", validate_contract_document(trajectory, "trajectory"))
    _raise_for_issues("skill context", validate_skill_context(skill_context))
    _raise_for_issues("retrieval alignment", validate_context_alignment(trajectory, skill_context))
    resources = load_curator_resources(manifest_path)

    package = {
        "package_version": PACKAGE_VERSION,
        "manifest": {
            "manifest_version": resources.manifest["manifest_version"],
            "manifest_checksum": resources.manifest_checksum,
            "prompt_template": resources.manifest["prompt_template"],
            "prompt_template_checksum": resources.prompt_checksum,
            "decision_schema": resources.manifest["decision_schema"],
            "proposal_schema": resources.manifest["proposal_schema"],
            "output_mode": resources.manifest["output_mode"],
        },
        "curator": {
            "curator_id": resources.manifest["curator_id"],
            "mode": resources.manifest["mode"],
            "model_id": model_id,
            "config_checksum": resources.manifest_checksum,
        },
        "prompt": resources.prompt_text,
        "trajectory": copy.deepcopy(trajectory),
        "skill_context": copy.deepcopy(skill_context),
    }
    package["package_checksum"] = sha256_bytes(canonical_json_bytes(package))
    return package


def validate_prompt_package(
    package: dict[str, Any],
    *,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
) -> list[str]:
    """Validate package integrity and its binding to current static resources."""
    issues: list[str] = []
    if set(package) != _PROMPT_PACKAGE_KEYS:
        issues.append("prompt package has unexpected or missing top-level fields")
    if package.get("package_version") != PACKAGE_VERSION:
        issues.append("prompt package version is not supported")

    checksum = package.get("package_checksum")
    unsigned_package = copy.deepcopy(package)
    unsigned_package.pop("package_checksum", None)
    if checksum != sha256_bytes(canonical_json_bytes(unsigned_package)):
        issues.append("prompt package checksum is invalid")

    resources = load_curator_resources(manifest_path)
    manifest = package.get("manifest")
    if not isinstance(manifest, dict):
        issues.append("prompt package manifest is missing")
    else:
        expected_manifest = {
            "manifest_version": resources.manifest["manifest_version"],
            "manifest_checksum": resources.manifest_checksum,
            "prompt_template": resources.manifest["prompt_template"],
            "prompt_template_checksum": resources.prompt_checksum,
            "decision_schema": resources.manifest["decision_schema"],
            "proposal_schema": resources.manifest["proposal_schema"],
            "output_mode": resources.manifest["output_mode"],
        }
        if manifest != expected_manifest:
            issues.append("prompt package manifest does not match verified Curator resources")

    if package.get("prompt") != resources.prompt_text:
        issues.append("prompt package template content does not match verified resources")

    curator = package.get("curator")
    if not isinstance(curator, dict):
        issues.append("prompt package curator configuration is missing")
    else:
        if set(curator) != _CURATOR_KEYS:
            issues.append("prompt package curator configuration has unexpected or missing fields")
        if curator.get("curator_id") != resources.manifest["curator_id"]:
            issues.append("prompt package curator_id does not match the manifest")
        if curator.get("mode") != resources.manifest["mode"]:
            issues.append("prompt package curator mode does not match the manifest")
        if curator.get("config_checksum") != resources.manifest_checksum:
            issues.append("prompt package config checksum does not match the manifest")
        if not isinstance(curator.get("model_id"), str) or not curator["model_id"].strip():
            issues.append("prompt package model_id is missing")

    trajectory = package.get("trajectory")
    context = package.get("skill_context")
    if not isinstance(trajectory, dict):
        issues.append("prompt package trajectory is missing")
    else:
        issues.extend(validate_contract_document(trajectory, "trajectory"))
    if not isinstance(context, dict):
        issues.append("prompt package skill context is missing")
    else:
        issues.extend(validate_skill_context(context))
    if isinstance(trajectory, dict) and isinstance(context, dict):
        issues.extend(validate_context_alignment(trajectory, context))
    issues.extend(
        f"sensitive content detected at {finding.path}: {finding.reason}"
        for finding in find_sensitive_content(package)
    )
    return issues


def build_draft_proposal(
    prompt_package: dict[str, Any],
    decision: dict[str, Any],
    current_skill_context: dict[str, Any],
    *,
    candidate_artifact: bytes | None = None,
    candidate_name: str = "SKILL.md",
    created_at: str | None = None,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
) -> dict[str, Any]:
    """Convert one bound offline decision into a validated dry draft proposal."""
    _raise_for_issues("prompt package", validate_prompt_package(prompt_package, manifest_path=manifest_path))
    _raise_for_issues("curator decision", validate_contract_document(decision, "curator_decision"))
    _raise_for_issues("current skill context", validate_skill_context(current_skill_context))
    _raise_for_sensitive("curator decision", decision)

    if decision.get("prompt_package_checksum") != prompt_package.get("package_checksum"):
        raise CuratorBoundaryError("curator decision is not bound to this prompt package")

    operation = decision["operation"]
    package_context = prompt_package["skill_context"]
    package_captured_at = _parse_datetime(package_context["captured_at"])
    current_captured_at = _parse_datetime(current_skill_context["captured_at"])
    if current_captured_at < package_captured_at:
        raise CuratorBoundaryError("current skill context is older than the prompt skill context")

    package_skills = _skills_by_id(package_context)
    current_skills = _skills_by_id(current_skill_context)
    target_skill_id = decision.get("target_skill_id")
    proposed_skill_id = decision.get("proposed_skill_id")

    target: dict[str, Any] | None = None
    if operation in {"update", "delete"}:
        package_target = package_skills.get(target_skill_id)
        current_target = current_skills.get(target_skill_id)
        if package_target is None:
            raise CuratorBoundaryError("update/delete target is not present in the prompt skill context")
        if current_target is None:
            raise CuratorBoundaryError("update/delete target is not present in the current skill context")
        if (
            package_target["revision_id"] != current_target["revision_id"]
            or package_target["revision_checksum"] != current_target["revision_checksum"]
        ):
            raise CuratorBoundaryError("target revision changed after prompt preparation")
        target = {
            "skill_id": package_target["skill_id"],
            "base_revision_id": package_target["revision_id"],
            "base_revision_checksum": package_target["revision_checksum"],
        }

    if operation == "insert" and proposed_skill_id in current_skills:
        raise CuratorBoundaryError("insert proposal skill_id already exists in the current context")
    if operation == "update" and proposed_skill_id != target_skill_id:
        raise CuratorBoundaryError("update proposal must preserve the target skill_id")

    candidate: dict[str, Any] | None = None
    candidate_checksum: str | None = None
    if operation in {"insert", "update"}:
        if candidate_artifact is None:
            raise CuratorBoundaryError("insert/update decisions require a candidate artifact")
        candidate_text = _decode_candidate(candidate_artifact)
        _raise_for_sensitive("candidate artifact", candidate_text)
        candidate_checksum = sha256_bytes(candidate_artifact)
        if target and candidate_checksum == target["base_revision_checksum"].removeprefix("sha256:"):
            raise CuratorBoundaryError("update candidate artifact is identical to the base revision")
    elif candidate_artifact is not None:
        raise CuratorBoundaryError("delete decisions must not provide a candidate artifact")

    proposal_created_at = created_at or current_skill_context["captured_at"]
    proposal_created_time = _parse_datetime(proposal_created_at)
    earliest_created_time = max(
        _parse_datetime(prompt_package["trajectory"]["run"]["completed_at"]),
        package_captured_at,
        current_captured_at,
    )
    if proposal_created_time < earliest_created_time:
        raise CuratorBoundaryError("proposal created_at precedes its trajectory or skill context")
    proposal_seed = {
        "package_checksum": prompt_package["package_checksum"],
        "decision": decision,
        "candidate_checksum": candidate_checksum,
        "created_at": proposal_created_at,
    }
    proposal_id = f"proposal_{sha256_bytes(canonical_json_bytes(proposal_seed))[:24]}"
    if candidate_checksum is not None:
        candidate = {
            "proposed_skill_id": proposed_skill_id,
            "artifact_ref": f"proposal://{proposal_id}/{Path(candidate_name).name}",
            "artifact_checksum": candidate_checksum,
        }

    trajectory = prompt_package["trajectory"]
    proposal: dict[str, Any] = {
        "contract_version": PACKAGE_VERSION,
        "proposal_id": proposal_id,
        "operation": operation,
        "supporting_trajectories": [
            {
                "trajectory_id": trajectory["trajectory_id"],
                "task_id": trajectory["task"]["task_id"],
                "observed_at": trajectory["run"]["completed_at"],
            }
        ],
        "retrieval_context": [
            {
                key: item[key]
                for key in ("skill_id", "revision_id", "rank", "retriever", "score")
                if key in item
            }
            for item in trajectory["retrieved_skills"]
        ],
        "curator": copy.deepcopy(prompt_package["curator"]),
        "rationale_summary": decision["rationale_summary"],
        "confidence": decision["confidence"],
        "validations": {
            "schema": {"status": "pass", "summary": "P2 proposal contract validation passed."},
            "ard": {"status": "not_run", "summary": "Candidate ARD analysis is deferred."},
            "duplicate": {"status": "not_run", "summary": "Repository duplicate analysis is deferred."},
            "conflict": {"status": "not_run", "summary": "Repository conflict analysis is deferred."},
            "provenance": {"status": "pass", "summary": "Prompt and trajectory bindings passed."},
        },
        "governance": {"state": "draft"},
        "created_at": proposal_created_at,
    }
    if target is not None:
        proposal["target"] = target
    if candidate is not None:
        proposal["candidate"] = candidate

    _raise_for_issues("draft proposal", validate_contract_document(proposal, "proposal"))
    if target is not None:
        _raise_for_issues(
            "current revision",
            validate_proposal_base_revision(
                proposal,
                current_revision_id=target["base_revision_id"],
                current_revision_checksum=target["base_revision_checksum"],
            ),
        )
    _raise_for_sensitive("draft proposal", proposal)
    return proposal


def write_dry_json_artifact(document: dict[str, Any], output_path: Path) -> Path:
    """Write a new JSON artifact without allowing canonical repository targets."""
    resolved = output_path.resolve()
    if _is_relative_to(resolved, REPO_ROOT.resolve()) and not _is_relative_to(
        resolved,
        DRY_OUTPUT_ROOT.resolve(),
    ):
        raise CuratorBoundaryError("repo-local Curator output is allowed only under output/curation")
    resolved.parent.mkdir(parents=True, exist_ok=True)
    with resolved.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(document, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return resolved


def _resolve_repo_reference(value: Any, field_name: str) -> Path:
    if not isinstance(value, str) or not value:
        raise CuratorBoundaryError(f"offline Curator manifest {field_name} is missing")
    path = (REPO_ROOT / value).resolve()
    if not _is_relative_to(path, REPO_ROOT.resolve()):
        raise CuratorBoundaryError(f"offline Curator manifest {field_name} escapes the repository")
    if not path.is_file():
        raise CuratorBoundaryError(f"offline Curator manifest {field_name} does not exist")
    return path


def _skills_by_id(context: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {skill["skill_id"]: skill for skill in context["skills"]}


def _decode_candidate(candidate_artifact: bytes) -> str:
    try:
        return candidate_artifact.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CuratorBoundaryError("candidate artifact must be UTF-8 text") from exc


def _parse_datetime(value: Any) -> datetime:
    if not isinstance(value, str):
        raise CuratorBoundaryError("expected an RFC 3339 date-time string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CuratorBoundaryError("expected an RFC 3339 date-time string") from exc
    if parsed.tzinfo is None:
        raise CuratorBoundaryError("date-time values must include a timezone")
    return parsed


def _raise_for_issues(label: str, issues: list[str]) -> None:
    if issues:
        raise CuratorBoundaryError(f"{label} rejected: " + "; ".join(issues))


def _raise_for_sensitive(label: str, value: Any) -> None:
    findings = find_sensitive_content(value)
    if findings:
        summary = ", ".join(f"{finding.path}: {finding.reason}" for finding in findings)
        raise CuratorBoundaryError(f"{label} contains sensitive content at {summary}")


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True
