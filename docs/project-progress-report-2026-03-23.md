# Skill-0 Project Progress Report

Updated: `2026-03-23`

Status note:
- This file is a dated snapshot from `2026-03-23`, not the current authoritative status document.
- Some items listed here as in progress or incomplete were later closed or re-scoped by subsequent review and improvement work.
- For the current phase baseline, use [final-development-phase-plan-2026-03-23.md](/home/miles/dev2/skill-0/docs/final-development-phase-plan-2026-03-23.md), [project-review-2026-03-23.md](/home/miles/dev2/skill-0/docs/project-review-2026-03-23.md), and [project-improvement-plan-2026-03-27.zh-TW.md](/home/miles/dev2/skill-0/docs/project-improvement-plan-2026-03-27.zh-TW.md).

Superseded-conclusions note:
- The assessment and priorities below should be read as the team view on `2026-03-23`.
- They are useful for audit/history, but they are not the live delivery checklist.

## Main Functional Areas

### 1. Core Search API

Provides semantic search, similar-skill lookup, clustering, stats, skill listing, re-indexing, JWT auth, health checks, and Prometheus metrics.

- Main entry: [api/main.py](/home/miles/dev2/skill-0/api/main.py)
- Key functions:
  - `/api/search`
  - `/api/similar`
  - `/api/cluster`
  - `/api/stats`
  - `/api/skills`
  - `/api/index`
  - `/api/auth/token`
  - `/health`
  - `/metrics`

### 2. Vector Search and Indexing Layer

Handles embedding generation, SQLite-vec storage, similarity search, clustering, and CLI operations.

- Main files:
  - [vector_db/search.py](/home/miles/dev2/skill-0/vector_db/search.py)
  - [vector_db/vector_store.py](/home/miles/dev2/skill-0/vector_db/vector_store.py)
  - [vector_db/embedder.py](/home/miles/dev2/skill-0/vector_db/embedder.py)

### 3. Governance Database and Workflow

Tracks skill metadata, security scans, equivalence tests, approval workflow, and audit history.

- Main files:
  - [tools/governance_db.py](/home/miles/dev2/skill-0/tools/governance_db.py)
  - [tools/skill_governance.py](/home/miles/dev2/skill-0/tools/skill_governance.py)
  - [governance/GOVERNANCE.md](/home/miles/dev2/skill-0/governance/GOVERNANCE.md)

### 4. Governance Dashboard API

Wraps governance capabilities into JWT-protected REST endpoints for stats, skills, reviews, scans, and audit log.

- Main files:
  - [skill-0-dashboard/apps/api/main.py](/home/miles/dev2/skill-0/skill-0-dashboard/apps/api/main.py)
  - [skill-0-dashboard/apps/api/services/governance.py](/home/miles/dev2/skill-0/skill-0-dashboard/apps/api/services/governance.py)
  - [skill-0-dashboard/apps/api/routers/stats.py](/home/miles/dev2/skill-0/skill-0-dashboard/apps/api/routers/stats.py)
  - [skill-0-dashboard/apps/api/routers/skills.py](/home/miles/dev2/skill-0/skill-0-dashboard/apps/api/routers/skills.py)
  - [skill-0-dashboard/apps/api/routers/reviews.py](/home/miles/dev2/skill-0/skill-0-dashboard/apps/api/routers/reviews.py)
  - [skill-0-dashboard/apps/api/routers/scans.py](/home/miles/dev2/skill-0/skill-0-dashboard/apps/api/routers/scans.py)
  - [skill-0-dashboard/apps/api/routers/audit.py](/home/miles/dev2/skill-0/skill-0-dashboard/apps/api/routers/audit.py)

### 5. Governance Dashboard Web

React/Vite frontend for dashboard overview, skills list, review queue, security, audit log, and skill detail views.

- Main files:
  - [skill-0-dashboard/apps/web/src/App.tsx](/home/miles/dev2/skill-0/skill-0-dashboard/apps/web/src/App.tsx)
  - [skill-0-dashboard/apps/web/src/pages/Dashboard.tsx](/home/miles/dev2/skill-0/skill-0-dashboard/apps/web/src/pages/Dashboard.tsx)
  - [skill-0-dashboard/apps/web/src/pages/SkillsList.tsx](/home/miles/dev2/skill-0/skill-0-dashboard/apps/web/src/pages/SkillsList.tsx)
  - [skill-0-dashboard/apps/web/src/pages/SkillDetail.tsx](/home/miles/dev2/skill-0/skill-0-dashboard/apps/web/src/pages/SkillDetail.tsx)
  - [skill-0-dashboard/apps/web/src/pages/ReviewQueue.tsx](/home/miles/dev2/skill-0/skill-0-dashboard/apps/web/src/pages/ReviewQueue.tsx)
  - [skill-0-dashboard/apps/web/src/pages/Security.tsx](/home/miles/dev2/skill-0/skill-0-dashboard/apps/web/src/pages/Security.tsx)
  - [skill-0-dashboard/apps/web/src/pages/AuditLog.tsx](/home/miles/dev2/skill-0/skill-0-dashboard/apps/web/src/pages/AuditLog.tsx)

### 6. Parsed Data and Schema

`parsed/` contains decomposed skill examples, and `schema/` defines the Skill-0 JSON schema used for validation and indexing.

- Main files:
  - [schema/skill-decomposition.schema.json](/home/miles/dev2/skill-0/schema/skill-decomposition.schema.json)
  - [parsed](/home/miles/dev2/skill-0/parsed)

### 7. Tooling and Maintenance Scripts

Provides batch import, conversion, scanning, testing, DB maintenance, and operations scripts.

- Main directories:
  - [tools](/home/miles/dev2/skill-0/tools)
  - [scripts](/home/miles/dev2/skill-0/scripts)

### 8. Testing and CI/CD

Includes Python regression tests, dashboard API tests, frontend tests, build guardrails, and Docker build workflow.

- Main files:
  - [.github/workflows/ci.yml](/home/miles/dev2/skill-0/.github/workflows/ci.yml)
  - [tests](/home/miles/dev2/skill-0/tests)
  - [skill-0-dashboard/apps/api/tests](/home/miles/dev2/skill-0/skill-0-dashboard/apps/api/tests)
  - [skill-0-dashboard/apps/web/src/App.test.tsx](/home/miles/dev2/skill-0/skill-0-dashboard/apps/web/src/App.test.tsx)

## Progress Report

Snapshot interpretation note:
- The table below preserves the `2026-03-23` assessment.
- Specific statements about frontend JWT/session integration, frontend test instability, and local Python verification should be read as dated observations rather than current repo truth.

| Completed | In Progress | Not Completed |
|---|---|---|
| Core API and search endpoints are implemented, including search, similar lookup, cluster analysis, stats, skill listing, indexing, auth, health, and metrics. Files: [api/main.py](/home/miles/dev2/skill-0/api/main.py). Risk: runtime still depends on local `skills.db`, sqlite-vec, and embedding model availability. | Dashboard API scan/test actions are implemented and wired to real service methods instead of placeholder responses. Files: [skill-0-dashboard/apps/api/services/governance.py#L400](/home/miles/dev2/skill-0/skill-0-dashboard/apps/api/services/governance.py#L400). Risk: success depends on `source_path` and `installed_path` existing on disk; stale DB paths will cause frequent action failures. | Dashboard "Recent Activity" is still a placeholder. Files: [skill-0-dashboard/apps/web/src/pages/Dashboard.tsx#L61](/home/miles/dev2/skill-0/skill-0-dashboard/apps/web/src/pages/Dashboard.tsx#L61). Risk: the landing page does not yet provide real operational visibility. |
| Vector search infrastructure is implemented, including embeddings, SQLite-vec storage, KNN queries, statistics, and CLI usage. Files: [vector_db/search.py](/home/miles/dev2/skill-0/vector_db/search.py), [vector_db/vector_store.py](/home/miles/dev2/skill-0/vector_db/vector_store.py). Risk: first-run and deployment reliability depend on ML/model setup being consistent. | CI, docs, and local bootstrap are being aligned to a newer baseline. Files: [.github/workflows/ci.yml](/home/miles/dev2/skill-0/.github/workflows/ci.yml), [README.md](/home/miles/dev2/skill-0/README.md), [requirements-dev.txt](/home/miles/dev2/skill-0/requirements-dev.txt). Risk: documentation and actual repository state are temporarily out of sync. | Review Queue bulk approve is visible in the UI but intentionally disabled. Files: [skill-0-dashboard/apps/web/src/pages/ReviewQueue.tsx#L66](/home/miles/dev2/skill-0/skill-0-dashboard/apps/web/src/pages/ReviewQueue.tsx#L66). Risk: operators still need to review and approve low-risk skills one by one. |
| Governance DB and governance CLI pipeline are present, covering registration, scanning, equivalence testing, approval, rejection, and audit trail. Files: [tools/governance_db.py](/home/miles/dev2/skill-0/tools/governance_db.py), [tools/skill_governance.py](/home/miles/dev2/skill-0/tools/skill_governance.py). Risk: current persistence model is local SQLite, which will constrain concurrency and service scaling later. | Frontend build optimization is active, including lazy-loaded routes and a bundle-size guardrail. Files: [skill-0-dashboard/apps/web/src/App.tsx](/home/miles/dev2/skill-0/skill-0-dashboard/apps/web/src/App.tsx), [skill-0-dashboard/apps/web/package.json#L6](/home/miles/dev2/skill-0/skill-0-dashboard/apps/web/package.json#L6). Risk: local environment uses Node 18 here, while CI is pinned to Node 20 in [.github/workflows/ci.yml#L128](/home/miles/dev2/skill-0/.github/workflows/ci.yml#L128); local and CI behavior may diverge. | Historical snapshot: frontend automated tests were unstable here on `2026-03-23`. Current local state should be checked against the active web test baseline before reusing this claim. Files: [skill-0-dashboard/apps/web/src/App.test.tsx](/home/miles/dev2/skill-0/skill-0-dashboard/apps/web/src/App.test.tsx), [skill-0-dashboard/apps/web/package.json#L43](/home/miles/dev2/skill-0/skill-0-dashboard/apps/web/package.json#L43). Risk: frontend regression safety depends on the current dependency set, not this dated row alone. |
| Dashboard API router structure is complete across stats, skills, reviews, scans, and audit, all behind auth. Files: [skill-0-dashboard/apps/api/main.py](/home/miles/dev2/skill-0/skill-0-dashboard/apps/api/main.py), [skill-0-dashboard/apps/api/routers](/home/miles/dev2/skill-0/skill-0-dashboard/apps/api/routers). Risk: dashboard usefulness depends directly on governance DB data quality. | Batch scan/test service methods exist, but UI integration is still partial. Files: [skill-0-dashboard/apps/api/services/governance.py#L521](/home/miles/dev2/skill-0/skill-0-dashboard/apps/api/services/governance.py#L521), [skill-0-dashboard/apps/api/services/governance.py#L634](/home/miles/dev2/skill-0/skill-0-dashboard/apps/api/services/governance.py#L634). Risk: backend capability is ahead of frontend workflow support. | Historical snapshot: local Python regression was not verifiable in that environment. Current repo state already includes `pytest`, but app-specific dependencies may still be missing, so this row should not be read as the current blocker verbatim. Files: [requirements-dev.txt](/home/miles/dev2/skill-0/requirements-dev.txt). Risk: environment drift can still prevent full regression runs. |
| Main dashboard pages already exist and are wired to data hooks: Skills, Skill Detail, Security, Audit Log, and Review Queue. Files: [skill-0-dashboard/apps/web/src/pages/SkillsList.tsx](/home/miles/dev2/skill-0/skill-0-dashboard/apps/web/src/pages/SkillsList.tsx), [skill-0-dashboard/apps/web/src/pages/SkillDetail.tsx](/home/miles/dev2/skill-0/skill-0-dashboard/apps/web/src/pages/SkillDetail.tsx), [skill-0-dashboard/apps/web/src/pages/Security.tsx](/home/miles/dev2/skill-0/skill-0-dashboard/apps/web/src/pages/Security.tsx), [skill-0-dashboard/apps/web/src/pages/AuditLog.tsx](/home/miles/dev2/skill-0/skill-0-dashboard/apps/web/src/pages/AuditLog.tsx), [skill-0-dashboard/apps/web/src/pages/ReviewQueue.tsx](/home/miles/dev2/skill-0/skill-0-dashboard/apps/web/src/pages/ReviewQueue.tsx). Risk: UX is usable but still admin-console grade rather than fully polished product workflow. | Tests and CI stabilization are actively underway, based on the current uncommitted modifications in workflows, tests, frontend, and docs. Files: [.github/workflows/ci.yml](/home/miles/dev2/skill-0/.github/workflows/ci.yml), [tests](/home/miles/dev2/skill-0/tests), [skill-0-dashboard/apps/api/tests](/home/miles/dev2/skill-0/skill-0-dashboard/apps/api/tests). Risk: late-stage dependency or config drift can still break the "all green" baseline. | Historical snapshot: frontend JWT/session integration looked incomplete from that code path on `2026-03-23`. Current local code later added token attachment and auth-state handling, so this row is no longer the live authority. Files: [skill-0-dashboard/apps/web/src/api/client.ts](/home/miles/dev2/skill-0/skill-0-dashboard/apps/web/src/api/client.ts), [skill-0-dashboard/apps/web/src/auth/AuthProvider.tsx](/home/miles/dev2/skill-0/skill-0-dashboard/apps/web/src/auth/AuthProvider.tsx). Risk: validate current auth flow in code and tests rather than relying on this dated snapshot. |

## Overall Assessment

Historical assessment:
- This section preserves the `2026-03-23` judgment and should not be quoted as the latest project state without reconfirmation.

The project is beyond prototype stage. The main product shape is already present:

- Core search API exists.
- Governance workflow exists.
- Dashboard API exists.
- Dashboard frontend exists.
- Schema, parsed data, and tools exist.

At that date, the stage was described as:

`feature-complete foundation with stabilization and delivery work still in progress`

The highest remaining risks at that time were:

1. Frontend test instability.
2. Local Python verification environment not restored yet.
3. A few visible dashboard gaps remain unfinished.
4. Local and CI runtime baselines are not fully aligned.

## Recommended Next Priorities

Historical next-priorities snapshot:
- The list below reflects what looked next from the `2026-03-23` vantage point.

1. Restore local Python test environment and rerun the full regression suite.
2. Fix the frontend `ERR_REQUIRE_ESM` test failure and re-establish a trusted green baseline.
3. Decide whether to complete or remove visible placeholders such as Recent Activity.
4. Finish the UI path for bulk review actions if batch review is part of the release goal.
5. Confirm how JWT/session handling is intended to work in the dashboard web app.
