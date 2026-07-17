# Runtime Asset P1 Search Evidence Decision

- Decision: **NO_GO**
- Date: `2026-07-18`
- Scope: local offline evidence; no production security or integration clearance
- Plan: [`../planning/runtime-asset-p1-search-evidence-plan.md`](../planning/runtime-asset-p1-search-evidence-plan.md)
- Traditional Chinese companion: [`runtime-asset-p1-search-evidence.zh-tw.md`](runtime-asset-p1-search-evidence.zh-tw.md)

## Outcome

The expanded representative evidence does not authorize an FTS5 prototype or
integration. Hybrid retrieval improved overall quality, but every predeclared
gate had to pass in one profile. All profiles exceeded the storage ceiling and
the lexical nDCG gain missed its floor; the smallest profile also exceeded the
relative latency ceiling. Runtime search therefore remains sqlite-vec
vector-only. Physical database reorganization, a second Asset Type, and
Dashboard renaming remain deferred.

## Frozen evidence

| Item | Verified result |
|---|---|
| Corpus | 196 canonical Assets; 196 exact index rows |
| Judged suite | 84 queries: 42 lexical, 42 semantic; 120 qrels; 85 direct targets; eight taxonomies |
| Suite SHA-256 | `614c41967d6c45e6d07f9760414a153fecbdff7e9d59de5734f9f0dcd91ec18f` |
| Freeze manifest SHA-256 | `c355eb423448c52c4fa8198ede1ecaae88e27bb18a8bff183db61922791c24fe` |
| Freeze review | curator `agent:governance_authority_research`; reviewer `agent:p02_bootstrap_review`; reviewed before measurement |
| Source Index | 3,485,696 bytes; integrity `ok`; migration `001_asset_index_state` applied with exact checksum |
| Source isolation | SHA-256 `2266356996053850eb5c5619da0ae7a5e00bdd4fbf9c22b18b33504f555ef119`; SHA, size, and mtime identical before and after |
| Disposable evidence | `.artifacts/p1-search/20260717T231233Z/` (ignored, local only) |

The harness validated the detached freeze manifest before retrieval. It queried
an integrity-checked `vector-snapshot.db`; FTS5 DDL existed only in three
disposable profile databases. No benchmark artifact became an authority source.

## Quality

The three storage profiles produced the same rankings. Binary judgments treat
all positive qrels as relevant.

| Slice / nDCG@5 | sqlite-vec | FTS5 | Hybrid RRF |
|---|---:|---:|---:|
| Overall | 0.8391 | 0.8843 | **0.8977** |
| Lexical | 0.8666 | 0.8920 | **0.9013** |
| Semantic | 0.8116 | 0.8766 | **0.8941** |

Overall Recall@5 rose from `0.8889` to `0.9306`. Semantic nDCG and the overall
quality/recall floors passed. Lexical nDCG improved by `0.0347`, below the
predeclared `0.05` floor, so every profile failed the lexical gain gate.

## Performance and storage

| FTS5 profile | Build | Bytes | Source ratio | Vector p95 | FTS5 p95 | Hybrid p95 | Gate |
|---|---:|---:|---:|---:|---:|---:|---|
| baseline | 83.40 ms | 1,155,072 | 33.14% | 32.67 ms | 4.65 ms | 32.98 ms | NO_GO |
| `detail=none` | 97.67 ms | 925,696 | 26.56% | 29.08 ms | 15.88 ms | 41.88 ms | NO_GO |
| `detail=none,columnsize=0` | 98.95 ms | 921,600 | 26.44% | 31.16 ms | 20.67 ms | 53.66 ms | NO_GO |

Mapping storage is embedded and included in every byte count. All profiles
failed the `25%` storage gate. Baseline and `detail=none` passed both latency
gates. The smallest profile added `22.50 ms` but `72.21%` over vector p95, so it
failed the relative `50%` ceiling.

## Gate decision

| Gate | Result |
|---|---|
| Reviewed frozen evidence and representative 84/42/42 coverage | PASS |
| Complete exact 196-Asset projection | PASS |
| Source Index unchanged | PASS |
| Overall and semantic quality floors | PASS |
| Overall Recall floor | PASS |
| Lexical nDCG gain at least 0.05 | **FAIL — 0.0347** |
| Hybrid p95 absolute/relative ceilings | PASS for two profiles; **FAIL relative ceiling for smallest profile** |
| FTS5 artifact no more than 25% | **FAIL — all profiles; best 26.44%** |

The deterministic aggregate decision is `NO_GO`, with no selected profile.

## Recommendation

Keep Runtime search vector-only and do not implement FTS5 in P1. The measured
gap is small enough to justify retaining the reproducible harness, but not
changing the frozen gates. Reopen only with a new, separately approved evidence
cycle that states a concrete hypothesis before measurement—for example, a
different lexical representation that improves discriminative ranking while
reducing whole-file storage. Do not tune against this suite and reuse it as
unseen validation evidence.
