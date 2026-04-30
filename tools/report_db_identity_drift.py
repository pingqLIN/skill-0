#!/usr/bin/env python3
"""Report identity drift between parsed skills, skills.db, and governance.db."""

from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_PARSED_DIR = Path("parsed")
DEFAULT_SKILLS_DB = Path("skills.db")
DEFAULT_GOVERNANCE_DB = Path("governance") / "db" / "governance.db"


@dataclass(frozen=True)
class ParsedSkill:
    skill_id: str
    name: str
    source_path: str
    file: str


@dataclass(frozen=True)
class VectorSkill:
    row_id: int
    skill_id: str | None
    name: str
    filename: str
    source_path: str | None


@dataclass(frozen=True)
class GovernanceSkill:
    skill_id: str
    name: str
    source_path: str
    current_revision_id: str | None
    source_checksum: str | None


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} does not contain a JSON object")
    return payload


def load_parsed_skills(parsed_dir: Path) -> list[ParsedSkill]:
    skills: list[ParsedSkill] = []
    for path in sorted(parsed_dir.glob("*.json")):
        payload = _read_json(path)
        meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
        original = (
            payload.get("original_definition")
            if isinstance(payload.get("original_definition"), dict)
            else {}
        )
        skill_id = str(meta.get("skill_id") or "").strip()
        name = str(meta.get("name") or meta.get("title") or path.stem).strip()
        source_path = str(original.get("source") or "").strip()
        if skill_id:
            skills.append(
                ParsedSkill(
                    skill_id=skill_id,
                    name=name,
                    source_path=source_path,
                    file=path.as_posix(),
                )
            )
    return skills


def _connect_readonly(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type IN ('table', 'view') AND name = ?",
        (table,),
    ).fetchone()
    return row is not None


def load_vector_skills(db_path: Path) -> tuple[list[VectorSkill], list[str]]:
    warnings: list[str] = []
    if not db_path.exists():
        return [], [f"skills_db_missing:{db_path.as_posix()}"]
    with _connect_readonly(db_path) as conn:
        if not _table_exists(conn, "skills"):
            return [], [f"skills_table_missing:{db_path.as_posix()}"]
        rows = conn.execute(
            "SELECT id, name, filename, raw_json FROM skills ORDER BY name"
        ).fetchall()

    skills: list[VectorSkill] = []
    for row in rows:
        skill_id: str | None = None
        source_path: str | None = None
        raw_json = row["raw_json"]
        if raw_json:
            try:
                payload = json.loads(raw_json)
            except json.JSONDecodeError:
                warnings.append(f"vector_raw_json_invalid:{row['id']}")
            else:
                meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
                original = (
                    payload.get("original_definition")
                    if isinstance(payload.get("original_definition"), dict)
                    else {}
                )
                skill_id = str(meta.get("skill_id") or "").strip() or None
                source_path = str(original.get("source") or "").strip() or None
        skills.append(
            VectorSkill(
                row_id=int(row["id"]),
                skill_id=skill_id,
                name=str(row["name"] or ""),
                filename=str(row["filename"] or ""),
                source_path=source_path,
            )
        )
    return skills, warnings


def load_governance_skills(db_path: Path) -> tuple[list[GovernanceSkill], list[str]]:
    if not db_path.exists():
        return [], [f"governance_db_missing:{db_path.as_posix()}"]
    with _connect_readonly(db_path) as conn:
        if not _table_exists(conn, "skills"):
            return [], [f"governance_skills_table_missing:{db_path.as_posix()}"]
        has_revisions = _table_exists(conn, "skill_revisions")
        if has_revisions:
            rows = conn.execute(
                """
                SELECT
                    s.skill_id,
                    s.name,
                    COALESCE(sr.source_path, s.source_path, '') AS source_path,
                    s.current_revision_id,
                    sr.source_checksum
                FROM skills s
                LEFT JOIN skill_revisions sr ON sr.revision_id = s.current_revision_id
                ORDER BY s.name
                """
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT skill_id, name, COALESCE(source_path, '') AS source_path,
                       NULL AS current_revision_id, NULL AS source_checksum
                FROM skills
                ORDER BY name
                """
            ).fetchall()

    return [
        GovernanceSkill(
            skill_id=str(row["skill_id"]),
            name=str(row["name"] or ""),
            source_path=str(row["source_path"] or ""),
            current_revision_id=row["current_revision_id"],
            source_checksum=row["source_checksum"],
        )
        for row in rows
    ], []


def _name_key(value: str) -> str:
    return value.strip().lower().replace("_", "-")


def build_report(parsed: list[ParsedSkill], vector: list[VectorSkill], governance: list[GovernanceSkill], warnings: list[str]) -> dict[str, Any]:
    parsed_ids = {skill.skill_id for skill in parsed}
    parsed_names = {_name_key(skill.name) for skill in parsed}
    parsed_sources = {skill.source_path for skill in parsed if skill.source_path}

    vector_ids = {skill.skill_id for skill in vector if skill.skill_id}
    vector_rows_without_skill_id = [
        {"row_id": skill.row_id, "name": skill.name, "filename": skill.filename}
        for skill in vector
        if not skill.skill_id
    ]

    governance_missing_current_revision = [
        {"skill_id": skill.skill_id, "name": skill.name}
        for skill in governance
        if not skill.current_revision_id
    ]
    governance_without_checksum = [
        {
            "skill_id": skill.skill_id,
            "name": skill.name,
            "current_revision_id": skill.current_revision_id,
        }
        for skill in governance
        if skill.current_revision_id and not skill.source_checksum
    ]
    governance_unmatched_to_parsed = [
        {"skill_id": skill.skill_id, "name": skill.name, "source_path": skill.source_path}
        for skill in governance
        if _name_key(skill.name) not in parsed_names and skill.source_path not in parsed_sources
    ]

    drift = {
        "parsed_missing_from_vector": sorted(parsed_ids - vector_ids) if vector else [],
        "vector_missing_from_parsed": sorted(vector_ids - parsed_ids),
        "vector_rows_without_skill_id": vector_rows_without_skill_id,
        "governance_missing_current_revision": governance_missing_current_revision,
        "governance_without_revision_checksum": governance_without_checksum,
        "governance_unmatched_to_parsed": governance_unmatched_to_parsed,
    }
    drift_count = sum(len(items) for items in drift.values())

    status = "ok"
    if warnings:
        status = "warning"
    if drift_count:
        status = "drift_detected"

    return {
        "status": status,
        "counts": {
            "parsed": len(parsed),
            "vector": len(vector),
            "governance": len(governance),
        },
        "warnings": warnings,
        "drift": drift,
    }


def _print_text(report: dict[str, Any]) -> None:
    print(f"Status: {report['status']}")
    counts = report["counts"]
    print(
        "Counts: "
        f"parsed={counts['parsed']} vector={counts['vector']} governance={counts['governance']}"
    )
    for warning in report["warnings"]:
        print(f"Warning: {warning}")
    for key, items in report["drift"].items():
        print(f"{key}: {len(items)}")
        for item in items[:10]:
            print(f"  - {item}")
        if len(items) > 10:
            print(f"  ... {len(items) - 10} more")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Report identity drift across parsed skills, skills.db, and governance.db."
    )
    parser.add_argument("--parsed-dir", type=Path, default=DEFAULT_PARSED_DIR)
    parser.add_argument("--skills-db", type=Path, default=DEFAULT_SKILLS_DB)
    parser.add_argument("--governance-db", type=Path, default=DEFAULT_GOVERNANCE_DB)
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument(
        "--allow-missing-db",
        action="store_true",
        help="Return success when runtime DB files are absent but parsed skills can be read.",
    )
    args = parser.parse_args(argv)

    parsed = load_parsed_skills(args.parsed_dir)
    vector, vector_warnings = load_vector_skills(args.skills_db)
    governance, governance_warnings = load_governance_skills(args.governance_db)
    warnings = vector_warnings + governance_warnings
    report = build_report(parsed, vector, governance, warnings)

    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        _print_text(report)

    if report["status"] == "drift_detected":
        return 1
    if warnings and not args.allow_missing_db:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
