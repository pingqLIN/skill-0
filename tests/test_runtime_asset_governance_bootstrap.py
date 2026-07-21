from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
import sqlite3

import pytest

from asset_registry.repositories import LegacySkillAssetRepository
from tools.runtime_asset_governance_bootstrap import (
    BootstrapApplyError,
    BootstrapValidationError,
    apply_operator_decision,
    build_candidate_packet,
    build_decision_template,
    main,
    validate_operator_decision,
)


def _write_skill(path, *, skill_id, name, source_name=None):
    payload = {
        "meta": {
            "skill_id": skill_id,
            "name": name,
            "description": f"{name} fixture",
            "parsed_by": "governance-bootstrap-test",
            "parser_version": "1.0.0",
        },
        "decomposition": {"actions": [], "rules": [], "directives": []},
    }
    if source_name is not None:
        payload["original_definition"] = {"skill_name": source_name}
    path.write_text(json.dumps(payload), encoding="utf-8")


def _create_index(path, revisions):
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
        connection.executemany(
            """
            INSERT INTO asset_index_state VALUES (
                ?, ?, 'skill-text-v1', 'fixture', '1', ?, ?, ?, ?, 'now'
            )
            """,
            [
                (
                    revision.asset_id,
                    revision.revision_id,
                    revision.content_hash,
                    row_id,
                    row_id,
                    revision.source_path.as_posix(),
                )
                for row_id, revision in enumerate(revisions, start=1)
            ],
        )


def _approved_decision(packet, *, reject_asset_id=None):
    decision = build_decision_template(packet)
    decision["reviewer"] = "operator:test-reviewer"
    decision["reviewed_at"] = datetime.now(timezone.utc).isoformat()
    for item in decision["decisions"]:
        rejected = item["asset_id"] == reject_asset_id
        item["decision"] = "reject" if rejected else "approve"
        item["reason"] = "fixture rejection" if rejected else "fixture approval"
    return decision


@pytest.fixture
def parsed_fixture(tmp_path):
    parsed = tmp_path / "parsed"
    parsed.mkdir()
    _write_skill(
        parsed / "alpha.json",
        skill_id="claude__skill__alpha",
        name="duplicate-display",
    )
    _write_skill(
        parsed / "pdf.json",
        skill_id="claude__skill__pdf",
        name="duplicate-display",
    )
    for name in ("java-8", "java-11", "java-17"):
        _write_skill(
            parsed / f"{name}.json",
            skill_id="claude__skill__java_upgrade",
            name="java-upgrade",
            source_name=name,
        )
    return parsed


def test_candidate_packet_is_deterministic_and_redacted(parsed_fixture):
    first = build_candidate_packet(parsed_fixture)
    second = build_candidate_packet(parsed_fixture)

    assert first == second
    assert first["candidate_count"] == 5
    assert len({item["asset_id"] for item in first["candidates"]}) == 5
    assert all("findings" not in item["security_scan"] for item in first["candidates"])
    assert all("scanned_at" not in item["security_scan"] for item in first["candidates"])


@pytest.mark.parametrize(
    ("mutation", "error"),
    [
        (lambda packet, decision: decision.update(packet_digest="sha256:" + "0" * 64), "digest"),
        (lambda packet, decision: decision["decisions"].pop(), "omits"),
        (
            lambda packet, decision: decision["decisions"].append(
                deepcopy(decision["decisions"][0])
            ),
            "duplicate",
        ),
        (
            lambda packet, decision: decision["decisions"][0].update(
                asset_id="claude__skill__unknown"
            ),
            "unknown",
        ),
        (
            lambda packet, decision: decision.update(reviewer_type="automation"),
            "human_operator",
        ),
        (
            lambda packet, decision: decision.update(attestation="not reviewed"),
            "attestation",
        ),
    ],
)
def test_decision_validation_fails_closed(parsed_fixture, mutation, error):
    packet = build_candidate_packet(parsed_fixture)
    decision = _approved_decision(packet)
    mutation(packet, decision)

    with pytest.raises(BootstrapValidationError, match=error):
        validate_operator_decision(packet, decision)


def test_apply_uses_real_governance_schema_and_supports_derived_ids(
    root, parsed_fixture, tmp_path
):
    packet = build_candidate_packet(parsed_fixture)
    decision = _approved_decision(packet)
    index = tmp_path / "index.db"
    revisions = LegacySkillAssetRepository(parsed_fixture).list_revisions()
    _create_index(index, revisions)
    target = tmp_path / "authority" / "governance.db"

    result = apply_operator_decision(
        parsed_dir=parsed_fixture,
        index_db=index,
        migration_dir=root / "migrations" / "index",
        packet=packet,
        decision=decision,
        target_db=target,
        expected_count=5,
    )

    assert result["state"] == "published"
    assert result["verification"]["integrity_check"] == "ok"
    assert result["verification"]["doctor"]["state"] == "healthy"
    assert result["verification"]["doctor"]["exit_code"] == 0
    assert target.is_file()
    with sqlite3.connect(target) as connection:
        names = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM skills ORDER BY name"
            )
        }
        evidence = [
            json.loads(row[0])["decision_evidence"]
            for row in connection.execute(
                "SELECT details_json FROM audit_log WHERE event_type='approve'"
            )
        ]
    assert names == {item["asset_id"] for item in packet["candidates"]}
    assert sum(
        item["identity_strategy"] == "source_name_disambiguation"
        for item in packet["candidates"]
    ) == 3
    assert len(evidence) == 5
    assert all(item["packet_digest"] == packet["packet_digest"] for item in evidence)
    assert all(item["decision_digest"] == result["decision_digest"] for item in evidence)


def test_rejection_is_truthful_and_never_published(root, parsed_fixture, tmp_path):
    packet = build_candidate_packet(parsed_fixture)
    rejected = packet["candidates"][0]["asset_id"]
    decision = _approved_decision(packet, reject_asset_id=rejected)
    index = tmp_path / "index.db"
    _create_index(index, LegacySkillAssetRepository(parsed_fixture).list_revisions())
    target = tmp_path / "authority" / "governance.db"

    with pytest.raises(BootstrapApplyError, match="refusing to publish"):
        apply_operator_decision(
            parsed_dir=parsed_fixture,
            index_db=index,
            migration_dir=root / "migrations" / "index",
            packet=packet,
            decision=decision,
            target_db=target,
            expected_count=5,
        )

    assert not target.exists()
    assert list(target.parent.glob("*.staging")) == []


def test_apply_cli_honors_expected_count(root, parsed_fixture, tmp_path):
    packet = build_candidate_packet(parsed_fixture)
    decision = _approved_decision(packet)
    packet_path = tmp_path / "packet.json"
    decision_path = tmp_path / "decision.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")
    decision_path.write_text(json.dumps(decision), encoding="utf-8")
    index = tmp_path / "index.db"
    _create_index(index, LegacySkillAssetRepository(parsed_fixture).list_revisions())
    target = tmp_path / "authority" / "governance.db"
    report = tmp_path / "report.json"

    exit_code = main(
        [
            "apply",
            "--parsed-dir",
            str(parsed_fixture),
            "--expected-count",
            "5",
            "--index-db",
            str(index),
            "--migration-dir",
            str(root / "migrations" / "index"),
            "--packet",
            str(packet_path),
            "--decision",
            str(decision_path),
            "--target-db",
            str(target),
            "--report",
            str(report),
        ]
    )

    assert exit_code == 0
    assert target.is_file()
    assert json.loads(report.read_text(encoding="utf-8"))["state"] == "published"


def test_stale_packet_and_existing_target_reject_before_publication(
    root, parsed_fixture, tmp_path
):
    packet = build_candidate_packet(parsed_fixture)
    decision = _approved_decision(packet)
    index = tmp_path / "index.db"
    _create_index(index, LegacySkillAssetRepository(parsed_fixture).list_revisions())
    target = tmp_path / "governance.db"

    _write_skill(
        parsed_fixture / "new.json",
        skill_id="claude__skill__new",
        name="new",
    )
    with pytest.raises(BootstrapValidationError, match="snapshot changed"):
        apply_operator_decision(
            parsed_dir=parsed_fixture,
            index_db=index,
            migration_dir=root / "migrations" / "index",
            packet=packet,
            decision=decision,
            target_db=target,
            expected_count=6,
        )
    assert not target.exists()

    packet = build_candidate_packet(parsed_fixture)
    decision = _approved_decision(packet)
    target.write_bytes(b"operator-state")
    with pytest.raises(BootstrapApplyError, match="already exists"):
        apply_operator_decision(
            parsed_dir=parsed_fixture,
            index_db=index,
            migration_dir=root / "migrations" / "index",
            packet=packet,
            decision=decision,
            target_db=target,
            expected_count=6,
        )
    assert target.read_bytes() == b"operator-state"
