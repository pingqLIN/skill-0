# Runtime Asset P1 Search Evidence Plan

- Status: **Executed — NO_GO_INSUFFICIENT_EVIDENCE**
- Date: `2026-07-18`
- Decision scope: FTS5 plus sqlite-vec retrieval evidence
- Traditional Chinese companion: [`runtime-asset-p1-search-evidence-plan.zh-tw.md`](runtime-asset-p1-search-evidence-plan.zh-tw.md)

## Objective

Decide whether FTS5 plus sqlite-vec hybrid retrieval has enough measured value
to justify a separate P1 prototype. This sprint does not add FTS5 to the
production schema or API and does not reopen physical database reorganization,
a second Asset Type, or Dashboard renaming.

## Isolation boundary

The benchmark must open the source Index read-only, record its SHA-256 before
and after execution, and build a disposable SQLite backup under an ignored
artifact directory. FTS5 tables exist only in a separate disposable database
in that directory. No operator
Governance or Runtime database is opened, and no benchmark artifact is an
authority source.

## Fixed experiment

- Corpus: all 196 checked-in canonical Skill-backed Assets.
- Judgments: a versioned query file with explicit relevant source paths,
  resolved to canonical Asset IDs at runtime; lexical and semantic subsets are
  reported separately.
- Vector baseline: current `all-MiniLM-L6-v2` sqlite-vec Asset search.
- Lexical baseline: FTS5 BM25 over title, description, and the existing
  `skill-text-v1` representation, with fixed column weights `8, 4, 1`.
- Hybrid: equal-weight reciprocal-rank fusion, `k=60`, from the top 20 vector
  and FTS5 candidates. Ties sort by canonical Asset ID.
- Quality: binary `nDCG@5`, `MRR@5`, and `Recall@5`.
- Performance: one unmeasured warm-up followed by five measured warm runs per
  query; report p50/p95 search latency, build duration, and FTS5 storage bytes.

## Predeclared decision gate

The result may be **GO for a separate P1 prototype**, never direct production
integration, only if all of the following hold:

1. all judgments resolve, all 196 Assets are measured, and the source Index
   hash is unchanged;
2. a representative GO decision requires at least 80 judged queries, including
   at least 30 lexical and 30 semantic queries. A smaller pilot may run but must
   return `NO_GO_INSUFFICIENT_EVIDENCE` regardless of directional metrics;
3. hybrid overall nDCG@5 is no more than `0.01` below vector and lexical-subset
   nDCG@5 improves by at least `0.05`;
4. hybrid semantic-subset nDCG@5 is no more than `0.02` below vector and overall
   Recall@5 is no more than `0.02` below vector;
5. hybrid p95 adds at most `25 ms` and at most `50%` over vector p95;
6. the FTS5 artifact adds at most `25%` of the source Index size;
7. the benchmark, focused tests, full Python regression, documentation gates,
   and artifact/secret scans pass.

Failure of any technical gate is **NO-GO**; insufficient query coverage is
`NO_GO_INSUFFICIENT_EVIDENCE`. A GO authorizes only a later reviewed
prototype plan; it does not authorize production DDL or API changes.

## Batches

1. Freeze the plan, query judgments, deterministic scoring contract, and unit
   tests.
2. Run the benchmark in a disposable directory and capture machine-readable
   evidence.
3. Review result integrity, publish an English authoritative decision report
   plus Traditional Chinese companion, and run integrated verification.

## Rollback

Delete or archive the ignored disposable benchmark directory. Revert the
research commits if the harness is not retained. No operator data rollback is
required because the source Index is read-only and production schemas are
unchanged.

## Execution outcome

The frozen 18-query pilot ran on `2026-07-18` and returned exit `5`,
`NO_GO_INSUFFICIENT_EVIDENCE`. Directional quality and latency gates passed,
but representative query coverage failed (`18 < 80`) and the FTS5 artifact
ratio failed (`33.53% > 25%`). Production remains vector-only. See
[`../reports/runtime-asset-p1-search-evidence.md`](../reports/runtime-asset-p1-search-evidence.md).
