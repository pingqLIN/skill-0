# ARDE v4 Phase 0 Local Landing Report

Updated: 2026-07-13

## Scope

This report records the first local landing pass for the SKILL-0 ARDE Codex
Execution Package v4.0.

The landing intentionally stops at the first v4.0 gate:

- repository audit
- runtime schema scaffold
- ARD cross-reference validator
- append-only runtime ledger
- fail-closed dry-run executor
- recovery coordinator test surface

MCP, OpenAI Agents SDK, LangGraph, OPA, production sandbox, public push, and
deployment were not started in this phase.

## Source Package

- Package path: `E:\miles\Downloads\SKILL-0_ARDE_Codex_Execution_Package_v4.0`
- Package verifier: `tools\verify_package.py`
- Verification command:
  `Q:\Projects\skill-0\.venv\Scripts\python.exe tools\verify_package.py`
- Verification result: `46 passed`

The package verifier was run with Git for Windows Bash first in `PATH` so the
package shell syntax check used the Windows-local Bash path instead of the WSL
shim.

## Repository Baseline

- Repository: `Q:\Projects\skill-0`
- Branch at landing: `codex/skill0-arde-v4-runtime`
- Baseline HEAD: `a3124ef3e884970b4a5e0f5b1bf731963775d652`
- Phase 0 audit output: `audit\v4-phase0`
- Audit summary:
  - dirty worktree: `true`
  - tracked/untracked files scanned: `689`
  - schema files inventoried: `1`
  - API routes inventoried: `50`
  - merge-conflict markers: `0`
  - overlay collisions: `2`
  - audit blockers: `0`

The worktree already contained unrelated uncommitted changes before the v4
landing. Those changes were preserved and are outside this phase's commit
boundary.

## Overlay Result

The overlay was applied through the package's collision-safe apply tool with
`--allow-dirty` because the current repository already had unrelated product
changes. The tool only copied non-conflicting new paths and did not overwrite
existing files.

Copied new paths:

- `.agents/skills/skill0-arde-runtime/`
- `.github/workflows/arde-runtime-v4.yml`
- `adapters/README.md`
- `api/routers/runs_v4.py`
- `docs/ADR-0004-ard-plus-evidence.md`
- `docs/ADR-0005-event-ledger.md`
- `docs/ADR-0006-runtime-boundary.md`
- `docs/migration-v2.4-to-v4.md`
- `docs/runtime-state-machine.md`
- `examples/runtime-contract.*.json`
- `examples/runtime-event.valid.json`
- `examples/evidence-summary.valid.json`
- `examples/prompt-manifest.valid.json`
- `migrations/001_runtime_ledger.sql`
- `policies/examples/skill0_runtime.rego`
- `runtime/`
- `schema/*runtime*.schema.json`
- `schema/evidence-summary.schema.json`
- `schema/prompt-manifest.schema.json`
- `scripts/validate_runtime_contract.py`
- `tests/test_runtime_*.py`
- `tests/test_v4_schema.py`
- `tests/test_evidence_projection.py`

Collisions reconciled manually:

- `.gitignore`: added runtime SQLite journal, runtime JSONL, and audit-output
  ignores while preserving existing local changes.
- `tests/conftest.py`: preserved existing API test environment setup and added
  shared `root` / `read_json` fixtures needed by v4 schema and evidence tests.

## Local Compatibility Fix

`scripts/validate_runtime_contract.py` now inserts the repository root into
`sys.path` before importing `runtime.validators`, so the script works when run
directly from the repository root on Windows.

## Verification

Focused v4 regression:

```text
python -m pytest tests\test_v4_schema.py tests\test_runtime_ledger.py tests\test_runtime_executor.py tests\test_runtime_policy.py tests\test_runtime_recovery.py tests\test_evidence_projection.py -q
43 passed
```

Runtime contract CLI:

```text
python scripts\validate_runtime_contract.py examples\runtime-contract.read-only.json
python scripts\validate_runtime_contract.py examples\runtime-contract.auto-rollback.json
python scripts\validate_runtime_contract.py examples\runtime-contract.manual-approval.json
All returned VALID.
```

Full Python regression:

```text
python -m pytest tests skill-0-dashboard\apps\api\tests -q
290 passed, 65 warnings
```

## Deferred Work

Next implementation batch should wire `api/routers/runs_v4.py` into the core
API with repository-local conventions for:

- authentication dependency
- runtime database path configuration
- rate limiting and middleware behavior
- router mount
- API tests

Adapters and production sandbox remain disabled until the runtime API gate is
implemented and reviewed.
