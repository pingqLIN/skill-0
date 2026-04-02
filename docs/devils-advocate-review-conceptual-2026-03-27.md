# Skill-0 Devil's Advocate Review

Date: `2026-03-27`

Scope:
- `skill-0` conceptual / theoretical positioning
- canonical contract stability
- governance model validity
- equivalence claim strength

This document is intentionally written from a hostile-review posture. The goal is not to praise the current architecture, but to stress where the project's claims are stronger than its present evidence.

## Executive Summary

Current conclusion:

> Skill-0 is credible as a local-first search/review prototype.
> It is not yet credible as a rigorously grounded decomposition + governance + equivalence framework.

The largest issue is not UI polish, test count, or containerization. The largest issue is that the repo currently lacks a single stable canonical contract. The live schema, generated `parsed/*.json`, parser outputs, and embedding/search layer are not aligned. That breaks the project's own theory that a shared structured representation is the foundation for search, comparison, and governance.

## Review Environment

I created a repo-local virtual environment:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install \
  pytest pytest-cov pytest-timeout \
  fastapi uvicorn pydantic PyJWT prometheus_client structlog httpx rich \
  pydantic-settings numpy scikit-learn sqlite-vec markdown-it-py jsonschema
```

Notes:
- I intentionally did **not** complete the full `requirements-dev.txt` install path because it started pulling the CUDA-flavored `torch` stack for `sentence-transformers`, which is unnecessary for this review and materially wasteful on a CPU review host.
- The environment is sufficient for parser/API/rate-limit tests, schema validation, and static review.

## Verification Performed

### 1. Targeted tests

Command:

```bash
.venv/bin/python -m pytest \
  tests/test_complex_skill_parser.py \
  tests/test_api_security.py \
  tests/integration/test_auth_flow.py \
  tests/integration/test_rate_limiting.py -q
```

Result:
- `44 passed in 1.26s`

Interpretation:
- The local review environment is functional.
- The current safety net covers parser shape checks, auth, and rate limiting.
- It does **not** prove the decomposition model is semantically sound.

### 2. Live schema validation against generated artifacts

Validation script outcome:

- `parsed/docx-skill.json`: `12` schema errors
- `parsed/webapp-testing-skill.json`: `9` schema errors
- Entire `parsed/` directory: `178` invalid files

Representative failures:

```text
parsed/docx-skill.json
- decomposition/directives/0: 'name' is a required property
- decomposition/rules/0: 'name' is a required property
- decomposition/rules/0: 'condition_type' is a required property
- decomposition/rules/0: 'returns' is a required property

parsed/*.json sample failures
- 'claude__a11y' does not match '^(claude|mcp)__[a-z_]+__[a-z_]+$'
```

Interpretation:
- The repo's "live schema" is not a contract the repo's own parsed dataset currently satisfies.

## Findings

### Finding 1: There is no single canonical data contract

Severity: `High`

The project's core pitch is:

- convert natural-language skills into a shared structure
- use that shared structure for search, comparison, and governance

But the repo currently contains incompatible dialects:

- `schema/skill-decomposition.schema.json` requires `rule.name`, `condition_type`, `returns`, and `directive.name`
- `parsed/*.json` still emit `description`, `condition`, `output`, and directives without `name`
- `tools/batch_parse.py` still labels itself `v2.1`
- `vector_db/embedder.py` reads yet another field set: `type`, `mode`, `content`

Representative evidence:

- `schema/skill-decomposition.schema.json:305`
- `schema/skill-decomposition.schema.json:372`
- `schema/skill-decomposition.schema.json:594`
- `parsed/docx-skill.json:72`
- `parsed/docx-skill.json:92`
- `tools/batch_parse.py:3`
- `tools/batch_parse.py:266`
- `vector_db/embedder.py:103`
- `vector_db/embedder.py:115`
- `vector_db/embedder.py:126`

This is not just implementation drift. It directly breaks the project's theory that a shared structured layer is the substrate underneath search and governance.

### Finding 2: The governance model governs mutable names, not immutable artifacts

Severity: `High`

The docs describe governance as lifecycle tracking:

1. register skill
2. capture provenance / author / license
3. scan
4. equivalence test
5. approve / reject / block
6. retain audit trail

But the persistence model does not bind those decisions to immutable artifacts:

- `tools/governance_db.py` uses `name TEXT NOT NULL UNIQUE`
- `skill_id` is a generated UUID, not a content-addressed artifact identity
- there is no checksum or artifact revision table
- `create_skill()` ignores `**kwargs`, so version/source metadata is not captured at creation time
- `update_skill()` mutates the same row in place

Representative evidence:

- `docs/dossier/04-core-logic-and-governance.md:74`
- `docs/dossier/04-core-logic-and-governance.md:96`
- `tools/governance_db.py:148`
- `tools/governance_db.py:308`
- `tools/governance_db.py:372`

Practical consequence:

An approval, risk score, or equivalence result can silently drift underneath the same skill name. That means the system is closer to "workflow on mutable records" than "governance over traceable artifacts."

### Finding 3: "Equivalence" is currently weighted similarity, not equivalence

Severity: `Medium-High`

`tools/skill_tester.py` computes:

- semantic similarity of bodies
- structure similarity from headings and code blocks
- keyword or TF-IDF similarity
- metadata completeness

It then combines these via fixed weights and thresholds and stores the result in `equivalence_tests`.

Representative evidence:

- `tools/skill_tester.py:103`
- `tools/skill_tester.py:112`
- `tools/skill_tester.py:450`
- `tools/skill_tester.py:567`

This is a fidelity / resemblance score, not a proof of behavioral or semantic equivalence.

This matters because the repo's own shared contract is already stricter:

- `docs/shared/02-mode-and-equivalence-contract.md:30`
- `docs/shared/02-mode-and-equivalence-contract.md:39`

That contract says strict equivalence claims need named fixtures, expected canonical outputs, repeatable comparison rules, and documented pass/fail results. The current tester does not meet that bar.

### Finding 4: The ternary ontology is underconstrained and operationally collapses into "Directive"

Severity: `Medium-High`

In theory:

- `Action` = atomic operation
- `Rule` = atomic judgment
- `Directive` = descriptive statement

In practice, `Directive` is defined as "decomposable but chosen not to decompose at this level," which makes it the model's residual bucket. The schema only requires a small set of fields, and provenance is optional.

Representative evidence:

- `README.md:42`
- `README.md:59`
- `schema/skill-decomposition.schema.json:372`
- `schema/skill-decomposition.schema.json:422`

The parser implementation exposes the consequence:

- keyword-bag classification for action/rule/directive typing
- default directive type fallback to `knowledge`
- long sentences and directive-like sections collapse into directives

Representative evidence:

- `scripts/auto_parse.py:65`
- `scripts/auto_parse.py:102`
- `scripts/auto_parse.py:212`
- `scripts/auto_parse.py:224`

From a devil's-advocate stance, this means ambiguous or difficult content is not forced into a falsifiable model; it is simply absorbed into the least constrained category.

### Finding 5: The current tests mostly verify shape, not semantic truth

Severity: `Medium`

The tests I ran passed, but their protection scope is limited.

For example:

- `tests/test_complex_skill_parser.py` validates counts, extracted paths, and finding categories
- it does not validate that decomposition preserves source meaning
- it does not validate that parsed artifacts conform to the current live schema

Representative evidence:

- `tests/test_complex_skill_parser.py:14`
- `tests/test_complex_skill_parser.py:24`

This is not a criticism of having tests. It is a criticism of what the passing tests currently entitle the project to claim.

## Recommendations

### P0: Stabilize one canonical contract

Choose one of these as source of truth and make the rest obey it:

- live schema
- parser output
- parsed dataset

Do not keep all three drifting independently.

Minimum acceptance criteria:

- `parsed/*.json` validates cleanly against the published live schema
- embedder/search consumes the same field names the schema defines
- docs stop mixing `2.1`, `2.4`, and draft `2.5` semantics without explicit compatibility language

### P1: Change governance from skill-name-centric to artifact-centric

Introduce immutable artifact identity, for example:

- content hash / checksum
- source commit + path + extracted-at tuple
- revision table separate from logical skill name

Approvals, scans, and equivalence results should attach to a revision, not just the mutable latest row.

### P2: Rename or narrow "equivalence"

Until stronger evidence exists, use language like:

- compatibility score
- fidelity assessment
- conversion resemblance

Reserve "equivalence" for cases with canonical outputs and reproducible comparison rules.

### P3: Make decomposition quality falsifiable

If the ternary model is going to be a real theory and not a tagging convenience layer, add:

- required provenance or confidence on inferred elements
- explicit unresolved/ambiguous states
- review workflows for "cannot classify without semantic loss"

## Final Judgment

Skill-0 is strongest when described as:

> a pragmatic local-first prototype for indexing, reviewing, and operationalizing skill documents

Skill-0 is weakest when described as:

> a stable formal decomposition/governance/equivalence framework

That second claim may eventually become true, but the current repo state does not yet justify it.
