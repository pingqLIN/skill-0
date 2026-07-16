from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

from runtime.ledger import RuntimeLedger
from scripts.runtime_doctor import run_doctor
from tools.governance_db import GovernanceDB


ROOT = Path(__file__).resolve().parents[1]


def _configure_production_environment(monkeypatch, tmp_path: Path) -> dict[str, Path]:
    skills_db = tmp_path / "skills.db"
    governance_db = tmp_path / "governance.db"
    runtime_db = tmp_path / "runtime.db"
    parsed_dir = tmp_path / "parsed"
    parsed_dir.mkdir()
    (parsed_dir / "fixture.json").write_text("{}", encoding="utf-8")
    sqlite3.connect(skills_db).close()
    GovernanceDB(db_path=governance_db)
    with RuntimeLedger(runtime_db, journal_mode="WAL"):
        pass

    monkeypatch.setenv("SKILL0_ENV", "production")
    monkeypatch.setenv("SKILL0_DB_PATH", str(skills_db))
    monkeypatch.setenv("SKILL0_GOVERNANCE_DB_PATH", str(governance_db))
    monkeypatch.setenv("SKILL0_RUNTIME_DB_PATH", str(runtime_db))
    monkeypatch.setenv("SKILL0_PARSED_DIR", str(parsed_dir))
    monkeypatch.setenv(
        "SKILL0_RUNTIME_BINDING_KEY",
        "runtime-production-binding-key-0123456789",
    )
    monkeypatch.setenv("JWT_SECRET_KEY", "jwt-production-key-0123456789")
    monkeypatch.setenv("SKILL0_RUNTIME_DECISION_ACTORS", "runtime-reviewer")
    monkeypatch.setenv("SKILL0_RUNTIME_HITL_TTL_SECONDS", "86400")
    monkeypatch.setenv("SKILL0_RUNTIME_JOURNAL_MODE", "WAL")
    return {
        "skills": skills_db,
        "governance": governance_db,
        "runtime": runtime_db,
    }


def test_runtime_doctor_passes_three_store_release_gate(
    tmp_path, monkeypatch
):
    databases = _configure_production_environment(monkeypatch, tmp_path)
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    for prefix, source in databases.items():
        shutil.copy2(source, backup_dir / f"{prefix}_20260716_000000.db")

    report = run_doctor(
        production=True,
        require_backups=True,
        backup_dir=backup_dir,
        max_backup_age_days=2,
    )

    assert report["status"] == "healthy"
    assert report["errors"] == []
    assert report["checks"]["runtime_db"]["journal_mode"] == "wal"


def test_runtime_doctor_fails_closed_when_runtime_store_is_missing(
    tmp_path, monkeypatch
):
    databases = _configure_production_environment(monkeypatch, tmp_path)
    databases["runtime"].unlink()

    report = run_doctor(
        production=True,
        require_backups=False,
        backup_dir=tmp_path / "backups",
        max_backup_age_days=2,
    )

    assert report["status"] == "failed"
    assert any(issue.startswith("runtime_db_missing:") for issue in report["errors"])


def test_release_gate_rejects_runtime_initialization_mode(tmp_path, monkeypatch):
    _configure_production_environment(monkeypatch, tmp_path)
    monkeypatch.setenv("SKILL0_RUNTIME_ALLOW_INITIALIZE", "true")

    report = run_doctor(
        production=True,
        require_backups=True,
        backup_dir=tmp_path / "missing-backups",
        max_backup_age_days=2,
    )

    assert "runtime_initialization_is_enabled" in report["errors"]


def test_release_gate_rejects_corrupt_runtime_backup(tmp_path, monkeypatch):
    databases = _configure_production_environment(monkeypatch, tmp_path)
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    for prefix, source in databases.items():
        shutil.copy2(source, backup_dir / f"{prefix}_20260716_000000.db")
    (backup_dir / "runtime_20260716_000000.db").write_bytes(b"not sqlite")

    report = run_doctor(
        production=True,
        require_backups=True,
        backup_dir=backup_dir,
        max_backup_age_days=2,
    )

    assert report["status"] == "failed"
    assert any(
        issue.startswith("runtime_backup_unreadable:")
        for issue in report["errors"]
    )


def test_production_compose_persists_runtime_and_reads_governance_db():
    compose = (ROOT / "docker-compose.prod.yml").read_text(encoding="utf-8")

    assert "SKILL0_RUNTIME_DB_PATH: /app/runtime-data/runtime.db" in compose
    assert "SKILL0_GOVERNANCE_DB_PATH: /app/governance/db/governance.db" in compose
    assert "skill0-runtime-db:/app/runtime-data" in compose
    assert "skill0-governance-db:/app/governance/db:ro" in compose
    assert "SKILL0_RUNTIME_JOURNAL_MODE: WAL" in compose
    assert "SKILL0_RUNTIME_ALLOW_INITIALIZE: ${SKILL0_RUNTIME_ALLOW_INITIALIZE:-false}" in compose
    assert "dashboard:\n        condition: service_healthy" in compose


def test_maintenance_scripts_cover_all_three_databases():
    backup = (ROOT / "scripts" / "backup_db.sh").read_text(encoding="utf-8")
    health = (ROOT / "scripts" / "check_db_health.sh").read_text(
        encoding="utf-8"
    )

    for text in (backup, health):
        assert "SKILL0_RUNTIME_DB_PATH" in text
        assert '"runtime"' in text
        assert '"runtime.db"' in text

    rehearsal = (ROOT / "scripts" / "rehearse_prod_compose.ps1").read_text(
        encoding="utf-8"
    )
    assert "skill0-runtime-db:/runtime:ro" in rehearsal
    assert "Three-store online backup and restore verification" in rehearsal
    assert "Runtime production doctor" in rehearsal
    assert "API restart persistence" in rehearsal
    assert "runtime-rehearsal-sentinel" in rehearsal
    assert "sentinel_ok" in rehearsal
    assert "runtime_sentinel_after_restart" in rehearsal

    entrypoint = (ROOT / "scripts" / "docker-entrypoint-api.sh").read_text(
        encoding="utf-8"
    )
    assert "SKILL0_RUNTIME_ALLOW_INITIALIZE" in entrypoint
    assert "Runtime ledger is missing" in entrypoint
