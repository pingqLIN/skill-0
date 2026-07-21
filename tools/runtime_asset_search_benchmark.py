#!/usr/bin/env python3
"""Offline FTS5/sqlite-vec benchmark with source-Index isolation evidence."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import platform
import re
import sqlite3
import statistics
import sys
import time
from typing import Callable, Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from asset_registry.repositories import LegacySkillAssetRepository
from asset_registry.sqlite import (
    backup_database,
    load_migrations,
    preflight_index_schema,
    preview_migrations,
)
from vector_db.embedder import SkillEmbedder
from vector_db.search import REPRESENTATION_VERSION, SemanticSearch


RRF_K = 60
CANDIDATE_LIMIT = 20
RESULT_LIMIT = 5
MEASURED_RUNS = 5
MINIMUM_QUERY_COUNT = 80
MINIMUM_SUBSET_QUERY_COUNT = 30
V2_QUERY_COUNT = 84
V2_SUBSET_QUERY_COUNT = 42
V2_MINIMUM_DIRECT_TARGETS = 40


@dataclass(frozen=True)
class FTSProfile:
    name: str
    options: tuple[str, ...]


FTS_PROFILES = (
    FTSProfile("baseline", ()),
    FTSProfile("detail-none", ("detail=none",)),
    FTSProfile("detail-none-columnsize-zero", ("detail=none", "columnsize=0")),
)


@dataclass(frozen=True)
class QueryCase:
    query_id: str
    subset: str
    query: str
    taxonomy: str
    relevant_asset_ids: frozenset[str]
    judgments: tuple[dict[str, object], ...]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def source_file_state(path: Path) -> dict[str, object]:
    stat = path.stat()
    return {
        "sha256": sha256_file(path),
        "bytes": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
    }


def source_state_unchanged(before: dict[str, object], after: dict[str, object]) -> bool:
    return before == after


def validate_output_dir(path: Path) -> Path:
    resolved = path.resolve()
    allowed_root = (ROOT / ".artifacts" / "p1-search").resolve()
    if allowed_root not in resolved.parents:
        raise ValueError("output directory must be under .artifacts/p1-search/<run-id>")
    if resolved.suffix.lower() in {".db", ".sqlite", ".sqlite3"}:
        raise ValueError("output directory must not use a database filename")
    return resolved


def percentile_higher(values: Iterable[float], percentile: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("percentile requires values")
    index = max(0, math.ceil(percentile * len(ordered)) - 1)
    return ordered[index]


def ranking_metrics(ranking: list[str], relevant: frozenset[str], *, k: int = 5):
    top = ranking[:k]
    hits = [1 if asset_id in relevant else 0 for asset_id in top]
    dcg = sum(hit / math.log2(rank + 1) for rank, hit in enumerate(hits, start=1))
    ideal_count = min(len(relevant), k)
    idcg = sum(1 / math.log2(rank + 1) for rank in range(1, ideal_count + 1))
    first = next((rank for rank, hit in enumerate(hits, start=1) if hit), None)
    return {
        "ndcg_at_5": dcg / idcg if idcg else 0.0,
        "mrr_at_5": 1.0 / first if first else 0.0,
        "recall_at_5": sum(hits) / len(relevant) if relevant else 0.0,
    }


def reciprocal_rank_fusion(
    vector_ids: list[str], fts_ids: list[str], *, k: int = RRF_K
) -> list[str]:
    scores: dict[str, float] = {}
    for ranking in (vector_ids, fts_ids):
        for rank, asset_id in enumerate(ranking, start=1):
            scores[asset_id] = scores.get(asset_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores, key=lambda asset_id: (-scores[asset_id], asset_id))


def fts_expression(query: str) -> str:
    tokens = re.findall(r"\w+", query, flags=re.UNICODE)
    if not tokens:
        raise ValueError("query contains no searchable tokens")
    return " OR ".join('"' + token.replace('"', '""') + '"' for token in tokens)


def _skill_text(payload: dict) -> str:
    formatter = object.__new__(SkillEmbedder)
    return formatter.skill_to_text(payload)


def validate_index_projection(connection: sqlite3.Connection, revisions):
    expected = {
        (
            revision.asset_id,
            revision.revision_id,
            REPRESENTATION_VERSION,
            revision.content_hash,
            revision.source_path.as_posix(),
        )
        for revision in revisions
    }
    rows = connection.execute(
        """
        SELECT asset_id, revision_id, representation_version,
               content_hash, source_path,
               embedding_model_id, embedding_model_version
        FROM asset_index_state
        """
    ).fetchall()
    actual = {
        (str(row[0]), str(row[1]), str(row[2]), str(row[3]), str(row[4]))
        for row in rows
    }
    if len(rows) != len(revisions) or actual != expected:
        missing = len(expected - actual)
        extra = len(actual - expected)
        raise RuntimeError(
            f"source Index projection mismatch: missing={missing},extra={extra}"
        )
    model_pairs = {(str(row[5]), str(row[6])) for row in rows}
    if len(model_pairs) != 1:
        raise RuntimeError("source Index has embedding model drift")
    return next(iter(model_pairs))


def preflight_source_index(path: Path, revisions):
    if path.name.lower() in {"governance.db", "runtime.db"}:
        raise ValueError("Governance and Runtime databases are not benchmark sources")
    migrations = load_migrations(ROOT / "migrations" / "index")
    with sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only=ON")
        integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
        if integrity != "ok":
            raise RuntimeError("source Index integrity failure")
        schema = preflight_index_schema(connection)
        migration_status = preview_migrations(connection, migrations)
        if not migrations or any(item.state != "applied" for item in migration_status):
            raise RuntimeError("source Index migration is not exact and applied")
        model_pair = validate_index_projection(connection, revisions)
    return {
        "integrity": integrity,
        "schema": schema,
        "index_rows": len(revisions),
        "migration_status": [
            {
                "migration_id": item.migration_id,
                "checksum": item.checksum,
                "state": item.state,
            }
            for item in migration_status
        ],
        "model_pair": model_pair,
    }


def load_query_suite(path: Path, repository: LegacySkillAssetRepository):
    document = json.loads(path.read_text(encoding="utf-8"))
    schema_version = document.get("schema_version")
    if schema_version not in {"1.0.0", "2.0.0"}:
        raise ValueError("unsupported query suite schema")
    if document.get("snapshot_id") != repository.snapshot_id:
        raise ValueError("query suite snapshot does not match parsed corpus")
    by_source = {
        revision.source_path.as_posix(): revision
        for revision in repository.list_revisions()
    }
    cases = []
    seen_ids = set()
    seen_queries = set()
    for item in document.get("queries", []):
        query_id = str(item["id"])
        if query_id in seen_ids:
            raise ValueError(f"duplicate query id: {query_id}")
        seen_ids.add(query_id)
        query = str(item["query"]).strip()
        normalized_query = " ".join(query.casefold().split())
        if not normalized_query or normalized_query in seen_queries:
            raise ValueError(f"empty or duplicate query wording: {query_id}")
        seen_queries.add(normalized_query)
        subset = str(item["subset"])
        if subset not in {"lexical", "semantic"}:
            raise ValueError(f"unsupported subset: {subset}")
        resolved = []
        judgments = []
        raw_judgments = item.get("judgments", [])
        if schema_version == "2.0.0" and not 1 <= len(raw_judgments) <= 3:
            raise ValueError(f"v2 query requires 1-3 judgments: {query_id}")
        for judgment in raw_judgments:
            source_path = str(judgment["source_path"])
            grade = int(judgment["grade"])
            if source_path not in by_source or grade not in {1, 2}:
                raise ValueError(f"invalid judgment: {query_id}:{source_path}")
            asset_id = by_source[source_path].asset_id
            resolved.append(asset_id)
            judgments.append(
                {"source_path": source_path, "asset_id": asset_id, "grade": grade}
            )
        if not resolved:
            raise ValueError(f"query has no relevant judgments: {query_id}")
        cases.append(
            QueryCase(
                query_id=query_id,
                subset=subset,
                query=query,
                taxonomy=str(item.get("taxonomy") or "unclassified"),
                relevant_asset_ids=frozenset(resolved),
                judgments=tuple(judgments),
            )
        )
    if not cases:
        raise ValueError("query suite is empty")
    if schema_version == "2.0.0":
        freeze = document.get("freeze", {})
        if (
            freeze.get("state") != "reviewed_frozen"
            or not str(freeze.get("reviewer", "")).startswith("agent:")
        ):
            raise ValueError("v2 suite must pass independent review before measurement")
        lexical_count = sum(case.subset == "lexical" for case in cases)
        semantic_count = sum(case.subset == "semantic" for case in cases)
        direct_targets = {
            str(judgment["asset_id"])
            for case in cases
            for judgment in case.judgments
            if judgment["grade"] == 2
        }
        taxonomies = {case.taxonomy for case in cases}
        if len(cases) != V2_QUERY_COUNT:
            raise ValueError(f"v2 suite requires exactly {V2_QUERY_COUNT} queries")
        if (lexical_count, semantic_count) != (
            V2_SUBSET_QUERY_COUNT,
            V2_SUBSET_QUERY_COUNT,
        ):
            raise ValueError("v2 suite requires exactly 42 lexical and 42 semantic queries")
        if len(direct_targets) < V2_MINIMUM_DIRECT_TARGETS:
            raise ValueError("v2 suite has insufficient distinct direct targets")
        if "unclassified" in taxonomies or len(taxonomies) < 6:
            raise ValueError("v2 suite requires classified taxonomy coverage")
    return tuple(cases), document


def validate_freeze_manifest(
    path: Path,
    *,
    query_suite: Path,
    repository: LegacySkillAssetRepository,
    cases: tuple[QueryCase, ...],
):
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != "1.0.0":
        raise ValueError("unsupported freeze manifest schema")
    try:
        relative_suite = query_suite.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError("v2 query suite must be inside the repository") from exc
    expected_profiles = {
        profile.name: list(profile.options) for profile in FTS_PROFILES
    }
    taxonomy_counts = {
        taxonomy: sum(case.taxonomy == taxonomy for case in cases)
        for taxonomy in sorted({case.taxonomy for case in cases})
    }
    direct_target_count = len(
        {
            judgment["asset_id"]
            for case in cases
            for judgment in case.judgments
            if judgment["grade"] == 2
        }
    )
    expected = {
        "suite": relative_suite,
        "suite_sha256": sha256_file(query_suite),
        "corpus_snapshot_id": repository.snapshot_id,
        "query_count": len(cases),
        "lexical_query_count": sum(case.subset == "lexical" for case in cases),
        "semantic_query_count": sum(case.subset == "semantic" for case in cases),
        "qrel_count": sum(len(case.judgments) for case in cases),
        "distinct_direct_target_count": direct_target_count,
        "taxonomy_counts": taxonomy_counts,
        "fts5_profiles": expected_profiles,
        "review_state": "passed_before_measurement",
        "measurement_state": "not_run_at_freeze",
    }
    mismatches = [key for key, value in expected.items() if manifest.get(key) != value]
    if mismatches:
        raise ValueError("freeze manifest mismatch: " + ",".join(sorted(mismatches)))
    return {
        "path": str(path.resolve()),
        "sha256": sha256_file(path),
        **expected,
        "curator": manifest.get("curator"),
        "reviewer": manifest.get("reviewer"),
        "reviewed_on": manifest.get("reviewed_on"),
    }


def build_fts_database(
    path: Path,
    repository: LegacySkillAssetRepository,
    profile: FTSProfile = FTS_PROFILES[0],
) -> float:
    start = time.perf_counter()
    with sqlite3.connect(path) as connection:
        profile_options = ""
        if profile.options:
            profile_options = ",\n                " + ",\n                ".join(profile.options)
        connection.execute(
            f"""
            CREATE VIRTUAL TABLE benchmark_asset_fts USING fts5(
                asset_id UNINDEXED,
                title,
                description,
                body,
                tokenize='unicode61 remove_diacritics 2'{profile_options}
            )
            """
        )
        rows = []
        for revision in repository.list_revisions():
            meta = revision.payload.get("meta", {})
            rows.append(
                (
                    revision.asset_id,
                    str(meta.get("title") or meta.get("name") or ""),
                    str(meta.get("description") or ""),
                    _skill_text(revision.payload),
                )
            )
        connection.executemany(
            "INSERT INTO benchmark_asset_fts(asset_id, title, description, body) VALUES (?, ?, ?, ?)",
            rows,
        )
        connection.execute("INSERT INTO benchmark_asset_fts(benchmark_asset_fts) VALUES('optimize')")
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise RuntimeError(f"FTS database integrity failure: {integrity}")
    return (time.perf_counter() - start) * 1000


def search_fts(connection: sqlite3.Connection, query: str, limit: int) -> list[str]:
    expression = fts_expression(query)
    rows = connection.execute(
        """
        SELECT asset_id
        FROM benchmark_asset_fts
        WHERE benchmark_asset_fts MATCH ?
        ORDER BY bm25(benchmark_asset_fts, 0.0, 8.0, 4.0, 1.0), asset_id
        LIMIT ?
        """,
        (expression, limit),
    ).fetchall()
    return [str(row[0]) for row in rows]


def _measure(function: Callable[[], list[str]]):
    function()
    rankings = []
    latencies = []
    for _ in range(MEASURED_RUNS):
        start = time.perf_counter_ns()
        ranking = function()
        latencies.append((time.perf_counter_ns() - start) / 1_000_000)
        rankings.append(ranking)
    if any(ranking != rankings[0] for ranking in rankings[1:]):
        raise RuntimeError("non-deterministic benchmark ranking")
    return rankings[0], latencies


def _aggregate_quality(query_results, method: str, subset: str | None = None):
    selected = [
        item
        for item in query_results
        if subset is None or item["subset"] == subset
    ]
    keys = ("ndcg_at_5", "mrr_at_5", "recall_at_5")
    return {
        key: statistics.fmean(item["metrics"][method][key] for item in selected)
        for key in keys
    }


def evaluate_gates(
    *,
    quality,
    latency,
    source_size: int,
    fts_size: int,
    isolation,
    asset_count: int,
    index_rows: int,
    query_count: int,
    lexical_query_count: int,
    semantic_query_count: int,
    reviewed_frozen_suite: bool = True,
):
    epsilon = 1e-12
    vector = quality["overall"]["vector"]
    hybrid = quality["overall"]["hybrid"]
    vector_lexical = quality["lexical"]["vector"]
    hybrid_lexical = quality["lexical"]["hybrid"]
    vector_semantic = quality["semantic"]["vector"]
    hybrid_semantic = quality["semantic"]["hybrid"]
    vector_p95 = latency["vector_ms"]["p95"]
    hybrid_p95 = latency["hybrid_ms"]["p95"]
    checks = {
        "complete_corpus": asset_count == index_rows == 196,
        "representative_query_coverage": (
            query_count >= MINIMUM_QUERY_COUNT
            and lexical_query_count >= MINIMUM_SUBSET_QUERY_COUNT
            and semantic_query_count >= MINIMUM_SUBSET_QUERY_COUNT
        ),
        "overall_ndcg_floor": hybrid["ndcg_at_5"] - vector["ndcg_at_5"] >= -0.01 - epsilon,
        "lexical_ndcg_gain": hybrid_lexical["ndcg_at_5"] - vector_lexical["ndcg_at_5"] >= 0.05 - epsilon,
        "semantic_ndcg_floor": hybrid_semantic["ndcg_at_5"] - vector_semantic["ndcg_at_5"] >= -0.02 - epsilon,
        "overall_recall_floor": hybrid["recall_at_5"] - vector["recall_at_5"] >= -0.02 - epsilon,
        "latency_absolute": hybrid_p95 - vector_p95 <= 25.0,
        "latency_ratio": hybrid_p95 <= vector_p95 * 1.5,
        "storage_ratio": fts_size <= source_size * 0.25,
        "source_index_unchanged": bool(isolation),
        "reviewed_frozen_suite": reviewed_frozen_suite,
    }
    if not checks["representative_query_coverage"] or not reviewed_frozen_suite:
        decision = "NO_GO_INSUFFICIENT_EVIDENCE"
    else:
        decision = "GO_P1_PROTOTYPE" if all(checks.values()) else "NO_GO"
    return {
        "decision": decision,
        "checks": checks,
    }


def select_profile_decision(
    profiles: dict[str, dict[str, object]], *, final_isolation: bool = True
):
    if not final_isolation:
        return {
            "decision": "NO_GO",
            "selected_profile": None,
            "profile_decisions": {
                name: profile["gate"]["decision"]
                for name, profile in profiles.items()
            },
            "final_source_isolation": False,
            "reason": "source_index_isolation_failed",
        }
    passing = [
        (name, profile)
        for name, profile in profiles.items()
        if profile["gate"]["decision"] == "GO_P1_PROTOTYPE"
    ]
    if passing:
        selected_name, _selected = min(
            passing,
            key=lambda item: (int(item[1]["storage"]["fts5_bytes"]), item[0]),
        )
        decision = "GO_P1_PROTOTYPE"
    else:
        selected_name = None
        decisions = {profile["gate"]["decision"] for profile in profiles.values()}
        decision = (
            "NO_GO_INSUFFICIENT_EVIDENCE"
            if decisions == {"NO_GO_INSUFFICIENT_EVIDENCE"}
            else "NO_GO"
        )
    return {
        "decision": decision,
        "selected_profile": selected_name,
        "profile_decisions": {
            name: profile["gate"]["decision"] for name, profile in profiles.items()
        },
        "final_source_isolation": True,
    }


def run_benchmark(
    *,
    source_index: Path,
    parsed_dir: Path,
    query_suite: Path,
    output_dir: Path,
    freeze_manifest: Path | None = None,
):
    source_index = source_index.resolve()
    parsed_dir = parsed_dir.resolve()
    query_suite = query_suite.resolve()
    output_dir = validate_output_dir(output_dir)
    if not source_index.is_file():
        raise FileNotFoundError(source_index)
    if output_dir.exists():
        raise FileExistsError(output_dir)
    if source_index == output_dir or output_dir in source_index.parents:
        raise ValueError("benchmark output must not contain the source Index")
    source_before = source_file_state(source_index)
    output_dir.mkdir(parents=True)
    vector_copy = output_dir / "vector-snapshot.db"
    failure: dict[str, str] | None = None
    try:
        repository = LegacySkillAssetRepository(parsed_dir)
        revisions = repository.list_revisions()
        cases, suite_document = load_query_suite(query_suite, repository)
        freeze_evidence = None
        if suite_document["schema_version"] == "2.0.0":
            manifest_path = (
                freeze_manifest
                if freeze_manifest is not None
                else ROOT / "benchmarks" / "runtime-asset-search-v2-freeze.json"
            )
            freeze_evidence = validate_freeze_manifest(
                manifest_path.resolve(),
                query_suite=query_suite,
                repository=repository,
                cases=cases,
            )
        source_preflight = preflight_source_index(source_index, revisions)
        backup_integrity = backup_database(source_index, vector_copy)
        vector_snapshot_sha256 = sha256_file(vector_copy)
        profile_paths = {
            profile.name: output_dir / f"fts5-{profile.name}.db"
            for profile in FTS_PROFILES
        }
        profile_build_ms = {
            profile.name: build_fts_database(
                profile_paths[profile.name], repository, profile
            )
            for profile in FTS_PROFILES
        }
        engine = SemanticSearch(db_path=vector_copy, initialize_schema=False)
        try:
            model_id, model_version = engine._embedding_identity()
            if (model_id, model_version) != tuple(source_preflight["model_pair"]):
                raise RuntimeError("query model identity does not match indexed vectors")
            profiles = {}
            lexical_count = sum(case.subset == "lexical" for case in cases)
            semantic_count = sum(case.subset == "semantic" for case in cases)
            for profile in FTS_PROFILES:
                query_results = []
                timing = {"vector_ms": [], "fts5_ms": [], "hybrid_ms": []}
                with sqlite3.connect(profile_paths[profile.name]) as fts_connection:
                    fts_connection.execute("PRAGMA query_only=ON")
                    for case in cases:
                        vector_function = lambda case=case: [
                            result.asset_id
                            for result in engine.search_assets(
                                case.query, limit=CANDIDATE_LIMIT
                            )
                        ]
                        fts_function = lambda case=case: search_fts(
                            fts_connection, case.query, CANDIDATE_LIMIT
                        )
                        hybrid_function = lambda: reciprocal_rank_fusion(
                            vector_function(), fts_function()
                        )
                        vector_ids, vector_times = _measure(vector_function)
                        fts_ids, fts_times = _measure(fts_function)
                        hybrid_ids, hybrid_times = _measure(hybrid_function)
                        timing["vector_ms"].extend(vector_times)
                        timing["fts5_ms"].extend(fts_times)
                        timing["hybrid_ms"].extend(hybrid_times)
                        rankings = {
                            "vector": vector_ids,
                            "fts5": fts_ids,
                            "hybrid": hybrid_ids,
                        }
                        query_results.append(
                            {
                                "id": case.query_id,
                                "subset": case.subset,
                                "taxonomy": case.taxonomy,
                                "query": case.query,
                                "judgments": list(case.judgments),
                                "rankings_at_5": {
                                    method: values[:RESULT_LIMIT]
                                    for method, values in rankings.items()
                                },
                                "metrics": {
                                    method: ranking_metrics(
                                        values,
                                        case.relevant_asset_ids,
                                        k=RESULT_LIMIT,
                                    )
                                    for method, values in rankings.items()
                                },
                            }
                        )

                quality = {
                    subset: {
                        method: _aggregate_quality(
                            query_results,
                            method,
                            None if subset == "overall" else subset,
                        )
                        for method in ("vector", "fts5", "hybrid")
                    }
                    for subset in ("overall", "lexical", "semantic")
                }
                latency = {
                    method: {
                        "samples": len(values),
                        "p50": percentile_higher(values, 0.50),
                        "p95": percentile_higher(values, 0.95),
                        "max": max(values),
                    }
                    for method, values in timing.items()
                }
                profile_path = profile_paths[profile.name]
                profile_isolation = source_state_unchanged(
                    source_before, source_file_state(source_index)
                )
                profiles[profile.name] = {
                    "configuration": {
                        "fts5_options": list(profile.options),
                        "fts5_weights": [0.0, 8.0, 4.0, 1.0],
                    },
                    "storage": {
                        "fts5_bytes": profile_path.stat().st_size,
                        "fts5_to_source_ratio": (
                            profile_path.stat().st_size / int(source_before["bytes"])
                        ),
                        "fts5_build_ms": profile_build_ms[profile.name],
                        "mapping_storage": "embedded_in_fts_database_and_included",
                    },
                    "quality": quality,
                    "latency": latency,
                    "queries": query_results,
                    "gate": evaluate_gates(
                        quality=quality,
                        latency=latency,
                        source_size=int(source_before["bytes"]),
                        fts_size=profile_path.stat().st_size,
                        isolation=profile_isolation,
                        asset_count=len(revisions),
                        index_rows=int(source_preflight["index_rows"]),
                        query_count=len(cases),
                        lexical_query_count=lexical_count,
                        semantic_query_count=semantic_count,
                        reviewed_frozen_suite=freeze_evidence is not None,
                    ),
                }
        finally:
            engine.close()

        source_after = source_file_state(source_index)
        isolation = source_state_unchanged(source_before, source_after)
        decision = select_profile_decision(profiles, final_isolation=isolation)
        taxonomy_counts = {
            taxonomy: sum(case.taxonomy == taxonomy for case in cases)
            for taxonomy in sorted({case.taxonomy for case in cases})
        }
        qrel_count = sum(len(case.judgments) for case in cases)
        direct_target_count = len(
            {
                judgment["asset_id"]
                for case in cases
                for judgment in case.judgments
                if judgment["grade"] == 2
            }
        )
        report = {
            "schema_version": "2.0.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "configuration": {
                "rrf_k": RRF_K,
                "candidate_limit": CANDIDATE_LIMIT,
                "result_limit": RESULT_LIMIT,
                "measured_runs": MEASURED_RUNS,
                "minimum_query_count": MINIMUM_QUERY_COUNT,
                "minimum_subset_query_count": MINIMUM_SUBSET_QUERY_COUNT,
                "fts5_profiles": {
                    profile.name: list(profile.options) for profile in FTS_PROFILES
                },
            },
            "environment": {
                "platform": platform.platform(),
                "python": platform.python_version(),
                "sqlite": sqlite3.sqlite_version,
                "embedding_model_id": model_id,
                "embedding_model_version": model_version,
            },
            "corpus": {
                "snapshot_id": repository.snapshot_id,
                "asset_count": len(revisions),
                "index_rows": source_preflight["index_rows"],
                "query_count": len(cases),
                "lexical_query_count": lexical_count,
                "semantic_query_count": semantic_count,
                "qrel_count": qrel_count,
                "direct_target_count": direct_target_count,
                "taxonomy_counts": taxonomy_counts,
                "query_suite_sha256": sha256_file(query_suite),
                "suite_schema_version": suite_document["schema_version"],
                "freeze_manifest": freeze_evidence,
            },
            "source_index": {
                "path": str(source_index),
                "before": source_before,
                "after": source_after,
                "integrity": source_preflight["integrity"],
                "schema": source_preflight["schema"],
                "migration_status": source_preflight["migration_status"],
                "indexed_model_pair": source_preflight["model_pair"],
                "unchanged": isolation,
            },
            "storage": {
                "backup_integrity": backup_integrity,
                "vector_snapshot_sha256": vector_snapshot_sha256,
                "vector_snapshot_bytes": vector_copy.stat().st_size,
                "profiles": {
                    name: profile["storage"] for name, profile in profiles.items()
                },
            },
            "profiles": profiles,
            "gate": decision,
            "scope": "offline_evidence_only_no_production_ddl",
        }
        evidence_path = output_dir / "benchmark-result.json"
        evidence_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        return report, evidence_path
    except Exception as exc:
        failure = {"type": type(exc).__name__, "message": str(exc)}
        raise
    finally:
        try:
            final_state: dict[str, object] = source_file_state(source_index)
        except OSError as exc:
            final_state = {"error": type(exc).__name__}
        isolation_evidence = {
            "schema_version": "1.0.0",
            "source_index": str(source_index),
            "before": source_before,
            "after": final_state,
            "unchanged": source_state_unchanged(source_before, final_state),
            "failure": failure,
        }
        (output_dir / "isolation-evidence.json").write_text(
            json.dumps(isolation_evidence, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-index", type=Path, default=Path("skills.db"))
    parser.add_argument("--parsed-dir", type=Path, default=Path("parsed"))
    parser.add_argument(
        "--queries",
        type=Path,
        default=Path("benchmarks/runtime-asset-search-queries-v2.json"),
    )
    parser.add_argument(
        "--freeze-manifest",
        type=Path,
        default=Path("benchmarks/runtime-asset-search-v2-freeze.json"),
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    report, evidence_path = run_benchmark(
        source_index=args.source_index,
        parsed_dir=args.parsed_dir,
        query_suite=args.queries,
        output_dir=args.output_dir,
        freeze_manifest=args.freeze_manifest,
    )
    print(
        json.dumps(
            {
                "decision": report["gate"]["decision"],
                "evidence": str(evidence_path),
                "source_index_unchanged": report["source_index"]["unchanged"],
                "asset_count": report["corpus"]["asset_count"],
                "query_count": report["corpus"]["query_count"],
            },
            ensure_ascii=False,
        )
    )
    return {
        "GO_P1_PROTOTYPE": 0,
        "NO_GO": 4,
        "NO_GO_INSUFFICIENT_EVIDENCE": 5,
    }[report["gate"]["decision"]]


if __name__ == "__main__":
    raise SystemExit(main())
