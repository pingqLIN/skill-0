from __future__ import annotations

import json
import subprocess
import sys

from runtime.ledger import RuntimeLedger
from runtime.models import RuntimeEvent, RuntimeEventType


def test_runtime_evidence_cli_renders_deterministic_run_summary(tmp_path, root):
    database = tmp_path / "runtime.db"
    with RuntimeLedger(database) as ledger:
        run_id = ledger.create_run(skill_name="demo", skill_version="1")
        ledger.append_event(
            RuntimeEvent(
                run_id=run_id,
                event_type=RuntimeEventType.RUN_SUCCEEDED,
                skill_name="demo",
                skill_version="1",
                action_id="a_001",
            )
        )

    command = [
        sys.executable,
        str(root / "scripts" / "runtime_evidence.py"),
        "--db",
        str(database),
        "--run-id",
        run_id,
    ]
    first = subprocess.run(command, cwd=root, check=True, capture_output=True, text=True)
    second = subprocess.run(command, cwd=root, check=True, capture_output=True, text=True)
    assert first.stdout == second.stdout
    summary = json.loads(first.stdout)
    assert summary["run_ref"] == {"run_id": run_id, "status": "succeeded"}
    assert summary["event_count"] == 2
    assert summary["last_event_type"] == "run_succeeded"

    output = tmp_path / "evidence.json"
    written = subprocess.run(
        [*command, "--output", str(output)],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    assert written.stdout == ""
    assert json.loads(output.read_text(encoding="utf-8")) == summary
    assert list(tmp_path.glob("evidence.json.*.tmp")) == []


def test_runtime_evidence_cli_returns_two_for_missing_run(tmp_path, root):
    database = tmp_path / "runtime.db"
    with RuntimeLedger(database):
        pass
    result = subprocess.run(
        [
            sys.executable,
            str(root / "scripts" / "runtime_evidence.py"),
            "--db",
            str(database),
            "--run-id",
            "missing",
        ],
        cwd=root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert result.stderr.strip() == "Run not found"


def test_runtime_evidence_cli_does_not_create_missing_database(tmp_path, root):
    database = tmp_path / "missing.db"
    result = subprocess.run(
        [
            sys.executable,
            str(root / "scripts" / "runtime_evidence.py"),
            "--db",
            str(database),
            "--run-id",
            "missing",
        ],
        cwd=root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert result.stderr.strip() == "Runtime ledger not found"
    assert not database.exists()


def test_runtime_evidence_cli_hides_corrupt_ledger_details(tmp_path, root):
    database = tmp_path / "runtime.db"
    database.write_bytes(b"invalid sqlite secret-value")
    result = subprocess.run(
        [
            sys.executable,
            str(root / "scripts" / "runtime_evidence.py"),
            "--db",
            str(database),
            "--run-id",
            "anything",
        ],
        cwd=root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert result.stderr.strip() == "Unable to render Runtime Evidence"
    assert "secret-value" not in result.stderr


def test_runtime_evidence_cli_invalid_selector_returns_two(tmp_path, root):
    result = subprocess.run(
        [
            sys.executable,
            str(root / "scripts" / "runtime_evidence.py"),
            "--db",
            str(tmp_path / "runtime.db"),
            "--skill-name",
            "demo",
        ],
        cwd=root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "--skill-version is required" in result.stderr
