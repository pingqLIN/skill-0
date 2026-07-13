from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import FormatChecker
from jsonschema.validators import validator_for


class RuntimeContractValidationError(ValueError):
    pass


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_schema(contract: dict[str, Any], schema: dict[str, Any]) -> None:
    validator_class = validator_for(schema)
    validator_class.check_schema(schema)
    validator = validator_class(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(contract), key=lambda error: list(error.absolute_path))
    if errors:
        messages = [f"/{'/'.join(map(str, error.absolute_path))}: {error.message}" for error in errors]
        raise RuntimeContractValidationError("\n".join(messages))


def validate_cross_references(skill_document: dict[str, Any], contract: dict[str, Any]) -> None:
    decomposition = skill_document.get("decomposition", {})
    actions = {item.get("id") for item in decomposition.get("actions", [])}
    rules = {item.get("id") for item in decomposition.get("rules", [])}
    directives = {item.get("id") for item in decomposition.get("directives", [])}
    problems: list[str] = []

    bindings = contract.get("action_bindings", [])
    binding_ids = [binding.get("action_id") for binding in bindings]
    duplicate_ids = sorted({item for item in binding_ids if item and binding_ids.count(item) > 1})
    if duplicate_ids:
        problems.append(f"Duplicate Action bindings: {duplicate_ids}")
    binding_by_id = {binding.get("action_id"): binding for binding in bindings}

    referenced_compensations: set[str] = set()
    for binding in bindings:
        action_id = binding.get("action_id")
        role = binding.get("role")
        if action_id not in actions:
            problems.append(f"Unknown Action reference: {action_id}")
        if role not in {"primary", "compensation"}:
            problems.append(f"Action {action_id} has invalid or missing role: {role!r}")

        compensation = binding.get("compensation", {})
        comp_id = compensation.get("action_id")
        if comp_id:
            referenced_compensations.add(comp_id)
            if comp_id not in actions:
                problems.append(f"Unknown compensation Action reference: {comp_id}")
            target = binding_by_id.get(comp_id)
            if target is None:
                problems.append(f"Compensation Action has no runtime binding: {comp_id}")
            elif target.get("role") != "compensation":
                problems.append(f"Compensation target must have role=compensation: {comp_id}")
            if comp_id == action_id:
                problems.append(f"Action cannot compensate itself: {action_id}")

        validation = binding.get("validation", {})
        for rule_id in validation.get("precondition_rule_ids", []):
            if rule_id not in rules:
                problems.append(f"Unknown precondition Rule reference: {rule_id}")
        for rule_id in validation.get("postcondition_rule_ids", []):
            if rule_id not in rules:
                problems.append(f"Unknown postcondition Rule reference: {rule_id}")

    for binding in bindings:
        if binding.get("role") == "compensation" and binding.get("action_id") not in referenced_compensations:
            problems.append(f"Orphan compensation Action binding: {binding.get('action_id')}")

    for binding in contract.get("governance", {}).get("rule_policy_bindings", []):
        if binding.get("rule_id") not in rules:
            problems.append(f"Unknown governance Rule reference: {binding.get('rule_id')}")

    manifest = contract.get("directive_manifest", {})
    for directive_id in [*manifest.get("include", []), *manifest.get("exclude", [])]:
        if directive_id not in directives:
            problems.append(f"Unknown Directive reference: {directive_id}")

    overlap = set(manifest.get("include", [])) & set(manifest.get("exclude", []))
    if overlap:
        problems.append(f"Directive IDs appear in both include and exclude: {sorted(overlap)}")

    if problems:
        raise RuntimeContractValidationError("\n".join(problems))
