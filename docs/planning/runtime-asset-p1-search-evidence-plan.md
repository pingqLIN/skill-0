# Runtime Asset P1 Search Evidence Plan

- Status: **Executed — NO_GO**
- Date: `2026-07-18`
- Decision scope: FTS5 plus sqlite-vec retrieval evidence
- Traditional Chinese companion: [`runtime-asset-p1-search-evidence-plan.zh-tw.md`](runtime-asset-p1-search-evidence-plan.zh-tw.md)

## Objective

Decide whether FTS5 plus sqlite-vec hybrid retrieval has enough measured value
to justify a separate P1 prototype. This sprint does not add FTS5 to the
production schema or API and does not reopen physical database reorganization,
a second Asset Type, or Dashboard renaming.

## Isolation and review boundary

The benchmark opens the source Index read-only, records its SHA-256 before and
after execution, and queries only an integrity-checked disposable copy. Each
FTS5 profile exists in a separate ignored artifact database. No Governance or
Runtime authority database is opened or created.

The expanded suite was curated from Asset metadata only. A second agent
reviewed and froze the judgments before any retrieval measurement. The harness
validates the detached freeze manifest, suite digest, corpus snapshot, counts,
taxonomy, and exact profile options before it builds or searches anything.

## Frozen experiment

- Corpus: all 196 canonical Skill-backed Assets.
- Suite: 84 queries, split into 42 lexical and 42 semantic cases, with 120
  qrels, 85 distinct direct targets, and eight taxonomy groups.
- Vector baseline: current `all-MiniLM-L6-v2` sqlite-vec Asset search.
- Lexical baseline: FTS5 BM25 over title, description, and the existing
  `skill-text-v1` representation, with fixed weights `8, 4, 1`.
- Hybrid: equal-weight reciprocal-rank fusion, `k=60`, from the top 20 vector
  and FTS5 candidates. Ties sort by canonical Asset ID.
- Profiles: FTS5 baseline, `detail=none`, and
  `detail=none,columnsize=0`. Mapping storage is included in every artifact.
- Quality: binary `nDCG@5`, `MRR@5`, and `Recall@5`, reported overall and for
  both query subsets.
- Performance: one unmeasured warm-up followed by five measured warm runs per
  query; report p50/p95 search latency, build duration, and whole-file bytes.

## Predeclared decision gate

The result may be **GO for a separate P1 prototype**, never direct production
integration, only if one profile satisfies every condition:

1. all judgments resolve, all 196 Assets are measured, the suite is reviewed
   and frozen, and the source Index hash is unchanged;
2. at least 80 judged queries are present, including at least 30 lexical and
   30 semantic queries;
3. hybrid overall nDCG@5 is no more than `0.01` below vector and lexical-subset
   nDCG@5 improves by at least `0.05`;
4. hybrid semantic-subset nDCG@5 is no more than `0.02` below vector and overall
   Recall@5 is no more than `0.02` below vector;
5. hybrid p95 adds at most `25 ms` and at most `50%` over vector p95;
6. the complete FTS5 artifact is at most `25%` of the source Index size;
7. benchmark integrity, focused tests, full regressions, documentation gates,
   reviews, and scoped secret checks pass.

Failure of any technical gate is **NO_GO**. Insufficient coverage or missing
review/freeze evidence is `NO_GO_INSUFFICIENT_EVIDENCE`. The smallest artifact
may be selected only among profiles that pass every gate. A final source
isolation failure overrides every profile result.

## Batches

1. Curate and independently review the expanded judgments without retrieval.
2. Freeze the suite, detached manifest, profile definitions, deterministic
   scoring contract, and fail-closed tests.
3. Run one benchmark against the frozen inputs in a disposable directory.
4. Independently review result integrity, publish the authoritative English
   report plus Traditional Chinese companion, and run integrated verification.

## Rollback

Delete or archive the ignored benchmark directory and revert the research
commits if the harness is not retained. No operator data rollback is required
because authority data and production schemas are unchanged.

## Execution outcome

The frozen 84-query run returned `NO_GO`. All three profiles failed the `25%`
storage gate; the best ratio was `26.44%`. Hybrid lexical nDCG@5 improved by
`0.0347`, below the required `0.05`. The smallest profile also failed the
relative p95 latency gate. Production remains vector-only. See
[`../reports/runtime-asset-p1-search-evidence.md`](../reports/runtime-asset-p1-search-evidence.md).
