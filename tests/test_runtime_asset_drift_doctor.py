from __future__ import annotations

import json
import sqlite3

from jsonschema.validators import validator_for

from asset_registry.repositories import LegacySkillAssetRepository
from tools.runtime_asset_drift_doctor import build_doctor_report


def _write_skill(path, skill_id="claude__skill__doctor"):
    path.write_text(
        json.dumps(
            {
                "meta": {
                    "skill_id": skill_id,
                    "name": "doctor",
                    "description": "doctor fixture",
                    "parsed_by": "doctor-test",
                    "parser_version": "1.0.0",
                },
                "decomposition": {"actions": [], "rules": [], "directives": []},
            }
        ),
        encoding="utf-8",
    )


def _create_index(path, revision):
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE asset_index_state (
                asset_id TEXT, revision_id TEXT, representation_version TEXT,
                embedding_model_id TEXT, embedding_model_version TEXT,
                content_hash TEXT, skill_row_id INTEGER, vector_row_id INTEGER,
                source_path TEXT, indexed_at TEXT
            )
            """
        )
        connection.execute(
            "INSERT INTO asset_index_state VALUES (?, ?, 'skill-text-v1', 'fixture', '1', ?, 1, 1, ?, 'now')",
            (
                revision.asset_id,
                revision.revision_id,
                revision.content_hash,
                revision.source_path.as_posix(),
            ),
        )


def _create_governance(path, revision):
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE skills (skill_id TEXT, canonical_skill_id TEXT, current_revision_id TEXT)"
        )
        connection.execute(
            "CREATE TABLE skill_revisions (skill_id TEXT, revision_id TEXT, artifact_digest TEXT, status TEXT, is_current INTEGER)"
        )
        connection.execute(
            "INSERT INTO skills VALUES ('gov', ?, 'gov-rev')", (revision.asset_id,)
        )
        connection.execute(
            "INSERT INTO skill_revisions VALUES ('gov', 'gov-rev', ?, 'approved', 1)",
            (revision.content_hash,),
        )


def test_doctor_reports_healthy_and_validates_schema(root, tmp_path):
    parsed = tmp_path / "parsed"
    parsed.mkdir()
    _write_skill(parsed / "doctor.json")
    revision = LegacySkillAssetRepository(parsed).list_revisions()[0]
    index = tmp_path / "index.db"
    governance = tmp_path / "governance.db"
    _create_index(index, revision)
    _create_governance(governance, revision)

    report = build_doctor_report(
        parsed_dir=parsed, index_db=index, governance_db=governance
    )
    schema = json.loads(
        (root / "schema/runtime-asset-drift-report.schema.json").read_text(
            encoding="utf-8"
        )
    )
    validator_class = validator_for(schema)
    validator_class.check_schema(schema)
    assert list(validator_class(schema).iter_errors(report)) == []
    assert report["state"] == "healthy"
    assert report["exit_code"] == 0


def test_doctor_state_precedence(tmp_path):
    parsed = tmp_path / "parsed"
    parsed.mkdir()
    _write_skill(parsed / "doctor.json")

    authority = build_doctor_report(
        parsed_dir=parsed,
        index_db=tmp_path / "missing-index.db",
        governance_db=tmp_path / "missing-governance.db",
    )
    assert authority["state"] == "authority-missing"
    assert authority["exit_code"] == 2

    (parsed / "doctor.json").write_text("{", encoding="utf-8")
    unknown = build_doctor_report(
        parsed_dir=parsed,
        index_db=tmp_path / "missing-index.db",
        governance_db=tmp_path / "missing-governance.db",
    )
    assert unknown["state"] == "unknown"
    assert unknown["exit_code"] == 3


def test_doctor_distinguishes_stale_projection(tmp_path):
    parsed = tmp_path / "parsed"
    parsed.mkdir()
    _write_skill(parsed / "doctor.json")
    revision = LegacySkillAssetRepository(parsed).list_revisions()[0]
    governance = tmp_path / "governance.db"
    _create_governance(governance, revision)

    report = build_doctor_report(
        parsed_dir=parsed,
        index_db=tmp_path / "missing-index.db",
        governance_db=governance,
    )
    assert report["state"] == "stale-derived-projection"
    assert report["findings"]["pending_projection"] == ["doctor.json"]
