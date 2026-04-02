import json
from pathlib import Path

import scripts.auto_parse as auto_parse_module
from scripts.auto_parse import extract_code_commands, parse_skill_md, resolve_skill_dirs, run_auto_parse


def _write_skill(root: Path, name: str, description: str) -> None:
    skill_dir = root / name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "\n".join(
            [
                "---",
                f"name: {name}",
                f"description: {description}",
                "---",
                "# Test Skill",
                "",
                "## Workflow",
                "",
                "- Read the repo state before changing files.",
                "- Never overwrite unrelated parsed output.",
            ]
        ),
        encoding="utf-8",
    )


def test_resolve_skill_dirs_returns_only_requested_names_in_stable_order(tmp_path):
    converted_dir = tmp_path / "converted-skills"
    converted_dir.mkdir()
    _write_skill(converted_dir, "beta", "Beta fixture skill")
    _write_skill(converted_dir, "alpha", "Alpha fixture skill")

    resolved = resolve_skill_dirs(converted_dir, ["alpha", "beta", "alpha"])

    assert [path.name for path in resolved] == ["alpha", "beta"]


def test_run_auto_parse_only_writes_requested_skill(tmp_path):
    converted_dir = tmp_path / "converted-skills"
    parsed_dir = tmp_path / "parsed"
    converted_dir.mkdir()
    parsed_dir.mkdir()

    _write_skill(converted_dir, "alpha", "Alpha fixture skill")
    _write_skill(converted_dir, "beta", "Beta fixture skill")

    beta_output = parsed_dir / "beta-skill.json"
    beta_original = {"meta": {"name": "beta"}, "sentinel": "keep-me"}
    beta_output.write_text(json.dumps(beta_original), encoding="utf-8")

    exit_code = run_auto_parse(
        converted_dir=converted_dir,
        parsed_dir=parsed_dir,
        skill_names=["alpha"],
    )

    assert exit_code == 0
    assert (parsed_dir / "alpha-skill.json").exists()
    assert json.loads(beta_output.read_text(encoding="utf-8")) == beta_original


def test_run_auto_parse_returns_error_for_unknown_skill_without_writing(tmp_path):
    converted_dir = tmp_path / "converted-skills"
    parsed_dir = tmp_path / "parsed"
    converted_dir.mkdir()
    parsed_dir.mkdir()

    _write_skill(converted_dir, "alpha", "Alpha fixture skill")

    exit_code = run_auto_parse(
        converted_dir=converted_dir,
        parsed_dir=parsed_dir,
        skill_names=["missing-skill"],
    )

    assert exit_code == 1
    assert not any(parsed_dir.iterdir())


def test_extract_code_commands_detects_repo_local_python_and_cd_commands():
    body = """
```bash
.venv/bin/python scripts/auto_parse.py --force --skills yolo-unattended
cd skill-0-dashboard/apps/web && npm test && npm run build
```
"""

    commands = extract_code_commands(body)

    assert commands == [
        ".venv/bin/python scripts/auto_parse.py --force --skills yolo-unattended",
        "cd skill-0-dashboard/apps/web && npm test && npm run build",
    ]


def test_parse_skill_md_marks_fenced_commands_as_external_calls():
    content = """
---
name: command-fixture
description: Fixture for fenced command extraction.
---
# Command Fixture

## Validation

```bash
.venv/bin/python scripts/auto_parse.py --force --skills yolo-unattended
cd skill-0-dashboard/apps/web && npm test && npm run build
```
"""

    result = parse_skill_md("command-fixture", content)

    commands = [
        action for action in result["decomposition"]["actions"]
        if action["description"].startswith(".venv/bin/python")
        or action["description"].startswith("cd skill-0-dashboard/apps/web")
    ]

    assert len(commands) == 2
    assert {action["action_type"] for action in commands} == {"external_call"}


def test_parse_skill_md_preserves_full_original_description():
    full_description = "A" * 210 + " 07:00 cutoff support"
    content = (
        f"---\n"
        f"name: description-fixture\n"
        f"description: {full_description}\n"
        f"---\n"
        f"# Description Fixture\n\n"
        f"## Workflow\n\n"
        f"- Read the repo state before changing files.\n"
    )

    result = parse_skill_md("description-fixture", content)

    assert len(result["meta"]["description"]) == 200
    assert result["original_definition"]["skill_description"] == full_description
    assert result["original_definition"]["skill_description"].endswith("07:00 cutoff support")


def test_run_auto_parse_validate_writes_file_when_schema_passes(tmp_path):
    converted_dir = tmp_path / "converted-skills"
    parsed_dir = tmp_path / "parsed"
    converted_dir.mkdir()
    parsed_dir.mkdir()

    _write_skill(converted_dir, "alpha", "Alpha fixture skill")

    exit_code = run_auto_parse(
        converted_dir=converted_dir,
        parsed_dir=parsed_dir,
        skill_names=["alpha"],
        validate=True,
    )

    assert exit_code == 0
    assert (parsed_dir / "alpha-skill.json").exists()


def test_run_auto_parse_validate_skips_write_when_schema_fails(tmp_path, monkeypatch):
    converted_dir = tmp_path / "converted-skills"
    parsed_dir = tmp_path / "parsed"
    converted_dir.mkdir()
    parsed_dir.mkdir()

    _write_skill(converted_dir, "alpha", "Alpha fixture skill")

    class _FakeError:
        absolute_path = ("meta", "name")
        message = "synthetic schema failure"

    monkeypatch.setattr(
        auto_parse_module,
        "iter_validation_errors",
        lambda skill, schema_path: [_FakeError()],
    )

    exit_code = run_auto_parse(
        converted_dir=converted_dir,
        parsed_dir=parsed_dir,
        skill_names=["alpha"],
        validate=True,
    )

    assert exit_code == 1
    assert not (parsed_dir / "alpha-skill.json").exists()
