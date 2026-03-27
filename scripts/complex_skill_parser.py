"""Prototype parser for multi-file Claude skills.

This module adds a manifest-oriented entrypoint without breaking the existing
single-file ``parse_skill_md(name, text)`` contract in ``auto_parse.py``.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from scripts.auto_parse import parse_frontmatter, parse_skill_md

PATHISH_EXTENSIONS = {
    ".json",
    ".md",
    ".mjs",
    ".py",
    ".sh",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}

COMMAND_PREFIXES = (
    "npm ",
    "npx ",
    "pip ",
    "python ",
    "python3 ",
    "bash ",
    "sh ",
    "node ",
    "git ",
    "docker ",
    "curl ",
    "wget ",
    "rg ",
)


def parse_skill_manifest(
    entry_path: str | Path,
    *,
    root_dir: str | Path | None = None,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Parse a multi-file skill package into a manifest-first structure."""
    del options  # Reserved for future parser tuning.

    entry = Path(entry_path).resolve()
    if not entry.exists():
        raise FileNotFoundError(f"Entry skill not found: {entry}")

    root = Path(root_dir).resolve() if root_dir else entry.parent
    content = entry.read_text(encoding="utf-8")
    metadata, body = parse_frontmatter(content)
    skill_name = metadata.get("name", entry.parent.name or entry.stem)

    result = parse_skill_md(skill_name, content)

    supporting_files, unresolved_refs = _extract_supporting_files(
        entry=entry,
        root=root,
        metadata=metadata,
        body=body,
    )
    command_references = _extract_command_references(
        body=body,
        source_path=_relative_to_root(entry, root),
    )
    delegation_nodes = _extract_delegation_nodes(
        metadata=metadata,
        body=body,
        source_path=_relative_to_root(entry, root),
    )
    analysis_findings = _build_analysis_findings(
        supporting_files=supporting_files,
        unresolved_refs=unresolved_refs,
        command_references=command_references,
        delegation_nodes=delegation_nodes,
    )

    result["manifest"] = {
        "entry_skill": {
            "path": _relative_to_root(entry, root),
            "name": skill_name,
            "resolved": True,
        },
        "analysis_level": "manifest",
        "supporting_files_count": len(supporting_files),
        "command_references_count": len(command_references),
        "delegation_nodes_count": len(delegation_nodes),
        "unresolved_references_count": len(unresolved_refs),
    }
    result["supporting_files"] = supporting_files
    result["command_references"] = command_references
    result["delegation_nodes"] = delegation_nodes
    result["analysis_findings"] = analysis_findings
    result["parser_meta"] = {
        "analysis_level": "manifest",
        "entry_path": _relative_to_root(entry, root),
        "manifest_present": True,
        "resolved_reference_count": sum(1 for item in supporting_files if item["resolved"]),
        "unresolved_reference_count": len(unresolved_refs),
        "experimental_fields": [
            "manifest",
            "supporting_files",
            "command_references",
            "delegation_nodes",
            "analysis_findings",
        ],
        "target_schema_version": "2.5.0-draft",
    }
    return result


def _extract_supporting_files(
    *,
    entry: Path,
    root: Path,
    metadata: dict[str, str],
    body: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    references = []
    references.extend(_extract_markdown_links(body))
    references.extend(_extract_inline_paths(body))
    references.extend(_extract_frontmatter_paths(metadata))

    deduped_refs = []
    seen_refs = set()
    for ref in references:
        if ref not in seen_refs:
            seen_refs.add(ref)
            deduped_refs.append(ref)

    supporting_files: list[dict[str, Any]] = []
    unresolved_refs: list[str] = []
    for index, ref in enumerate(deduped_refs, start=1):
        resolved = (entry.parent / ref).resolve()
        exists = resolved.exists()
        if not exists:
            unresolved_refs.append(ref)
        supporting_files.append(
            {
                "id": f"sf_{index:03d}",
                "path": ref,
                "kind": _classify_supporting_file_kind(ref),
                "resolved": exists,
                "referenced_by": [_relative_to_root(entry, root)],
                "summary": _summarize_path(resolved) if exists else "Referenced file could not be resolved",
            }
        )
    return supporting_files, unresolved_refs


def _extract_command_references(*, body: str, source_path: str) -> list[dict[str, Any]]:
    commands = []
    in_fence = False
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence or not stripped:
            continue
        if not any(stripped.startswith(prefix) for prefix in COMMAND_PREFIXES):
            continue
        authority = _classify_authority_profile(stripped)
        commands.append(
            {
                "id": f"cr_{len(commands) + 1:03d}",
                "source_path": source_path,
                "command": stripped,
                "shell_family": _detect_shell_family(stripped),
                "authority_profile": authority,
                "risk_grade": _classify_risk_grade(stripped, authority),
                "resolved_from": source_path,
            }
        )
    return commands


def _extract_delegation_nodes(
    *,
    metadata: dict[str, str],
    body: str,
    source_path: str,
) -> list[dict[str, Any]]:
    nodes = []
    context_value = metadata.get("context", "").strip().lower()
    if context_value == "fork":
        nodes.append(
            {
                "id": f"dg_{len(nodes) + 1:03d}",
                "kind": "fork_context",
                "agent": None,
                "source_path": source_path,
                "resolved": True,
                "notes": "Frontmatter requested forked context execution.",
            }
        )

    agent_value = metadata.get("agent", "").strip()
    if agent_value:
        nodes.append(
            {
                "id": f"dg_{len(nodes) + 1:03d}",
                "kind": "named_agent",
                "agent": agent_value,
                "source_path": source_path,
                "resolved": True,
                "notes": "Frontmatter explicitly names an agent.",
            }
        )

    if re.search(r"\b(subagent|delegate|delegation)\b", body, re.IGNORECASE):
        nodes.append(
            {
                "id": f"dg_{len(nodes) + 1:03d}",
                "kind": "subagent_reference",
                "agent": agent_value or None,
                "source_path": source_path,
                "resolved": True,
                "notes": "Body text contains delegation instructions.",
            }
        )

    return nodes


def _build_analysis_findings(
    *,
    supporting_files: list[dict[str, Any]],
    unresolved_refs: list[str],
    command_references: list[dict[str, Any]],
    delegation_nodes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    findings = []

    for ref in unresolved_refs:
        findings.append(
            {
                "finding_id": f"fd_{len(findings) + 1:03d}",
                "title": f"Unresolved reference: {ref}",
                "category": "reference_integrity",
                "severity": "medium",
                "confidence": "high",
                "affected_paths": [ref],
                "evidence": [
                    {
                        "kind": "missing_reference",
                        "source_path": ref,
                        "excerpt": ref,
                        "explanation": "The referenced file could not be resolved from the entry skill.",
                    }
                ],
                "recommended_action": "resolve_reference",
            }
        )

    for command in command_references:
        if command["risk_grade"] not in {"medium", "high"}:
            continue
        findings.append(
            {
                "finding_id": f"fd_{len(findings) + 1:03d}",
                "title": f"Authority-bearing command: {command['command'][:60]}",
                "category": "execution_authority",
                "severity": "high" if command["risk_grade"] == "high" else "medium",
                "confidence": "high",
                "affected_paths": [command["source_path"]],
                "evidence": [
                    {
                        "kind": "command_snippet",
                        "source_path": command["source_path"],
                        "excerpt": command["command"],
                        "explanation": f"Command classified as {command['authority_profile']}.",
                    }
                ],
                "recommended_action": "review_before_run",
            }
        )

    if delegation_nodes:
        findings.append(
            {
                "finding_id": f"fd_{len(findings) + 1:03d}",
                "title": "Delegation path present",
                "category": "control_flow",
                "severity": "info",
                "confidence": "high",
                "affected_paths": [node["source_path"] for node in delegation_nodes],
                "evidence": [
                    {
                        "kind": "delegation_signal",
                        "source_path": node["source_path"],
                        "excerpt": node["notes"],
                        "explanation": node["kind"],
                    }
                    for node in delegation_nodes
                ],
                "recommended_action": "confirm_scope",
            }
        )

    if supporting_files and all(not item["resolved"] for item in supporting_files):
        findings.append(
            {
                "finding_id": f"fd_{len(findings) + 1:03d}",
                "title": "All supporting references are unresolved",
                "category": "hidden_dependency",
                "severity": "medium",
                "confidence": "medium",
                "affected_paths": [item["path"] for item in supporting_files],
                "evidence": [
                    {
                        "kind": "missing_reference",
                        "source_path": item["path"],
                        "excerpt": item["path"],
                        "explanation": "The parser could not resolve any supporting file.",
                    }
                    for item in supporting_files
                ],
                "recommended_action": "document_dependency",
            }
        )

    return findings


def _extract_markdown_links(body: str) -> list[str]:
    refs = []
    for match in re.findall(r"\[[^\]]+\]\(([^)]+)\)", body):
        ref = match.strip()
        if _looks_like_relative_path(ref):
            refs.append(ref)
    return refs


def _extract_inline_paths(body: str) -> list[str]:
    body_without_fences = re.sub(r"```.*?```", "", body, flags=re.DOTALL)
    refs = []
    for match in re.findall(r"`([^`\n]+)`", body_without_fences):
        candidate = match.strip()
        if _looks_like_relative_path(candidate):
            refs.append(candidate)
    return refs


def _extract_frontmatter_paths(metadata: dict[str, str]) -> list[str]:
    refs = []
    for value in metadata.values():
        candidate = value.strip()
        if _looks_like_relative_path(candidate):
            refs.append(candidate)
    return refs


def _looks_like_relative_path(value: str) -> bool:
    if value.startswith(("http://", "https://", "/", "#")):
        return False
    if " " in value and not any(sep in value for sep in ("/", "\\")):
        return False
    suffix = Path(value).suffix.lower()
    return suffix in PATHISH_EXTENSIONS or "/" in value


def _classify_supporting_file_kind(path_str: str) -> str:
    lowered = path_str.lower()
    suffix = Path(path_str).suffix.lower()
    if "template" in lowered or suffix in {".tmpl"}:
        return "template"
    if "script" in lowered or suffix in {".py", ".sh", ".mjs", ".js", ".ts"}:
        return "script"
    if suffix in {".json", ".yaml", ".yml", ".toml"}:
        return "config"
    if suffix in {".md", ".txt"}:
        return "reference"
    return "unknown"


def _summarize_path(path: Path) -> str:
    if path.suffix.lower() in {".md", ".txt"}:
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip().lstrip("#").strip()
            if stripped:
                return stripped[:120]
    return f"{path.suffix.lower() or 'file'} reference"


def _detect_shell_family(command: str) -> str:
    first = command.split()[0].lower()
    if first in {"python", "python3"}:
        return "python"
    if first in {"bash", "sh"}:
        return "posix_shell"
    return first


def _classify_authority_profile(command: str) -> str:
    lowered = command.lower()
    if any(token in lowered for token in ("curl ", "wget ", "http://", "https://")):
        return "network_call"
    if any(token in lowered for token in ("rm ", "docker ", "git push", "npm install", "pip install", "chmod ", "chown ")):
        return "system_mutation"
    if any(token in lowered for token in ("python ", "python3 ", "bash ", "sh ", "node ", "npx ")):
        return "process_exec"
    if any(token in lowered for token in ("tee ", "cp ", "mv ", "touch ", "mkdir ")):
        return "file_write"
    if any(token in lowered for token in ("rg ", "cat ", "ls ", "find ")):
        return "read_only"
    return "unknown_authority"


def _classify_risk_grade(command: str, authority_profile: str) -> str:
    lowered = command.lower()
    if authority_profile == "system_mutation":
        return "high"
    if authority_profile in {"network_call", "process_exec"}:
        return "medium"
    if authority_profile == "file_write":
        return "medium" if "--force" in lowered else "low"
    return "low"


def _relative_to_root(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)
