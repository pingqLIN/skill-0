# Runtime Asset P1 Search 實證決策

- 決策：**NO_GO**
- 日期：`2026-07-18`
- 範圍：本機 offline evidence；不構成 production security 或 integration clearance
- 計畫：[`../planning/runtime-asset-p1-search-evidence-plan.md`](../planning/runtime-asset-p1-search-evidence-plan.md)
- 英文權威版本：[`runtime-asset-p1-search-evidence.md`](runtime-asset-p1-search-evidence.md)

## 結果

擴充後的 representative evidence 不授權 FTS5 prototype 或 integration。Hybrid
retrieval 的 overall quality 有改善，但規則要求單一 profile 通過全部預先門檻。
所有 profiles 都超過 storage ceiling，lexical nDCG gain 也未達標；最小 profile
另超過 relative latency ceiling。因此 Runtime search 維持 sqlite-vec
vector-only；實體 DB 重整、第二種 Asset Type 與 Dashboard 改名繼續延後。

## 固定證據

| 項目 | 已驗證結果 |
|---|---|
| Corpus | 196 canonical Assets；196 exact index rows |
| Judged suite | 84 queries：lexical 42、semantic 42；120 qrels；85 direct targets；八個 taxonomies |
| Suite SHA-256 | `614c41967d6c45e6d07f9760414a153fecbdff7e9d59de5734f9f0dcd91ec18f` |
| Freeze manifest SHA-256 | `c355eb423448c52c4fa8198ede1ecaae88e27bb18a8bff183db61922791c24fe` |
| Freeze review | curator `agent:governance_authority_research`；reviewer `agent:p02_bootstrap_review`；量測前完成審核 |
| Source Index | 3,485,696 bytes；integrity `ok`；migration `001_asset_index_state` exact checksum 已套用 |
| Source isolation | SHA-256 `2266356996053850eb5c5619da0ae7a5e00bdd4fbf9c22b18b33504f555ef119`；執行前後 SHA、size、mtime 相同 |
| Disposable evidence | `.artifacts/p1-search/20260717T231233Z/`（ignored、僅本機） |

Harness 在 retrieval 前驗證 detached freeze manifest，查詢只使用通過 integrity
check 的 `vector-snapshot.db`；FTS5 DDL 只存在三個 disposable profile DB。
沒有 benchmark artifact 成為 authority source。

## Quality

三個 storage profiles 的 ranking 相同；binary judgments 將所有 positive qrels
視為 relevant。

| Slice / nDCG@5 | sqlite-vec | FTS5 | Hybrid RRF |
|---|---:|---:|---:|
| Overall | 0.8391 | 0.8843 | **0.8977** |
| Lexical | 0.8666 | 0.8920 | **0.9013** |
| Semantic | 0.8116 | 0.8766 | **0.8941** |

Overall Recall@5 從 `0.8889` 升至 `0.9306`。Semantic nDCG 與 overall
quality／recall floors 通過；lexical nDCG 僅提升 `0.0347`，低於預先固定的
`0.05`，因此所有 profiles 都未通過 lexical gain gate。

## Performance 與 storage

| FTS5 profile | Build | Bytes | Source ratio | Vector p95 | FTS5 p95 | Hybrid p95 | Gate |
|---|---:|---:|---:|---:|---:|---:|---|
| baseline | 83.40 ms | 1,155,072 | 33.14% | 32.67 ms | 4.65 ms | 32.98 ms | NO_GO |
| `detail=none` | 97.67 ms | 925,696 | 26.56% | 29.08 ms | 15.88 ms | 41.88 ms | NO_GO |
| `detail=none,columnsize=0` | 98.95 ms | 921,600 | 26.44% | 31.16 ms | 20.67 ms | 53.66 ms | NO_GO |

每個 byte count 都包含 embedded mapping。所有 profiles 未通過 `25%` storage
gate。Baseline 與 `detail=none` 通過兩個 latency gates；最小 profile 相對 vector
p95 增加 `22.50 ms`，但增幅 `72.21%`，超過 relative `50%` ceiling。

## Gate 決策

| Gate | 結果 |
|---|---|
| 已審核凍結 evidence 與 representative 84/42/42 coverage | PASS |
| 完整 exact 196-Asset projection | PASS |
| Source Index unchanged | PASS |
| Overall、semantic quality floors | PASS |
| Overall Recall floor | PASS |
| Lexical nDCG gain 至少 0.05 | **FAIL — 0.0347** |
| Hybrid p95 absolute/relative ceilings | 兩個 profiles PASS；**最小 profile 的 relative ceiling FAIL** |
| FTS5 artifact 不超過 25% | **FAIL — 全部 profiles；最佳 26.44%** |

Deterministic aggregate decision 是 `NO_GO`，沒有 selected profile。

## 建議

Runtime search 維持 vector-only，P1 不實作 FTS5。量測差距足以保留 reproducible
harness，但不應修改 frozen gates。只有新一輪、另行批准且在量測前提出具體
hypothesis 的 evidence cycle 才能重啟，例如改用不同 lexical representation，
同時改善 discriminative ranking 與 whole-file storage。不得以本 suite 調參後又把
同一 suite 當 unseen validation evidence。
