# Runtime Asset P1 Search 實證決策

- 決策：**NO_GO_INSUFFICIENT_EVIDENCE**
- 日期：`2026-07-18`
- 計畫：[`../planning/runtime-asset-p1-search-evidence-plan.md`](../planning/runtime-asset-p1-search-evidence-plan.md)
- 英文權威版本：[`runtime-asset-p1-search-evidence.md`](runtime-asset-p1-search-evidence.md)

## 結果

此 offline pilot 不授權 FTS5 production prototype 或 integration。Hybrid
retrieval 呈現有用的方向性 quality，warm latency overhead 也很小，但預先固定的
query coverage 與 storage ratio gate 失敗。因此 production search 維持
sqlite-vec vector-only；實體 DB 重整、第二種 Asset Type 與 Dashboard 改名仍延後。

## 固定證據

- Corpus：196 canonical Assets，revision／content／source identities 完全相符。
- Judgments：18 queries，lexical 9、semantic 9，共 31 positive qrel rows；GO
  門檻為 80／30／30。
- Source Index：3,444,736 bytes、integrity `ok`；執行前後 SHA-256、size、mtime
  全部相同。
- Index migration：`001_asset_index_state` exact checksum 已套用。
- Vector model：`all-MiniLM-L6-v2`，machine evidence 記錄 immutable digest。
- Ignored local evidence：`.artifacts/p1-search/20260717T194521Z/`。

未開啟或建立 Governance／Runtime DB。FTS5 DDL 只存在 disposable
`fts5-benchmark.db`；vector query 使用通過 integrity check 的 SQLite backup。

## Quality

| Slice / nDCG@5 | sqlite-vec | FTS5 | Hybrid RRF |
|---|---:|---:|---:|
| Overall | 0.9018 | **0.9551** | 0.9459 |
| Lexical | 0.8528 | **0.9727** | 0.9412 |
| Semantic | **0.9507** | 0.9375 | **0.9507** |

Overall Recall@5：vector `0.9444`，FTS5 與 hybrid 都是 `0.9722`。Hybrid
相對 vector 的 overall nDCG@5 提升 `+0.0442`、lexical 提升 `+0.0883`，且
semantic 未退步。不過這只是 pilot direction，不能當成 representative quality
claim；FTS5 單獨的 overall 結果也高於 hybrid，尚不足以證明 fusion prototype。

## Performance、storage 與 gate

| Method | Warm p50 | Warm p95 |
|---|---:|---:|
| sqlite-vec | 22.82 ms | 28.99 ms |
| FTS5 | 2.81 ms | 3.96 ms |
| Hybrid RRF | 26.28 ms | 31.25 ms |

Hybrid p95 只增加 `2.25 ms`，latency gates 通過。FTS5 build 為 `90.56 ms`；
但 1,155,072-byte DB 是 source Index 的 `33.53%`，超過 `25%` gate。

PASS：完整 196-Asset exact projection、source unchanged、quality floors、Recall、
absolute/relative latency。FAIL：query coverage `18/9/9 < 80/30/30`，storage
`33.53% > 25%`。CLI 依契約回傳 exit `5`／
`NO_GO_INSUFFICIENT_EVIDENCE`。

## 建議

Production 維持 vector-only。只有在獨立 judgment 將 suite 擴充至至少 80 queries
並符合分層門檻，以及另行規劃的 storage experiment 能在不改變 frozen relevance
protocol 下降低 FTS5 overhead 後，才重新開啟此候選。不得看到結果後放寬門檻。
