# Runtime Asset P1 Search Evidence Decision

- Decision: **NO_GO_INSUFFICIENT_EVIDENCE**
- Date: `2026-07-18`
- Plan: [`../planning/runtime-asset-p1-search-evidence-plan.md`](../planning/runtime-asset-p1-search-evidence-plan.md)
- Traditional Chinese companion: [`runtime-asset-p1-search-evidence.zh-tw.md`](runtime-asset-p1-search-evidence.zh-tw.md)

## Outcome

The offline pilot does not authorize an FTS5 production prototype or
integration. Hybrid retrieval showed useful directional quality with small
warm-latency overhead, but the predeclared decision gate failed on query
coverage and storage ratio. Production search therefore remains sqlite-vec
vector-only. Physical database reorganization, a second Asset Type, and
Dashboard renaming remain deferred.

## Frozen evidence

| Item | Result |
|---|---|
| Corpus | 196 canonical Assets; exact revision/content/source identities matched |
| Judged queries | 18 total; 9 lexical and 9 semantic; 31 positive qrel rows; required GO coverage is 80/30/30 |
| Query suite SHA-256 | `2969b1916b4fb07d38f605e6c46de991ee74bfd26e8c0e1bf5107cdb2397d6be` |
| Vector model | `all-MiniLM-L6-v2`; immutable local digest recorded |
| Index migration | `001_asset_index_state` exact checksum, applied |
| Source Index | 3,444,736 bytes; integrity `ok` |
| Source isolation | SHA-256, size, and mtime identical before and after |
| Disposable evidence | `.artifacts/p1-search/20260717T194521Z/` (ignored, local only) |

No Governance or Runtime database was opened or created. FTS5 DDL existed only
in the disposable `fts5-benchmark.db`; vector queries used an integrity-checked
SQLite backup.

## Quality

Binary judgments treat direct and useful-adjacent targets as relevant.

| Slice / nDCG@5 | sqlite-vec | FTS5 | Hybrid RRF |
|---|---:|---:|---:|
| Overall | 0.9018 | **0.9551** | 0.9459 |
| Lexical | 0.8528 | **0.9727** | 0.9412 |
| Semantic | **0.9507** | 0.9375 | **0.9507** |

Overall Recall@5 was `0.9444` for vector and `0.9722` for both FTS5 and hybrid.
Hybrid improved overall nDCG@5 by `+0.0442` and lexical nDCG@5 by `+0.0883`
versus vector without semantic regression. These are directional pilot results,
not a representative quality claim; FTS5 alone also outscored hybrid overall,
so a fusion prototype is not yet justified.

## Performance and storage

| Method | Warm p50 | Warm p95 |
|---|---:|---:|
| sqlite-vec | 22.82 ms | 28.99 ms |
| FTS5 | 2.81 ms | 3.96 ms |
| Hybrid RRF | 26.28 ms | 31.25 ms |

Hybrid added `2.25 ms` at p95 and stayed within both latency thresholds. FTS5
built in `90.56 ms`, but its 1,155,072-byte database was `33.53%` of the source
Index, exceeding the `25%` gate.

## Gate result

| Gate | Result |
|---|---|
| Complete exact 196-Asset projection | PASS |
| Source Index unchanged | PASS |
| Overall/lexical/semantic quality floors | PASS |
| Recall floor | PASS |
| Absolute and relative p95 latency | PASS |
| Representative query coverage | **FAIL — 18/9/9 below 80/30/30** |
| FTS5 storage ratio | **FAIL — 33.53% above 25%** |

The stable CLI exit was `5`, which is the expected non-success result for
`NO_GO_INSUFFICIENT_EVIDENCE`.

## Recommendation

Keep production vector-only. Reopen this candidate only after independent
judgment expands the suite to at least 80 queries with the required stratified
coverage and after a separately planned storage experiment reduces FTS5
overhead without changing the frozen relevance protocol. Any future run needs
new evidence; it must not relax these thresholds after observing results.
