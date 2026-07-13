from __future__ import annotations

import re
from typing import Any, Mapping

_TOKEN = re.compile(r"\{(run_id|external_resource_id|input\.[A-Za-z_][A-Za-z0-9_]*)\}")


def render_key_template(
    template: str,
    *,
    run_id: str,
    inputs: Mapping[str, Any],
    external_resource_id: str | None = None,
) -> str:
    """Render a deliberately small template language; no eval or attribute access."""

    def replace(match: re.Match[str]) -> str:
        token = match.group(1)
        if token == "run_id":
            return run_id
        if token == "external_resource_id":
            if not external_resource_id:
                raise ValueError("external_resource_id is required by template")
            return external_resource_id
        key = token.split(".", 1)[1]
        if key not in inputs:
            raise KeyError(f"Missing template input: {key}")
        return str(inputs[key])

    rendered = _TOKEN.sub(replace, template)
    if "{" in rendered or "}" in rendered:
        raise ValueError("Unsupported or unresolved template token")
    if not rendered:
        raise ValueError("Rendered key must not be empty")
    return rendered


def resolve_json_pointer(document: Any, pointer: str) -> Any:
    """Resolve an RFC 6901 JSON Pointer without evaluating code.

    Only ordinary object keys and array indexes are supported. The empty pointer
    selects the whole document. Invalid or missing paths fail closed.
    """

    if pointer == "":
        return document
    if not pointer.startswith("/"):
        raise ValueError(f"JSON Pointer must start with '/': {pointer!r}")

    current = document
    for raw_part in pointer.split("/")[1:]:
        part = raw_part.replace("~1", "/").replace("~0", "~")
        if isinstance(current, Mapping):
            if part not in current:
                raise KeyError(f"JSON Pointer segment not found: {part!r}")
            current = current[part]
        elif isinstance(current, list):
            if part == "-" or not part.isdigit():
                raise KeyError(f"Invalid JSON Pointer array index: {part!r}")
            index = int(part)
            if index >= len(current):
                raise IndexError(f"JSON Pointer array index out of range: {index}")
            current = current[index]
        else:
            raise KeyError(f"Cannot descend through non-container at segment {part!r}")
    return current


def resolve_parameter_mapping(mapping: Mapping[str, str], document: Any) -> dict[str, Any]:
    """Resolve a declared compensation mapping against the action result envelope."""

    return {name: resolve_json_pointer(document, pointer) for name, pointer in mapping.items()}
