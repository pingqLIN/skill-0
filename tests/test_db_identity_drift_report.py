import json
import sqlite3
from pathlib import Path

from tools import report_db_identity_drift


def _write_parsed(path: Path, skill_id: str, name: str, source: str) -> None:
    path.write_text(
        json.dumps(
            {
                "meta": {"skill_id": skill_id, "name": name},
                "original_definition": {"source": source},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def _create_vector_db(path: Path, rows: list[dict]) -> None:
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE skills (
            id INTEGER PRIMARY KEY,
            name TEXT,
            filename TEXT,
            raw_json TEXT
        )
        """
    )
    for index, row in enumerate(rows, start=1):
        conn.execute(
            "INSERT INTO skills (id, name, filename, raw_json) VALUES (?, ?, ?, ?)",
            (
                index,
                row["name"],
                row.get("filename", f"{row['name']}.json"),
                json.dumps(row["raw_json"], ensure_ascii=False),
            ),
        )
    conn.commit()
    conn.close()


def _create_governance_db(path: Path, rows: list[dict]) -> None:
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE skills (
            skill_id TEXT PRIMARY KEY,
            name TEXT,
            source_path TEXT,
            current_revision_id TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE skill_revisions (
            revision_id TEXT PRIMARY KEY,
            source_path TEXT,
            source_checksum TEXT
        )
        """
    )
    for row in rows:
        conn.execute(
            "INSERT INTO skills VALUES (?, ?, ?, ?)",
            (
                row["skill_id"],
                row["name"],
                row.get("source_path", ""),
                row.get("current_revision_id"),
            ),
        )
        if row.get("current_revision_id"):
            conn.execute(
                "INSERT INTO skill_revisions VALUES (?, ?, ?)",
                (
                    row["current_revision_id"],
                    row.get("source_path", ""),
                    row.get("source_checksum"),
                ),
            )
    conn.commit()
    conn.close()


def test_identity_report_allows_missing_runtime_databases(tmp_path):
    parsed_dir = tmp_path / "parsed"
    parsed_dir.mkdir()
    _write_parsed(parsed_dir / "one.json", "claude__skill__one", "one", "converted-skills/one/SKILL.md")

    exit_code = report_db_identity_drift.main(
        [
            "--parsed-dir",
            str(parsed_dir),
            "--skills-db",
            str(tmp_path / "missing-skills.db"),
            "--governance-db",
            str(tmp_path / "missing-governance.db"),
            "--allow-missing-db",
        ]
    )

    assert exit_code == 0


def test_identity_report_detects_vector_and_governance_drift(tmp_path):
    parsed_dir = tmp_path / "parsed"
    parsed_dir.mkdir()
    _write_parsed(parsed_dir / "one.json", "claude__skill__one", "one", "converted-skills/one/SKILL.md")
    _write_parsed(parsed_dir / "two.json", "claude__skill__two", "two", "converted-skills/two/SKILL.md")

    skills_db = tmp_path / "skills.db"
    _create_vector_db(
        skills_db,
        [
            {
                "name": "one",
                "raw_json": {
                    "meta": {"skill_id": "claude__skill__one"},
                    "original_definition": {"source": "converted-skills/one/SKILL.md"},
                },
            },
            {
                "name": "stale",
                "raw_json": {
                    "meta": {"skill_id": "claude__skill__stale"},
                    "original_definition": {"source": "converted-skills/stale/SKILL.md"},
                },
            },
        ],
    )

    governance_db = tmp_path / "governance.db"
    _create_governance_db(
        governance_db,
        [
            {
                "skill_id": "gov-one",
                "name": "one",
                "source_path": "converted-skills/one/SKILL.md",
                "current_revision_id": "rev-one",
                "source_checksum": "abc",
            },
            {
                "skill_id": "gov-orphan",
                "name": "orphan",
                "source_path": "converted-skills/orphan/SKILL.md",
                "current_revision_id": None,
            },
        ],
    )

    parsed = report_db_identity_drift.load_parsed_skills(parsed_dir)
    vector, vector_warnings = report_db_identity_drift.load_vector_skills(skills_db)
    governance, governance_warnings = report_db_identity_drift.load_governance_skills(governance_db)
    report = report_db_identity_drift.build_report(
        parsed, vector, governance, vector_warnings + governance_warnings
    )

    assert report["status"] == "drift_detected"
    assert report["drift"]["parsed_missing_from_vector"] == ["claude__skill__two"]
    assert report["drift"]["vector_missing_from_parsed"] == ["claude__skill__stale"]
    assert report["drift"]["governance_missing_current_revision"] == [
        {"skill_id": "gov-orphan", "name": "orphan"}
    ]
    assert report["drift"]["governance_unmatched_to_parsed"] == [
        {
            "skill_id": "gov-orphan",
            "name": "orphan",
            "source_path": "converted-skills/orphan/SKILL.md",
        }
    ]
