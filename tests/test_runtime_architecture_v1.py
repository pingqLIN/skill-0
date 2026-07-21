import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = ROOT / "docs" / "contracts" / "runtime-architecture-v1.json"


def test_runtime_architecture_v1_freezes_stable_foundation_boundaries():
    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))

    assert baseline["architecture_version"] == "1.0.0"
    assert baseline["status"] == "stable-foundation"
    assert baseline["supported_asset_types"] == ["skill"]
    assert baseline["physical_stores"] == {
        "skills.db": "derived-index",
        "governance.db": "revision-and-approval-authority",
        "runtime.db": "append-only-runtime-ledger",
    }
    assert baseline["execution"] == {
        "mode": "dry-run-only",
        "real_adapter_execution_available": False,
        "certification_artifacts_are_authority": False,
        "future_non_dry_run_requires_new_architecture_baseline": True,
        "unknown_outcome": "reconciliation-required",
    }
    assert baseline["excluded"] == {
        "fts5": True,
        "dashboard_redesign": True,
        "new_asset_type": True,
        "physical_database_migration": True,
    }


def test_runtime_architecture_v1_keeps_authority_out_of_derived_planes():
    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))

    assert baseline["planes"] == {
        "asset": {
            "authority": "canonical-skill-payload-and-deterministic-envelope",
            "mutable": False,
        },
        "index": {"authority": "none-derived-projection", "mutable": True},
        "governance": {
            "authority": "current-approved-governance-revision-and-artifact-digest",
            "mutable": True,
        },
        "runtime": {
            "authority": "append-only-runtime-event-ledger",
            "mutable": True,
        },
        "evidence": {
            "authority": "none-derived-from-immutable-facts",
            "mutable": False,
        },
    }
    assert baseline["semantic_invariants"] == {
        "ard_categories": ["action", "rule", "directive"],
        "evidence_is_orthogonal": True,
        "index_is_authority": False,
        "benchmark_is_authority": False,
        "runtime_status_is_projection": True,
    }
