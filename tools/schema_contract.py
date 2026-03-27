#!/usr/bin/env python3
"""
Shared helpers for enforcing the canonical skill schema contract.
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

from jsonschema import Draft7Validator, FormatChecker

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SCHEMA_PATH = REPO_ROOT / "schema" / "skill-decomposition.schema.json"
SKILL_ID_PATTERN = re.compile(r"^(claude|mcp)__[a-z_]+__[a-z_]+$")
VALID_FAIL_ACTIONS = {"halt", "branch", "default_value", "error_throw", "retry", "escalate"}


def load_schema(schema_path: str | Path = DEFAULT_SCHEMA_PATH) -> dict[str, Any]:
    """Load the canonical JSON schema."""
    schema_file = Path(schema_path)
    return json.loads(schema_file.read_text(encoding="utf-8"))


def build_validator(schema_path: str | Path = DEFAULT_SCHEMA_PATH) -> Draft7Validator:
    """Build a draft-07 validator with format checking."""
    return Draft7Validator(load_schema(schema_path), format_checker=FormatChecker())


def slugify_token(text: str) -> str:
    """Convert arbitrary text into a schema-safe token."""
    cleaned = text.lower().replace("-", "_")
    cleaned = re.sub(r"[^a-z_]+", "_", cleaned)
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned or "unknown"


def derive_short_name(text: str | None, fallback: str) -> str:
    """Derive a compact human-readable name from longer text."""
    if not text:
        return fallback

    cleaned = re.sub(r"\s+", " ", text).strip(" .:-")
    if not cleaned:
        return fallback

    words = cleaned.split()
    candidate = " ".join(words[:6])
    if len(words) > 6:
        candidate += "..."
    return candidate[:80]


def infer_condition_type(*texts: str | None) -> str:
    """Heuristically map legacy rule wording onto the canonical enum."""
    joined = " ".join(t for t in texts if t).lower()

    if any(token in joined for token in ("permission", "authorize", "auth", "access", "role")):
        return "permission_check"
    if any(token in joined for token in ("exist", "found", "available", "present", "missing")):
        return "existence_check"
    if any(token in joined for token in ("type", "format", "schema", "json", "yaml")):
        return "type_check"
    if any(token in joined for token in ("range", "minimum", "maximum", "bounded")):
        return "range_check"
    if any(token in joined for token in ("threshold", "limit", "quota", "rate", "too many")):
        return "threshold_check"
    if any(token in joined for token in ("consistent", "consistency", "match", "align", "same")):
        return "consistency_check"
    if any(token in joined for token in ("state", "ready", "running", "stopped", "complete")):
        return "state_check"
    return "validation"


def infer_returns(rule: dict[str, Any]) -> str:
    """Map legacy output semantics onto the canonical returns enum."""
    value = str(rule.get("returns") or rule.get("output") or "").strip().lower()

    if value in {"boolean", "classification", "enum_value", "score"}:
        return value
    if value in {"proceed_or_halt", "pass_fail", "true_false", "bool"}:
        return "boolean"
    if "score" in value:
        return "score"
    if "class" in value:
        return "classification"
    if "enum" in value:
        return "enum_value"
    return "boolean"


def normalize_skill_id(meta: dict[str, Any]) -> str:
    """Backfill a schema-safe skill_id if the current one is invalid."""
    current = str(meta.get("skill_id") or "").strip()
    if SKILL_ID_PATTERN.match(current):
        return current

    provider = "mcp" if meta.get("skill_layer", "").startswith("mcp") or current.startswith("mcp__") else "claude"
    scope = "tool" if meta.get("skill_layer") == "mcp_tool" else "server_internal" if meta.get("skill_layer") == "mcp_server_internal" else "skill"
    name = slugify_token(str(meta.get("name") or current or "unknown"))
    return f"{provider}__{scope}__{name}"


def normalize_action(action: dict[str, Any]) -> dict[str, Any]:
    """Normalize action fields while preserving legacy metadata."""
    normalized = copy.deepcopy(action)

    if not normalized.get("name"):
        normalized["name"] = derive_short_name(
            normalized.get("description") or normalized.get("content"),
            fallback=f"Action {normalized.get('id', '').upper() or 'Unnamed'}",
        )
    if not normalized.get("description"):
        normalized["description"] = normalized.get("content") or normalized.get("name", "")
    if not normalized.get("action_type") and normalized.get("type"):
        normalized["action_type"] = normalized["type"]
    normalized.setdefault("deterministic", True)
    normalized.setdefault("side_effects", [])
    normalized.pop("type", None)
    normalized.pop("content", None)
    return normalized


def normalize_rule(rule: dict[str, Any]) -> dict[str, Any]:
    """Backfill required canonical rule fields from legacy shapes."""
    normalized = copy.deepcopy(rule)

    legacy_description = normalized.get("description")
    legacy_condition = normalized.get("condition")
    if not normalized.get("name"):
        normalized["name"] = derive_short_name(
            legacy_description or legacy_condition,
            fallback=f"Rule {normalized.get('id', '').upper() or 'Unnamed'}",
        )
    if not normalized.get("condition_expression"):
        normalized["condition_expression"] = legacy_condition or legacy_description or normalized["name"]
    if not normalized.get("condition_type"):
        normalized["condition_type"] = infer_condition_type(
            legacy_description,
            legacy_condition,
            normalized.get("name"),
        )
    if not normalized.get("returns"):
        normalized["returns"] = infer_returns(normalized)
    fail_action = normalized.get("fail_action")
    if fail_action and fail_action not in VALID_FAIL_ACTIONS:
        if fail_action in {"flag", "warn"}:
            normalized["fail_action"] = "escalate"
        elif fail_action in {"abort", "stop", "cancel"}:
            normalized["fail_action"] = "halt"
        elif fail_action in {"skip", "continue", "transform"}:
            normalized["fail_action"] = "branch"
        else:
            normalized["fail_action"] = "escalate"
    normalized.pop("mode", None)
    normalized.pop("condition", None)
    normalized.pop("output", None)
    return normalized


def normalize_directive(directive: dict[str, Any]) -> dict[str, Any]:
    """Backfill required canonical directive fields from legacy shapes."""
    normalized = copy.deepcopy(directive)

    if not normalized.get("description"):
        normalized["description"] = normalized.get("content") or normalized.get("name", "")
    if not normalized.get("directive_type") and normalized.get("type"):
        normalized["directive_type"] = normalized["type"]
    if not normalized.get("name"):
        normalized["name"] = derive_short_name(
            normalized.get("description"),
            fallback=f"Directive {normalized.get('id', '').upper() or 'Unnamed'}",
        )
    normalized.pop("type", None)
    normalized.pop("content", None)
    return normalized


def normalize_execution_path(path: dict[str, Any], index: int) -> dict[str, Any]:
    """Backfill required execution path fields."""
    normalized = copy.deepcopy(path)
    normalized.setdefault("path_id", index)
    if not normalized.get("condition"):
        normalized["condition"] = normalized.get("path_name") or normalized.get("description") or "default"
    if not normalized.get("expected_outcome") and normalized.get("description"):
        normalized["expected_outcome"] = normalized["description"]
    return normalized


def normalize_skill_document(skill: dict[str, Any], schema_version: str = "2.4.0") -> dict[str, Any]:
    """Normalize a skill document toward the canonical schema contract."""
    normalized = copy.deepcopy(skill)

    meta = normalized.setdefault("meta", {})
    meta["skill_id"] = normalize_skill_id(meta)
    if schema_version:
        meta["schema_version"] = schema_version

    decomposition = normalized.setdefault("decomposition", {})
    decomposition["actions"] = [normalize_action(action) for action in decomposition.get("actions", [])]
    decomposition["rules"] = [normalize_rule(rule) for rule in decomposition.get("rules", [])]
    decomposition["directives"] = [
        normalize_directive(directive) for directive in decomposition.get("directives", [])
    ]
    if "execution_paths" in normalized:
        normalized["execution_paths"] = [
            normalize_execution_path(path, index)
            for index, path in enumerate(normalized.get("execution_paths", []), start=1)
        ]

    return normalized


def iter_validation_errors(
    skill: dict[str, Any],
    schema_path: str | Path = DEFAULT_SCHEMA_PATH,
):
    """Yield sorted validation errors for a skill document."""
    validator = build_validator(schema_path)
    return sorted(validator.iter_errors(skill), key=lambda error: list(error.absolute_path))
