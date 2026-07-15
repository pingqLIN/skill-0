# Skill-0 SkillOS Curation Development Plan

- Date: `2026-07-15`
- Status: `Current development plan / P2 offline Curator complete / P3 not started`
- Authority: `This non-suffixed English document is authoritative; the .zh-tw.md file is its human-readable companion.`
- Workspace: `<repo-root>`
- Branch: `codex/skillos-curation-mvp`

## 1. Executive Decision

Skill-0 will add an experience-driven skill curation track inspired by the paper
*SkillOS: Learning Skill Curation for Self-Evolving Agents*. The project will
remain Skill-0: an ARD decomposition, schema, retrieval, and revision-governance
system. The new work extends that foundation with a governed loop that turns
execution experience into proposed skill revisions and measures whether those
revisions improve later related tasks.

The first implementation is not an Agent OS, sandbox runtime, Saga engine, or
full reproduction of the paper's reinforcement-learning training. It is an
offline, human-gated curation MVP that can establish the data contracts and
evaluation evidence required before training a curator.

## 2. Naming and Workspace Decision

| Surface | Decision | Reason |
|---|---|---|
| Product and canonical repository | Keep `Skill-0` | Existing identity, history, schema, and integrations remain valid. |
| Development track | `SkillOS Curation` | Clearly identifies the research direction without redefining the whole product. |
| Local worktree | `skill-0-skillos` | Makes the experimental direction visible while preserving the canonical checkout. |
| Branch | `codex/skillos-curation-mvp` | Isolates the first curation slice from ARDE runtime experiments and unrelated dirty work. |
| Future code namespace | Prefer `curation/` and `evaluation/` | Describes product responsibilities without claiming a paper reproduction. |

Do not rename the canonical repository yet. If curation later becomes a separate
deployable product, evaluate `skill-0-curation` as the neutral repository name.

## 3. Correct Paper Context

Primary source:

- Ouyang et al., *SkillOS: Learning Skill Curation for Self-Evolving Agents*,
  arXiv:2605.06614v1, 7 May 2026:
  <https://arxiv.org/html/2605.06614v1>

The paper presents an experience-driven reinforcement-learning recipe for a
Skill Curator. Its core loop is:

```text
task stream
  -> frozen Agent Executor retrieves and applies skills
  -> execution trajectory and correctness feedback
  -> Skill Curator proposes insert, update, or delete operations
  -> external SkillRepo changes
  -> later related tasks measure downstream utility
```

The paper groups related tasks so that earlier curation decisions receive delayed
feedback from later tasks. It trains the curator with GRPO and a composite reward
covering future-task outcomes, valid function calls, skill content quality, and
repository compactness.

Important boundaries from the paper:

- SkillOS is a skill-curation learning method, not a general runtime operating system.
- The Agent Executor is frozen during curator training.
- The reference retrieval path uses BM25.
- The research representation flattens a skill to one Markdown file with YAML frontmatter.
- The paper identifies dense or hybrid retrieval, multi-file skills, hierarchy,
  and compositional skills as future directions.

## 4. Why Skill-0 Is a Suitable Substrate

| Paper requirement | Existing Skill-0 capability | Fit | Required extension |
|---|---|---:|---|
| Structured reusable skills | ARD decomposition and schema v2.4.0 | High | Preserve source artifacts and add curation-side contracts. |
| Relevant-skill retrieval | Dense semantic search with local embeddings | High | Add BM25 and hybrid comparison baselines. |
| SkillRepo updates | Revision-aware governance storage | High | Represent changes as proposals before creating revisions. |
| Valid curation operations | Schema normalization and validation | High | Validate insert/update/delete semantics and base revisions. |
| Human oversight | Review, approve, reject, audit, dashboard | High | Add curation proposal and evaluation views. |
| Experience ingestion | No canonical trajectory contract | Missing | Add a provenance-safe trajectory schema and ingestion path. |
| Future-task feedback | No grouped-task evaluation harness | Missing | Add before/after evaluation records and metrics. |
| Learned curator | No curator policy or training loop | Missing | Start with offline LLM proposals; defer RL. |

Skill-0 improves on two research simplifications without changing the paper's
central hypothesis: it can compare BM25 with dense and hybrid retrieval, and it
can retain original multi-file skill folders while using parsed ARD data as a
sidecar rather than flattening every skill into a replacement Markdown file.

## 5. Target MVP Loop

```text
Original Skill-0 skill source and parsed ARD
  -> ingest a redacted execution trajectory
  -> retrieve related current skill revisions
  -> offline Curator creates an insert/update/delete proposal
  -> schema, ARD, provenance, and conflict validation
  -> human governance approval or rejection
  -> approved proposal creates a new immutable skill revision
  -> later related tasks evaluate baseline versus candidate
  -> evaluation evidence updates proposal and revision provenance
```

Hard rules:

1. The Curator cannot write directly to the canonical SkillRepo.
2. Every update or delete proposal identifies the base `skill_id` and revision.
3. Approval creates a new revision; it does not mutate an approved artifact in place.
4. Raw trajectories are not copied into skills or logs by default.
5. Evidence is a derived curation, evaluation, and revision-provenance envelope.
   It is not a fourth peer category beside Action, Rule, and Directive.
6. A proposal cannot be promoted without validation and a recorded human decision.
7. Later evaluation tasks are temporal holdouts and are not visible to the Curator
   that produces the proposal being evaluated.
8. Approval rechecks that the proposal's base revision is still current; stale
   proposals must be superseded or explicitly rebased.

## 6. First Data Contracts

### 6.1 Trajectory

The trajectory contract should include:

- stable trajectory, task, executor, and run identifiers;
- task-family or grouping attributes;
- ordered observations, tool/action summaries, and terminal outcome;
- retrieved skill IDs and revision IDs;
- correctness or reviewer feedback with provenance;
- timestamps, source, redaction state, and content checksum;
- retention class and a reference to quarantined raw content when full replay is required;
- explicit exclusion of secrets, credentials, cookies, and unrestricted chain of thought.

### 6.2 Curation Proposal

The proposal contract should include:

- operation: `insert`, `update`, or `delete`;
- target skill and base revision where applicable;
- proposed source artifact or patch, never an implicit in-place mutation;
- supporting trajectory and retrieved-skill references;
- curator identity, model/config identity, rationale summary, and confidence;
- schema, ARD, duplicate, conflict, and provenance validation results;
- governance state: draft, pending review, approved, rejected, or superseded;
- approval actor, decision reason, and resulting revision ID.

### 6.3 Evaluation Result

The evaluation contract should include:

- task group and evaluation protocol identity;
- baseline and candidate repository snapshots;
- executor and retrieval configuration;
- later-task success, steps, tokens, latency, and error summaries;
- proposal acceptance and invalid-operation outcomes;
- duplicate/conflict findings and repository token growth;
- deterministic links to proposals, revisions, trajectories, and test fixtures.

## 7. Phased Implementation Plan

### P0: Planning and baseline lock

Deliverables:

- this plan and its Traditional Chinese companion;
- clean worktree and branch based on local `main`;
- paper source, scope correction, naming decision, and ARDE disposition;
- focused baseline tests for schema and revision governance.

Gate: documentation checks and focused baseline tests pass; no runtime code is added.

### P1: Contract-only foundation

Deliverables:

- JSON Schemas for trajectory, curation proposal, and evaluation result;
- positive and negative fixtures;
- Python validation and normalization helpers that follow existing schema patterns;
- provenance and redaction rules;
- temporal holdout and stale-base-revision negative fixtures.

Gate: legacy parsed skills remain unchanged and all new contract tests pass.

Implementation record (`2026-07-15`):

- Completed in commit `015b0e6` with three Draft-07 contracts under `schema/`,
  positive and negative fixtures under `tests/fixtures/curation_contracts/`, and
  semantic validation helpers in `tools/curation_contract.py`.
- The helper enforces redaction, ordered trajectory steps and retrieval ranks,
  operation/base-revision consistency, temporal holdout separation, approved
  validation state, and evaluation snapshot/delta consistency.
- P1 verification passed: the contract-focused tests, the full core regression
  (`184 passed`), and Flake8 `7.3.0` using the P1 fatal-error selection
  (`E9,F63,F7,F82`, result `0`).
- No files under `parsed/`, governance databases, APIs, runtime execution paths,
  or Curator generation paths were changed. P2 remains a separate review gate.

### P2: Offline, human-gated Curator

Deliverables:

- CLI or service function that consumes trajectory plus retrieved skills;
- structured insert/update/delete proposal output;
- deterministic prompt/config manifest;
- dry proposal mode only, with no canonical repository write path.

Gate: invalid operations fail closed and proposal generation cannot bypass governance.

Implementation record (`2026-07-16`):

- Added a two-step `prepare`/`propose` boundary in `curation/offline_curator.py`
  and `tools/offline_curator.py`; it performs no network or model-provider calls.
- Added pinned prompt/config resources plus Draft-07 skill-context and decision
  contracts. Prompt packages and decisions are checksum-bound and deterministic.
- Insert, update, and delete operations emit only `draft` proposals. Candidate
  content, stale target revisions, package tampering, and repo-local output paths
  outside ignored `output/curation/` fail closed.
- Added English and Traditional Chinese operator documentation. P2 does not
  persist proposals, call governance, create revisions, or write a SkillRepo.
- Verification passed: `50` focused tests, Flake8 fatal checks (`0`), Python
  compile checks, and the full core plus dashboard API regression
  (`279 passed`).

### P3: Revision governance integration

Deliverables:

- proposal persistence and audit events;
- approve, reject, and supersede workflow;
- approved insert/update creates a new revision;
- delete remains a governed state transition with recoverable history;
- optimistic concurrency rejects promotion when the base revision has changed.

Gate: every promoted artifact is revision-bound and traceable to its proposal;
stale proposals cannot overwrite a newer revision.

### P4: Retrieval baseline

Deliverables:

- BM25 baseline matching the paper's reference path;
- existing dense retrieval baseline;
- hybrid rank-fusion experiment;
- fixed corpus, query set, top-k budget, and reproducible metrics.

Gate: retrieval comparisons use identical inputs and report relevance plus downstream results.

### P5: Grouped-task evaluation harness

Deliverables:

- task-group schema and fixture runner;
- baseline versus curated repository snapshots;
- future-task success and efficiency metrics;
- proposal quality, invalid operation, duplication, conflict, and compactness metrics;
- temporal split evidence proving that the evaluated proposal did not observe later tasks.

Gate: at least one controlled benchmark shows whether approved curation improves later tasks.

### P6: Curator learning research gate

Only after P5 demonstrates measurable value, decide whether to reproduce GRPO or
another learned-curator approach. This phase requires a separate compute, data,
model-license, reproducibility, and cost review. The paper reports a materially
larger training setup than this MVP, so RL is not an implied deliverable.

## 8. Success Metrics

Primary metrics:

- future-task success or exact-match delta against the unchanged baseline;
- steps or tokens required per successful task;
- human proposal acceptance rate;
- invalid curation operation rate;
- duplicate or contradictory skill rate;
- SkillRepo token and revision growth;
- retrieval relevance at the fixed top-k budget.

MVP success requires evidence of later-task improvement without unacceptable
invalid operations, conflicts, or repository growth. Proposal volume alone is not success.

## 9. ARDE v4 Disposition

| Existing ARDE v4 direction | Disposition | Mainline rule |
|---|---|---|
| ARD parser, canonical schema, semantic search | Keep | Core Skill-0 substrate. |
| Revision governance and human review | Keep | Promotion gate for curator proposals. |
| Evidence projection and append-only audit ideas | Adapt | Use for proposal, evaluation, and revision provenance. |
| Runtime Contract and `/api/runs` | Experimental | Separate safety extension; not required by SkillOS. |
| Dry-run executor and runtime ledger | Experimental | Must not block the curation MVP. |
| Saga compensation and crash recovery | Experimental | Relevant only to side-effect execution, not paper reproduction. |
| MCP, Agents SDK, LangGraph, OPA, sandbox adapters | Defer | Revisit only after the curation loop has evidence. |
| Evidence as a fourth ARD peer | Reject | Evidence remains derived metadata and provenance. |
| Skill-0 as a complete Agent OS | Reject | Product remains a skill intelligence and governance layer. |

No ARDE runtime commit will be merged into this branch as part of the curation MVP.

## 10. Risks and Rollback

| Risk | Control | Rollback or disable path |
|---|---|---|
| Curator writes harmful or low-quality skills | Proposal-only output plus human approval | Reject or supersede proposal; current revision remains unchanged. |
| Sensitive trajectory content enters storage | Redaction contract and explicit allowed fields | Quarantine the trajectory record and invalidate dependent proposals. |
| Repository grows without utility | Compactness and duplicate metrics | Reject proposals or revert current pointer to the prior revision. |
| Retrieval comparison is biased | Fixed corpus, top-k, and executor settings | Re-run from immutable snapshots. |
| Paper reproduction claims exceed evidence | Separate research reproduction from product MVP | Label results as engineering experiments until benchmarks pass. |
| Experimental runtime work contaminates scope | Separate branch and module boundary | Keep runtime commits unmerged and feature-disabled. |

## 11. Development Workflow Contract

The `dev-workflow-scale-planner` classification is `large`, executed in fast
non-interactive planning mode for this document-only slice.

Implementation will proceed in reviewable commits:

1. plan and authority links;
2. contracts and fixtures;
3. offline Curator proposal path;
4. governance integration;
5. retrieval baselines;
6. grouped-task evaluation.

Each implementation commit requires targeted tests and a read-only review. Public
push, release, dependency mutation, database migration, external model calls with
private data, and runtime exposure remain explicit approval checkpoints.

## 12. Immediate Next Development Slice

P2 is complete. Stop before P3 until the P2 proposal-only boundary is reviewed.
The next separately approved slice would be P3 only:

1. define proposal persistence and append-only audit records;
2. add approve, reject, and supersede transitions;
3. preserve proposal and revision provenance without mutating approved artifacts;
4. recheck optimistic concurrency at promotion time;
5. create revisions only after all required validations and human approval pass;
6. stop before retrieval-baseline work in P4.
