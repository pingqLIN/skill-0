from __future__ import annotations

import re
import shutil
import sqlite3
from pathlib import Path

from runtime.ledger import RuntimeLedger
from scripts.runtime_doctor import run_doctor
from tools.governance_db import GovernanceDB
from vector_db.model_artifact import compute_model_artifact_digest


ROOT = Path(__file__).resolve().parents[1]


def test_production_docker_stages_pin_image_digests():
    for dockerfile_name in ("Dockerfile.api", "Dockerfile.dashboard", "Dockerfile.web"):
        dockerfile = (ROOT / dockerfile_name).read_text(encoding="utf-8")
        base_lines = [
            line for line in dockerfile.splitlines() if line.startswith("FROM ")
        ]

        assert base_lines
        for line in base_lines:
            image = line.split()[1]
            assert re.search(r"@sha256:[0-9a-f]{64}$", image), (
                f"{dockerfile_name} has an unpinned base stage: {line}"
            )


def test_web_runtime_uses_reviewed_zero_finding_base():
    dockerfile = (ROOT / "Dockerfile.web").read_text(encoding="utf-8")

    assert (
        "nginxinc/nginx-unprivileged:1.31.3-alpine3.24-slim"
        "@sha256:90d82b3358df5758b3c57d20f2565082ce6f744906e7dc09afd0096c1b8eb2b5"
        in dockerfile
    )


def test_api_and_dashboard_use_reviewed_zero_finding_bases():
    api_dockerfile = (ROOT / "Dockerfile.api").read_text(encoding="utf-8")
    dashboard_dockerfile = (ROOT / "Dockerfile.dashboard").read_text(
        encoding="utf-8"
    )

    assert api_dockerfile.count(
        "ubuntu:24.04"
        "@sha256:4fbb8e6a8395de5a7550b33509421a2bafbc0aab6c06ba2cef9ebffbc7092d90"
    ) == 2
    assert (
        "python:3.12-alpine3.24"
        "@sha256:f7fd610959cae736251523b54eb26cecb74f60ffa60bf39d9faccf128b526ab8"
        in dashboard_dockerfile
    )
    assert '"pip>=26.1.2,<27"' in api_dockerfile
    assert '"pip>=26.1.2,<27"' in dashboard_dockerfile


def test_legacy_partial_requirements_lock_is_not_an_authority_file():
    assert not (ROOT / "requirements.lock").exists()
    assert (ROOT / "requirements-api.txt").is_file()
    assert (ROOT / "requirements-runtime.txt").is_file()
    assert (ROOT / "requirements-dev.txt").is_file()


def _configure_production_environment(monkeypatch, tmp_path: Path) -> dict[str, Path]:
    skills_db = tmp_path / "skills.db"
    governance_db = tmp_path / "governance.db"
    runtime_db = tmp_path / "runtime.db"
    parsed_dir = tmp_path / "parsed"
    parsed_dir.mkdir()
    (parsed_dir / "fixture.json").write_text("{}", encoding="utf-8")
    model_dir = tmp_path / "approved-model"
    model_dir.mkdir()
    (model_dir / "config.json").write_text("{}\n", encoding="utf-8")
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
    monkeypatch.setenv("SKILL0_EMBEDDING_MODEL", str(model_dir.resolve()))
    monkeypatch.setenv(
        "SKILL0_EMBEDDING_MODEL_ARTIFACT_DIGEST",
        compute_model_artifact_digest(model_dir),
    )
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


def test_production_doctor_rejects_runtime_initialization_mode_without_backup_gate(
    tmp_path, monkeypatch
):
    _configure_production_environment(monkeypatch, tmp_path)
    monkeypatch.setenv("SKILL0_RUNTIME_ALLOW_INITIALIZE", "true")

    report = run_doctor(
        production=True,
        require_backups=False,
        backup_dir=tmp_path / "backups",
        max_backup_age_days=2,
    )

    assert "runtime_initialization_is_enabled" in report["errors"]
    assert "runtime_initialization_is_enabled" not in report["warnings"]


def test_production_doctor_rejects_model_artifact_drift(tmp_path, monkeypatch):
    _configure_production_environment(monkeypatch, tmp_path)
    monkeypatch.setenv(
        "SKILL0_EMBEDDING_MODEL_ARTIFACT_DIGEST",
        "sha256:" + "0" * 64,
    )

    report = run_doctor(
        production=True,
        require_backups=False,
        backup_dir=tmp_path / "backups",
        max_backup_age_days=2,
    )

    assert report["status"] == "failed"
    assert "embedding_model_artifact_digest_mismatch" in report["errors"]
    assert report["checks"]["embedding_model_artifact"] == {"verified": False}


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
    assert "SKILL0_EMBEDDING_MODEL_ARTIFACT_DIGEST:" in compose
    assert "model-cache:/app/.cache:ro" in compose
    assert 'HF_HUB_OFFLINE: "1"' in compose
    assert 'TRANSFORMERS_OFFLINE: "1"' in compose
    assert "dashboard:\n        condition: service_healthy" in compose
    assert '${SKILL0_BIND_ADDRESS:-127.0.0.1}:${API_PORT:-8080}:8000' in compose
    assert '${SKILL0_BIND_ADDRESS:-127.0.0.1}:${WEB_PORT:-3080}:8080' in compose

    dockerfile = (ROOT / "Dockerfile.api").read_text(encoding="utf-8")
    assert "--mount=type=secret,id=build_ca,required=false" in dockerfile
    assert "--trusted-host" not in dockerfile
    assert "rm -f \"$ca_path\"" in dockerfile
    assert "COPY requirements-api.txt requirements-runtime.txt ./" in dockerfile
    assert "pip install --no-cache-dir -r requirements-runtime.txt" in dockerfile
    assert "COPY skills.db" not in dockerfile
    assert "VectorStore('/app/bootstrap/skills.db').close()" in dockerfile
    assert "HF_HUB_OFFLINE=1" not in dockerfile
    assert "TRANSFORMERS_OFFLINE=1" not in dockerfile

    runtime_requirements = (ROOT / "requirements-runtime.txt").read_text(
        encoding="utf-8"
    )
    assert "jsonschema>=4.23,<5" in runtime_requirements
    assert "cryptography>=49,<50" in runtime_requirements

    dashboard_dockerfile = (ROOT / "Dockerfile.dashboard").read_text(
        encoding="utf-8"
    )
    assert "COPY runtime/digest.py ./runtime/digest.py" in dashboard_dockerfile
    assert "COPY parsed/ ./parsed/" in dashboard_dockerfile
    assert "COPY runtime/ ./runtime/" not in dashboard_dockerfile
    assert "COPY governance/" not in dashboard_dockerfile

    dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")
    assert "governance/db/" in dockerignore


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
    assert '?mode=ro",uri=True' in rehearsal
    assert 'skill0-runtime-db:/runtime" python:3.12-slim python -c $storageCheck' in rehearsal
    assert "Runtime production doctor" in rehearsal
    assert "Initialize disposable Runtime ledger before production startup" in rehearsal
    assert '"--entrypoint", "python", "api"' in rehearsal
    assert "RuntimeLedger(\"/app/runtime-data/runtime.db\"" in rehearsal
    assert "SKILL0_RUNTIME_ALLOW_INITIALIZE=false" in rehearsal
    assert "SKILL0_RUNTIME_ALLOW_INITIALIZE=true" not in rehearsal
    assert "Governed Runtime dry-run and deterministic Evidence" in rehearsal
    assert "governance_runtime_approval" in rehearsal
    assert 'Uri "http://127.0.0.1:$ApiPort/api/runs"' in rehearsal
    assert "$firstEvidence.Content -cne $secondEvidence.Content" in rehearsal
    assert "runtime_evidence_sha256=" in rehearsal
    assert "Runtime public projection exposed private rehearsal material" in rehearsal
    assert "API restart persistence" in rehearsal
    assert "runtime-rehearsal-sentinel" in rehearsal
    assert "sentinel_ok" in rehearsal
    assert "runtime_sentinel_after_restart" in rehearsal
    assert "BuildCaFile" in rehearsal
    assert "build_ca" in rehearsal
    assert "Provision disposable approved model artifact" in rehearsal
    assert "--user root" in rehearsal
    assert "compute_model_artifact_digest" in rehearsal
    assert "SKILL0_EMBEDDING_MODEL_ARTIFACT_DIGEST" in rehearsal
    assert "failed with exit code" in rehearsal
    assert "$rehearsalPassed = $false" in rehearsal
    assert "if (-not $KeepRunning -or -not $rehearsalPassed)" in rehearsal
    assert 'Invoke-Compose -ComposeArgs @("up", "--detach")' in rehearsal
    assert "Assert-LocalPortAvailable -Port $ApiPort" in rehearsal
    assert "Assert-LocalPortAvailable -Port $WebPort" in rehearsal
    assert "Assert-NoExistingComposeResources" in rehearsal
    assert 'com.docker.compose.project=$ProjectName' in rehearsal
    assert 'docker network ls --quiet --filter "label=$projectLabel"' in rehearsal
    assert "choose a unique -ProjectName" in rehearsal
    assert "SKILL0_BIND_ADDRESS=127.0.0.1" in rehearsal
    assert '"$ProjectName-$PID.env"' in rehearsal

    entrypoint = (ROOT / "scripts" / "docker-entrypoint-api.sh").read_text(
        encoding="utf-8"
    )
    assert 'export SKILL0_DB_PATH="$RUNTIME_DB"' in entrypoint
    assert 'export SKILL0_RUNTIME_DB_PATH="$RUNTIME_LEDGER"' in entrypoint
    assert 'export SKILL0_RUNTIME_JOURNAL_MODE="$RUNTIME_JOURNAL_MODE"' in entrypoint
    assert 'export SKILL0_RUNTIME_HITL_TTL_SECONDS="$HITL_TTL_SECONDS"' in entrypoint
    assert (
        'export SKILL0_RUNTIME_ALLOW_INITIALIZE="$ALLOW_RUNTIME_INITIALIZE"'
        in entrypoint
    )
    assert "SKILL0_RUNTIME_ALLOW_INITIALIZE" in entrypoint
    assert "Runtime ledger is missing" in entrypoint
    assert "Runtime initialization must be disabled in production" in entrypoint
    assert "set SKILL0_RUNTIME_ALLOW_INITIALIZE=true" not in entrypoint
