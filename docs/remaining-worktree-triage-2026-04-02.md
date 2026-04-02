# Remaining Worktree Triage

Status note: this file started as the live extraction note for the dirty `2026-04-02` worktree. The four recommended slices below were subsequently landed; keep it as an audit trail, not as an open checklist without re-checking current `git status`.

Date: `2026-04-02`
Context: `dirty main after runtime/dashboard, parser/corpus, review-doc, and yolo-unattended follow-on work`

## Current State

- Current uncommitted footprint is still dominated by mixed streams inside one dirty worktree.
- Largest buckets at time of inspection:
  - `parsed/`: `196`
  - `skill-0-dashboard/`: `30`
  - `docs/`: `23`
  - `tests/`: `9`
  - `tools/` + `scripts/`: `6`

Observed command snapshots:

```bash
git status --short
git diff --stat
git status --short | awk '{print $2}' | cut -d/ -f1 | sort | uniq -c | sort -nr
```

## Main Recommendation

- Do not keep treating the current dirty `main` worktree as one review stream.
- Split it into reviewable slices with one operational theme per branch or commit bundle.
- Extract the smallest coherent parser slice first before touching the full parsed-corpus churn.

## Recommended Extraction Order

1. `parsed-yolo-unattended-and-targeted-parser`
2. `dashboard-auth-runtime-hardening`
3. `parsed-corpus-and-complex-parser`
4. `review-bundle-and-dossier`

Why this order:

- The parser/yolo slice is now small, coherent, and already locally validated.
- Dashboard/runtime is the largest user-facing operational slice after that.
- Full parsed-corpus churn is still noisy and should stay isolated.
- Review/dossier docs are easiest to review after code direction is stable.

## Slice 1: Parsed YOLO And Targeted Parser Safety

Recommended branch intent:
`parsed-yolo-unattended-and-targeted-parser`

Include:

- `converted-skills/yolo-unattended/**`
- `parsed/yolo-unattended-skill.json`
- `scripts/auto_parse.py`
- `scripts/complex_skill_parser.py`
- `tests/test_auto_parse.py`
- `tests/test_complex_skill_parser.py`
- `tests/fixtures/complex_skills/**`

Optional include after manual review:

- `tests/fixtures/valid_skill.json`
- `tools/normalize_parsed_skills.py`

Why:

- This is the cleanest newly-added parser slice in the current worktree.
- It adds targeted parse mode, schema validation-on-write, repo-local command detection, and the new `yolo-unattended` skill.
- It is materially useful on its own and should not wait behind the massive corpus rewrite.

Suggested validation for this slice:

```bash
.venv/bin/python -m pytest tests/test_auto_parse.py tests/test_complex_skill_parser.py -q
.venv/bin/python scripts/auto_parse.py --force --skills yolo-unattended --validate
.venv/bin/python tools/validate_skill_schema.py parsed/yolo-unattended-skill.json
```

## Slice 2: Dashboard And Runtime Hardening

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
- `docs/planning/governance-p1-async-retry-spec-2026-03-31.md`
- `docs/planning/runtime-risk-hardening-spec-2026-03-31.md`
- `docs/document-authority-index-2026-03-27.md`
- `docs/planning/executable-dev-plan-2026-03-31.zh-TW.md`

Why:

- This remains the main operational slice: auth/session flow, runtime hardening, CI/deploy alignment, and tests tied to that stack.
- The two planning specs belong with the runtime/governance hardening stream, not the review-doc bundle.

## Slice 3: Parsed Corpus And Complex Parser Follow-On

Recommended branch intent:
`parsed-corpus-and-complex-parser`

Include:

- `parsed/*.json` except `parsed/yolo-unattended-skill.json` if Slice 1 already extracted
- `tools/batch_equivalence_backfill.py`
- `tools/skill_governance.py`
- `tools/skill_tester.py`
- `tests/test_embedder_contract.py`

Why:

- This is still the largest and noisiest bucket.
- It should remain isolated from dashboard/runtime and from the smaller parser-yolo slice.
- Review cost is dominated by generated corpus churn, so keep it separate on purpose.

## Slice 4: Review Bundle And Dossier Docs

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
- `DEVILS_ADVOCATE_REVIEW_CONCEPTUAL_2026-03-26.md`

Why:

- These are mostly review artifacts, diagrams, dossier material, and planning context.
- They should be authority-reviewed as a documentation bundle rather than mixed into operational commits.

## Cleanup / Do Not Commit Blindly

Review and usually exclude from any first-pass commit:

- `parsed/agent-skills-skill.json`
- `docs/p0-commit-boundaries-2026-03-27.md`

Why:

- `parsed/agent-skills-skill.json` was touched as parser spillover during targeted work and should not ride along accidentally.
- `docs/p0-commit-boundaries-2026-03-27.md` is process scaffolding, not product/runtime content.

## Practical Next Step

If the goal is to make progress quickly without destabilizing the rest of the dirty worktree, extract Slice 1 first.

Minimal candidate add set:

```bash
git add \
  converted-skills/yolo-unattended \
  parsed/yolo-unattended-skill.json \
  scripts/auto_parse.py \
  scripts/complex_skill_parser.py \
  tests/test_auto_parse.py \
  tests/test_complex_skill_parser.py \
  tests/fixtures/complex_skills
```

Then re-check what remains:

```bash
git status --short
```

## Outcome Note (`2026-04-02`)

Executed extraction result:

1. `e2fc8c1` `Add yolo-unattended skill and targeted parser safety`
2. `99f56e5` `Harden dashboard auth and governance runtime`
3. `3534eb0` `Normalize parsed corpus and align fidelity tooling`
4. `6d3ad5e` `Add review dossier and shared documentation bundle`

Residual leftovers after these four commits:

- `parsed/agent-skills-skill.json`
- `docs/p0-commit-boundaries-2026-03-27.md`
- `docs/remaining-worktree-triage-2026-03-27.md`
- `docs/remaining-worktree-triage-2026-04-02.md`
