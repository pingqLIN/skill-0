from __future__ import annotations

import json
import sqlite3
from types import SimpleNamespace

import pytest

from tools.runtime_asset_search_benchmark import (
    FTS_PROFILES,
    LegacySkillAssetRepository,
    build_fts_database,
    evaluate_gates,
    fts_expression,
    load_query_suite,
    percentile_higher,
    ranking_metrics,
    reciprocal_rank_fusion,
    search_fts,
    select_profile_decision,
    sha256_file,
    validate_freeze_manifest,
    validate_index_projection,
    validate_output_dir,
)
import tools.runtime_asset_search_benchmark as benchmark_module


def test_ranking_metrics_are_binary_and_bounded():
    metrics = ranking_metrics(["other", "a", "b"], frozenset({"a", "b"}))
    assert metrics["mrr_at_5"] == 0.5
    assert metrics["recall_at_5"] == 1.0
    assert 0 < metrics["ndcg_at_5"] < 1


def test_rrf_is_deterministic_and_uses_asset_id_for_ties():
    assert reciprocal_rank_fusion(["b"], ["a"]) == ["a", "b"]
    assert reciprocal_rank_fusion(["a", "b"], ["b", "a"])[0] == "a"


def test_percentile_uses_higher_method():
    assert percentile_higher([1.0, 2.0, 3.0, 4.0], 0.95) == 4.0


def test_fts_expression_and_search_are_safe_for_punctuation():
    assert fts_expression("ASP.NET REST API") == '"ASP" OR "NET" OR "REST" OR "API"'
    with sqlite3.connect(":memory:") as connection:
        connection.execute(
            "CREATE VIRTUAL TABLE benchmark_asset_fts USING fts5(asset_id UNINDEXED, title, description, body)"
        )
        connection.execute(
            "INSERT INTO benchmark_asset_fts VALUES ('api', 'ASP NET REST API', '', '')"
        )
        assert search_fts(connection, "ASP.NET REST API", 5) == ["api"]


def test_all_registered_fts_profiles_build_and_search(tmp_path):
    revision = SimpleNamespace(
        asset_id="asset-1",
        payload={
            "meta": {"name": "fixture", "description": "searchable fixture"},
            "decomposition": {"actions": [], "rules": [], "directives": []},
        },
    )
    repository = SimpleNamespace(list_revisions=lambda: (revision,))
    assert [profile.name for profile in FTS_PROFILES] == [
        "baseline",
        "detail-none",
        "detail-none-columnsize-zero",
    ]
    for profile in FTS_PROFILES:
        path = tmp_path / f"{profile.name}.db"
        build_fts_database(path, repository, profile)
        with sqlite3.connect(path) as connection:
            assert search_fts(connection, "searchable fixture", 5) == ["asset-1"]


def test_profile_selection_uses_smallest_passing_artifact():
    profiles = {
        "baseline": {
            "storage": {"fts5_bytes": 300},
            "gate": {"decision": "GO_P1_PROTOTYPE"},
        },
        "detail-none": {
            "storage": {"fts5_bytes": 200},
            "gate": {"decision": "GO_P1_PROTOTYPE"},
        },
        "detail-none-columnsize-zero": {
            "storage": {"fts5_bytes": 100},
            "gate": {"decision": "NO_GO"},
        },
    }
    decision = select_profile_decision(profiles)
    assert decision["decision"] == "GO_P1_PROTOTYPE"
    assert decision["selected_profile"] == "detail-none"


def test_profile_selection_fails_closed_when_final_isolation_fails():
    profiles = {
        "baseline": {
            "storage": {"fts5_bytes": 300},
            "gate": {"decision": "GO_P1_PROTOTYPE"},
        }
    }
    decision = select_profile_decision(profiles, final_isolation=False)
    assert decision["decision"] == "NO_GO"
    assert decision["selected_profile"] is None
    assert decision["reason"] == "source_index_isolation_failed"


def test_frozen_v2_query_suite_resolves_and_meets_coverage(root):
    cases, document = load_query_suite(
        root / "benchmarks" / "runtime-asset-search-queries-v2.json",
        LegacySkillAssetRepository(root / "parsed"),
    )
    assert document["schema_version"] == "2.0.0"
    assert len(cases) == 84
    assert sum(case.subset == "lexical" for case in cases) == 42
    assert sum(case.subset == "semantic" for case in cases) == 42
    assert len(
        {
            judgment["asset_id"]
            for case in cases
            for judgment in case.judgments
            if judgment["grade"] == 2
        }
    ) >= 40
    freeze = json.loads(
        (root / "benchmarks" / "runtime-asset-search-v2-freeze.json").read_text(
            encoding="utf-8"
        )
    )
    assert freeze["suite_sha256"] == sha256_file(
        root / "benchmarks" / "runtime-asset-search-queries-v2.json"
    )
    assert freeze["measurement_state"] == "not_run_at_freeze"


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("suite_sha256", "sha256:tampered"),
        ("corpus_snapshot_id", "sha256:tampered"),
        ("fts5_profiles", {"baseline": ["content=missing"]}),
        ("measurement_state", "measured"),
    ],
)
def test_freeze_manifest_tampering_fails_closed(root, tmp_path, field, replacement):
    suite_path = root / "benchmarks" / "runtime-asset-search-queries-v2.json"
    repository = LegacySkillAssetRepository(root / "parsed")
    cases, _document = load_query_suite(suite_path, repository)
    manifest = json.loads(
        (root / "benchmarks" / "runtime-asset-search-v2-freeze.json").read_text(
            encoding="utf-8"
        )
    )
    manifest[field] = replacement
    tampered = tmp_path / "freeze.json"
    tampered.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match=f"freeze manifest mismatch:.*{field}"):
        validate_freeze_manifest(
            tampered,
            query_suite=suite_path,
            repository=repository,
            cases=cases,
        )


def test_decision_requires_every_predeclared_gate():
    metric = {"ndcg_at_5": 0.8, "mrr_at_5": 0.8, "recall_at_5": 0.8}
    quality = {
        "overall": {"vector": metric, "hybrid": metric},
        "lexical": {
            "vector": metric,
            "hybrid": {**metric, "ndcg_at_5": 0.85},
        },
        "semantic": {"vector": metric, "hybrid": metric},
    }
    latency = {
        "vector_ms": {"p95": 10.0},
        "hybrid_ms": {"p95": 14.0},
    }
    accepted = evaluate_gates(
        quality=quality,
        latency=latency,
        source_size=1000,
        fts_size=250,
        isolation=True,
        asset_count=196,
        index_rows=196,
        query_count=80,
        lexical_query_count=40,
        semantic_query_count=40,
    )
    assert accepted["decision"] == "GO_P1_PROTOTYPE"

    rejected = evaluate_gates(
        quality=quality,
        latency=latency,
        source_size=1000,
        fts_size=251,
        isolation=True,
        asset_count=196,
        index_rows=196,
        query_count=80,
        lexical_query_count=40,
        semantic_query_count=40,
    )
    assert rejected["decision"] == "NO_GO"
    assert rejected["checks"]["storage_ratio"] is False

    insufficient = evaluate_gates(
        quality=quality,
        latency=latency,
        source_size=1000,
        fts_size=250,
        isolation=True,
        asset_count=196,
        index_rows=196,
        query_count=18,
        lexical_query_count=9,
        semantic_query_count=9,
    )
    assert insufficient["decision"] == "NO_GO_INSUFFICIENT_EVIDENCE"
    assert insufficient["checks"]["representative_query_coverage"] is False

    unreviewed = evaluate_gates(
        quality=quality,
        latency=latency,
        source_size=1000,
        fts_size=250,
        isolation=True,
        asset_count=196,
        index_rows=196,
        query_count=80,
        lexical_query_count=40,
        semantic_query_count=40,
        reviewed_frozen_suite=False,
    )
    assert unreviewed["decision"] == "NO_GO_INSUFFICIENT_EVIDENCE"
    assert unreviewed["checks"]["reviewed_frozen_suite"] is False


def test_fts_expression_rejects_empty_input():
    with pytest.raises(ValueError, match="no searchable tokens"):
        fts_expression("---")


def test_equal_count_stale_index_projection_fails_closed(tmp_path):
    revision = SimpleNamespace(
        asset_id="asset-current",
        revision_id="revision-current",
        content_hash="sha256:current",
        source_path=tmp_path / "current.json",
    )
    with sqlite3.connect(":memory:") as connection:
        connection.execute(
            """
            CREATE TABLE asset_index_state (
                asset_id TEXT, revision_id TEXT, representation_version TEXT,
                content_hash TEXT, source_path TEXT,
                embedding_model_id TEXT, embedding_model_version TEXT
            )
            """
        )
        connection.execute(
            "INSERT INTO asset_index_state VALUES ('asset-stale', 'revision-current', 'skill-text-v1', 'sha256:current', ?, 'model', 'version')",
            (revision.source_path.as_posix(),),
        )
        with pytest.raises(RuntimeError, match="projection mismatch"):
            validate_index_projection(connection, (revision,))


def test_output_directory_rejects_authority_paths():
    with pytest.raises(ValueError, match="must be under"):
        validate_output_dir(benchmark_module.ROOT / "governance" / "db" / "run")


def test_preflight_failure_records_unchanged_isolation_evidence(tmp_path, monkeypatch):
    monkeypatch.setattr(benchmark_module, "ROOT", tmp_path)
    parsed = tmp_path / "parsed"
    parsed.mkdir()
    (parsed / "fixture.json").write_text(
        json.dumps(
            {
                "meta": {
                    "skill_id": "claude__skill__fixture",
                    "name": "fixture",
                    "description": "fixture",
                    "parsed_by": "test",
                    "parser_version": "1.0.0",
                },
                "decomposition": {"actions": [], "rules": [], "directives": []},
            }
        ),
        encoding="utf-8",
    )
    repository = benchmark_module.LegacySkillAssetRepository(parsed)
    queries = tmp_path / "queries.json"
    queries.write_text(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "snapshot_id": repository.snapshot_id,
                "queries": [
                    {
                        "id": "L01",
                        "subset": "lexical",
                        "query": "fixture",
                        "judgments": [
                            {"source_path": "fixture.json", "grade": 2}
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    source = tmp_path / "skills.db"
    with sqlite3.connect(source) as connection:
        connection.execute("CREATE TABLE sample(value TEXT)")
    output = tmp_path / ".artifacts" / "p1-search" / "failed-run"

    with pytest.raises(Exception, match="index_schema_missing"):
        benchmark_module.run_benchmark(
            source_index=source,
            parsed_dir=parsed,
            query_suite=queries,
            output_dir=output,
        )

    evidence = json.loads(
        (output / "isolation-evidence.json").read_text(encoding="utf-8")
    )
    assert evidence["unchanged"] is True
    assert evidence["before"] == evidence["after"]
    assert evidence["failure"]["type"] == "IndexSchemaError"
