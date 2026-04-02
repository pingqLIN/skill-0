# Remaining Worktree Triage

Status note: historical triage snapshot. The follow-on slices described here were later executed and superseded by the `2026-04-02` triage record plus the landed commit series on branch `chore/executable-plan-20260331`.

Date: `2026-03-27`
Context: `after landing the 4 local P0 commits`
P0 branch anchor: `p0-closeout-2026-03-27`

## Current State

- Remaining worktree items after the P0 commit series: `273`
- Largest buckets:
  - `parsed/`: `195`
  - `skill-0-dashboard/`: `30`
  - `docs/`: `18`
  - `tests/`: `8`

## Best Handling

- Do not keep developing on top of the current dirty `main` worktree as a single stream.
- Split the remaining work into three follow-on branches plus one cleanup pass.
- Preserve the existing local P0 branch as the stable anchor.

## Branch A: Dashboard And Runtime Hardening

Recommended branch intent:
`dashboard-auth-runtime-hardening`

Include:
- `skill-0-dashboard/apps/api/**`
- `skill-0-dashboard/apps/web/**`
- `.github/workflows/ci.yml`
- `.env.production.example`
- `Dockerfile.api`
- `Dockerfile.dashboard`
- `Dockerfile.web`
- `docker-compose.yml`
- `docker-compose.prod.yml`
- `requirements.txt`
- `requirements-dev.txt`
- `requirements-api.txt`
- `.nvmrc`
- `.dockerignore`
- `tests/integration/test_auth_flow.py`
- `tests/integration/test_rate_limiting.py`
- `tests/__init__.py`
- `tests/conftest.py`
- `governance/GOVERNANCE.md`

Why:
- This is a coherent operational slice: dashboard auth/session flow, API/runtime configuration, CI/runtime alignment, deployment files, and the auth/rate-limiting tests that exercise that stack.
- It is large but internally consistent, and should not be mixed with parsed-corpus churn.

## Branch B: Parsed Corpus And Complex Parser Work

Recommended branch intent:
`parsed-corpus-and-complex-parser`

Include:
- `parsed/*.json`
- `scripts/auto_parse.py`
- `scripts/complex_skill_parser.py`
- `tools/normalize_parsed_skills.py`
- `tools/batch_equivalence_backfill.py`
- `tools/skill_governance.py`
- `tools/skill_tester.py`
- `tests/fixtures/valid_skill.json`
- `tests/fixtures/complex_skills/**`
- `tests/test_complex_skill_parser.py`
- `tests/test_embedder_contract.py`

Why:
- `parsed/` alone accounts for `195` modified files and is effectively generated/artifact-heavy churn.
- The remaining tools/tests in this bucket look like the parser/fidelity/complex-skill follow-on work that should be reviewed together.
- This branch will be noisy by design, so it should stay isolated from dashboard/runtime changes.

## Branch C: Review Bundle And Dossier Docs

Recommended branch intent:
`review-bundle-and-dossier`

Include:
- `docs/devils-advocate-review-conceptual-2026-03-27.md`
- `docs/devils-advocate-review-conceptual-2026-03-27.zh-TW.md`
- `docs/diagrams/**`
- `docs/dossier/**`
- `docs/external-review-report-2026-03-23.md`
- `docs/final-development-phase-plan-2026-03-23.md`
- `docs/final-phase-plan-review-2026-03-23.md`
- `docs/final-phase-plan-review-round2-2026-03-23.md`
- `docs/planning/current-execution-plan-2026-03-19.md`
- `docs/project-dossier-2026-03-23.md`
- `docs/project-improvement-plan-2026-03-27.zh-TW.md`
- `docs/project-review-2026-03-23.md`
- `docs/review-opinion-2026-03-23.md`
- `docs/schema-extension-design-complex-skills-2026-03-24.md`
- `docs/shared-documentation-model.md`
- `docs/shared/**`

Why:
- These are mostly untracked review/dossier/design artifacts.
- They are documentation-heavy and should be reviewed for authority, duplication, and audience as one package.
- Keeping them separate avoids burying operational/code changes under large doc imports.

## Cleanup / Do Not Commit Blindly

Review and usually drop from commit scope:
- `skills.db-shm`
- `skills.db-wal`
- `docs/p0-commit-boundaries-2026-03-27.md`

Why:
- `skills.db-shm` and `skills.db-wal` are runtime spill artifacts.
- `docs/p0-commit-boundaries-2026-03-27.md` was a process aid for splitting commits, not product/runtime deliverable content.

## Questionable Leftovers

Resolved placement after manual review:
- `tests/test_embedder_contract.py` -> include in `parsed-corpus-and-complex-parser`
- `skill-0-dashboard/apps/__init__.py` -> include in `dashboard-auth-runtime-hardening`
- `docs/devils-advocate-review-conceptual-2026-03-27.md`
- `docs/devils-advocate-review-conceptual-2026-03-27.zh-TW.md`
- `tests/__init__.py`

Why:
- `tests/test_embedder_contract.py` is a parser/embedder contract regression that belongs with parser and corpus normalization work.
- `skill-0-dashboard/apps/__init__.py` is a harmless support file for the dashboard package and should travel with the dashboard/runtime branch.
- The two `devils-advocate` review notes contain pre-P0 counts and need archival labeling or refresh before any merge.
- `tests/__init__.py` is only package-level wording cleanup and should not be treated as a standalone change.

## Recommended Order

1. Leave `p0-closeout-2026-03-27` untouched as the stable local anchor.
2. Triage and extract Branch A first, because it is the most user-facing and operationally consequential.
3. Handle Branch B second, because `parsed/` churn will dominate review volume.
4. Handle Branch C last, because doc bundles are easiest to review once code/runtime direction is already settled.
5. Remove cleanup/noise artifacts before pushing anything.

## Outcome Note (`2026-04-02`)

- Branch A intent landed as commit `99f56e5` `Harden dashboard auth and governance runtime`
- Branch B intent landed across commits `e2fc8c1` and `3534eb0`
- Branch C intent landed as commit `6d3ad5e` `Add review dossier and shared documentation bundle`
- Remaining spillover after extraction was reduced to `parsed/agent-skills-skill.json` plus process-only docs
