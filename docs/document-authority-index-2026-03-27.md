# Skill-0 Document Authority Index

Updated: `2026-05-04`
Purpose: `separate live authority from historical and conceptual documents`

## Start Here

Use these documents first when making current project decisions:

1. [development-recommendation-2026-04-27.zh-TW.md](<repo-root>/docs/development-recommendation-2026-04-27.zh-TW.md) - reviewed next-stage direction and 8HR loop shape.
2. [executable-dev-plan-2026-03-31.zh-TW.md](<repo-root>/docs/planning/executable-dev-plan-2026-03-31.zh-TW.md) - live checkpoint execution plan, refreshed on 2026-04-27.
3. [project-development-stage-report-2026-04-27-8hr-loop.md](<repo-root>/docs/project-development-stage-report-2026-04-27-8hr-loop.md) - latest completed development-loop evidence.
4. [dependabot-vulnerability-inventory-2026-04-27.md](<repo-root>/docs/security/dependabot-vulnerability-inventory-2026-04-27.md) - web dependency remediation record.
5. [pilot-adoption-guide-2026-04-30.zh-TW.md](<repo-root>/docs/pilot-adoption-guide-2026-04-30.zh-TW.md) - 30-minute pilot adoption path for reviewers/operators.
6. [gui-governance.md](<repo-root>/docs/gui-governance.md) - current repository-boundary decision for governing `skill-0-GUI` as a companion repo.
7. [skill-decomposition.schema.json](<repo-root>/schema/skill-decomposition.schema.json) - canonical schema source of truth.

## Current Snapshot

- Repo root: `<repo-root>`
- Branch: `main`
- Parsed corpus: `196` checked-in JSON files
- Imported corpus: `164` `converted-skills/` directories
- Schema validation baseline: `196 passed, 0 failed`
- Python + dashboard API regression baseline: `221 passed, 61 warnings`
- Dashboard web baseline: `26 passed`; production build passed
- Local web dependency audit after safe bumps: `0 vulnerabilities`
- Public checkout DB identity baseline: `tools/report_db_identity_drift.py --allow-missing-db` reports `parsed=196` and warns when runtime DB files are intentionally absent.

## Authoritative Current Baseline

- [development-recommendation-2026-04-27.zh-TW.md](<repo-root>/docs/development-recommendation-2026-04-27.zh-TW.md)
- [executable-dev-plan-2026-03-31.zh-TW.md](<repo-root>/docs/planning/executable-dev-plan-2026-03-31.zh-TW.md)
- [final-development-phase-plan-2026-03-23.md](<repo-root>/docs/final-development-phase-plan-2026-03-23.md)
- [project-improvement-plan-2026-03-27.zh-TW.md](<repo-root>/docs/project-improvement-plan-2026-03-27.zh-TW.md)
- [p0-repair-plan-2026-03-27.md](<repo-root>/docs/p0-repair-plan-2026-03-27.md)
- [contract-decision.md](<repo-root>/docs/contract-decision.md)
- [schema-compatibility-note.md](<repo-root>/docs/schema-compatibility-note.md)
- [gui-governance.md](<repo-root>/docs/gui-governance.md)
- [skill-decomposition.schema.json](<repo-root>/schema/skill-decomposition.schema.json)

## Review And Assessment Artifacts

- [external-agent-audit-synthesis-2026-04-27.zh-TW.md](<repo-root>/docs/external-agent-audit-synthesis-2026-04-27.zh-TW.md)
- [project-development-report-2026-04-27.zh-TW.md](<repo-root>/docs/project-development-report-2026-04-27.zh-TW.md)
- [dependabot-vulnerability-inventory-2026-04-27.md](<repo-root>/docs/security/dependabot-vulnerability-inventory-2026-04-27.md)
- [release-rehearsal-risk-inventory-2026-04-27.md](<repo-root>/docs/release-rehearsal-risk-inventory-2026-04-27.md)
- [pilot-adoption-guide-2026-04-30.zh-TW.md](<repo-root>/docs/pilot-adoption-guide-2026-04-30.zh-TW.md)
- [project-development-stage-report-2026-04-27-8hr-loop.md](<repo-root>/docs/project-development-stage-report-2026-04-27-8hr-loop.md)
- [project-review-2026-03-23.md](<repo-root>/docs/project-review-2026-03-23.md)
- [external-review-report-2026-03-23.md](<repo-root>/docs/external-review-report-2026-03-23.md)
- [final-phase-plan-review-2026-03-23.md](<repo-root>/docs/final-phase-plan-review-2026-03-23.md)
- [final-phase-plan-review-round2-2026-03-23.md](<repo-root>/docs/final-phase-plan-review-round2-2026-03-23.md)

## Historical Context Only

- [reference.md](<repo-root>/reference.md)
- [implementation-summary.md](<repo-root>/docs/implementation-summary.md)
- [current-execution-plan-2026-03-19.md](<repo-root>/docs/planning/current-execution-plan-2026-03-19.md)
- [plan.md](<repo-root>/docs/planning/plan.md)
- [plan-20-skills.md](<repo-root>/docs/planning/plan-20-skills.md)
- [yolo-dev-plan.md](<repo-root>/docs/planning/yolo-dev-plan.md)
- [project-progress-report-2026-03-23.md](<repo-root>/docs/project-progress-report-2026-03-23.md)
- [FINAL_PHASE_PLAN.md](<repo-root>/FINAL_PHASE_PLAN.md)

## Process Aids And Local Triage Records

- [p0-commit-boundaries-2026-03-27.md](<repo-root>/docs/p0-commit-boundaries-2026-03-27.md)
- [remaining-worktree-triage-2026-03-27.md](<repo-root>/docs/remaining-worktree-triage-2026-03-27.md)
- [remaining-worktree-triage-2026-04-02.md](<repo-root>/docs/remaining-worktree-triage-2026-04-02.md)
- [parsed-dataset-validation-report-2026-03-27.md](<repo-root>/docs/parsed-dataset-validation-report-2026-03-27.md)

## Design And Conceptual Pressure Tests

- [governance-p1-async-retry-spec-2026-03-31.md](<repo-root>/docs/planning/governance-p1-async-retry-spec-2026-03-31.md)
- [runtime-risk-hardening-spec-2026-03-31.md](<repo-root>/docs/planning/runtime-risk-hardening-spec-2026-03-31.md)
- [schema-extension-design-complex-skills-2026-03-24.md](<repo-root>/docs/schema-extension-design-complex-skills-2026-03-24.md)
- [devils-advocate-review-conceptual-2026-03-27.md](<repo-root>/docs/devils-advocate-review-conceptual-2026-03-27.md)
- [devils-advocate-review-conceptual-2026-03-27.zh-TW.md](<repo-root>/docs/devils-advocate-review-conceptual-2026-03-27.zh-TW.md)

## Usage Rule

- If two documents conflict, prefer `Start Here` and `Current Snapshot` first, then `Authoritative Current Baseline`.
- If a document is listed under `Historical Context Only`, treat its body claims as archival unless reconfirmed in current code or current-baseline docs.
- Historical local absolute paths have been redacted; use `<repo-root>` as the portable repository-root placeholder.
