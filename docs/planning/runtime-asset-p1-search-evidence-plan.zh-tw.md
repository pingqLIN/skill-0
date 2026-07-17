# Runtime Asset P1 Search 實證計畫

- 狀態：**僅核准離線 evidence**
- 日期：`2026-07-18`
- 決策範圍：FTS5 加 sqlite-vec retrieval evidence
- 英文權威版本：[`runtime-asset-p1-search-evidence-plan.md`](runtime-asset-p1-search-evidence-plan.md)

## 目標

以實測判斷 FTS5 加 sqlite-vec hybrid retrieval 是否值得另開 P1 prototype。
本輪不把 FTS5 加入 production schema 或 API，也不重新開啟實體 DB 重整、
第二種 Asset Type 或 Dashboard 改名。

## 隔離邊界

Benchmark 必須以 read-only 開啟 source Index，執行前後記錄 SHA-256，並在
ignored artifact directory 建立 disposable SQLite backup。FTS5 table 只能存在
該 backup；不得開啟 operator Governance 或 Runtime DB，也不得把 benchmark
artifact 當成 authority source。

## 固定實驗

- Corpus：全部 196 個 checked-in canonical Skill-backed Assets。
- Judgments：versioned query file 明列 relevant source paths，執行時解析成
  canonical Asset IDs；lexical 與 semantic subsets 分開報告。
- Vector baseline：現行 `all-MiniLM-L6-v2` sqlite-vec Asset search。
- Lexical baseline：對 title、description 與現有 `skill-text-v1`
  representation 執行 FTS5 BM25，固定 weights `8, 4, 1`。
- Hybrid：vector 與 FTS5 各取 top 20，以 equal-weight reciprocal-rank fusion
  `k=60`；同分依 canonical Asset ID 排序。
- Quality：binary `nDCG@5`、`MRR@5`、`Recall@5`。
- Performance：一次不計分 warm-up，加每 query 五次 warm runs；記錄 p50/p95、
  build duration 與 FTS5 storage bytes。

## 預先固定的決策門檻

只有下列條件全部成立，才可 **GO：另開 P1 prototype**，但絕不等於直接
production integration：

1. 所有 judgments 都可解析、196 Assets 全數納入、source Index hash 不變；
2. hybrid overall nDCG@5 不低於 vector 超過 `0.01`，且 lexical subset 至少提升
   `0.05`；
3. semantic subset nDCG@5 不低於 vector 超過 `0.02`，overall Recall@5 不低於
   vector 超過 `0.02`；
4. hybrid p95 相對 vector 最多增加 `25 ms` 且最多 `50%`；
5. FTS5 artifact 增量最多是 source Index size 的 `25%`；
6. benchmark、focused tests、完整 Python regression、文件、artifact 與 secret
   gates 全部通過。

任何一項失敗即 **NO-GO**。GO 只授權後續另提 reviewed prototype plan，不授權
production DDL 或 API 變更。

## 批次

1. 固定 plan、query judgments、deterministic scoring contract 與 unit tests。
2. 在 disposable directory 執行 benchmark 並保存 machine-readable evidence。
3. 審查結果完整性、產出英文權威決策報告與繁中 companion，再跑整合驗證。

## Rollback

刪除或封存 ignored disposable benchmark directory；若不保留 harness，可 revert
research commits。Source Index 全程 read-only，production schema 未變，不需要
operator data rollback。
