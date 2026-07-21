# Runtime Asset P1 Search 實證計畫

- 狀態：**已執行 — NO_GO**
- 日期：`2026-07-18`
- 決策範圍：FTS5 加 sqlite-vec retrieval evidence
- 英文權威版本：[`runtime-asset-p1-search-evidence-plan.md`](runtime-asset-p1-search-evidence-plan.md)

## 目標

以實測判斷 FTS5 加 sqlite-vec hybrid retrieval 是否值得另開 P1 prototype。
本輪不把 FTS5 加入 production schema 或 API，也不重新開啟實體 DB 重整、
第二種 Asset Type 或 Dashboard 改名。

## 隔離與審核邊界

Benchmark 以 read-only 開啟 source Index，執行前後記錄 SHA-256，查詢只使用
通過 integrity check 的 disposable copy。每個 FTS5 profile 都位於獨立的
ignored artifact DB；不開啟或建立任何 Governance／Runtime authority DB。

擴充 suite 的 curator 只使用 Asset metadata。第二位 agent 在任何 retrieval
量測前完成審核並凍結 judgments。Harness 在建庫或搜尋前，必須驗證 detached
freeze manifest、suite digest、corpus snapshot、counts、taxonomy 與精確 profile
options。

## 固定實驗

- Corpus：全部 196 個 canonical Skill-backed Assets。
- Suite：84 queries，lexical／semantic 各 42，共 120 qrels、85 個 distinct
  direct targets、八個 taxonomy groups。
- Vector baseline：現行 `all-MiniLM-L6-v2` sqlite-vec Asset search。
- Lexical baseline：title、description 與 `skill-text-v1` representation 的
  FTS5 BM25，固定 weights `8, 4, 1`。
- Hybrid：vector 與 FTS5 各取 top 20，以 equal-weight reciprocal-rank fusion
  `k=60`；同分依 canonical Asset ID 排序。
- Profiles：FTS5 baseline、`detail=none`、`detail=none,columnsize=0`；每個
  artifact 都包含 mapping storage。
- Quality：binary `nDCG@5`、`MRR@5`、`Recall@5`，分 overall、lexical、
  semantic 報告。
- Performance：一次不計分 warm-up，加每 query 五次 warm runs；記錄 p50/p95、
  build duration 與整個 DB bytes。

## 預先固定的決策門檻

只有單一 profile 同時滿足下列所有條件，才可 **GO：另開 P1 prototype**；
絕不等於直接 production integration：

1. 所有 judgments 可解析、196 Assets 全數納入、suite 已審核凍結、source
   Index hash 不變；
2. 至少 80 judged queries，lexical、semantic 各至少 30；
3. hybrid overall nDCG@5 不低於 vector 超過 `0.01`，且 lexical subset 至少
   提升 `0.05`；
4. semantic subset nDCG@5 不低於 vector 超過 `0.02`，overall Recall@5 不低於
   vector 超過 `0.02`；
5. hybrid p95 相對 vector 最多增加 `25 ms` 且最多 `50%`；
6. 完整 FTS5 artifact 最多是 source Index size 的 `25%`；
7. benchmark integrity、focused tests、完整 regression、文件 gates、reviews
   與 scoped secret checks 全部通過。

任何 technical gate 失敗即 `NO_GO`；coverage 或 review/freeze evidence 不足則為
`NO_GO_INSUFFICIENT_EVIDENCE`。只能從全數通過 gate 的 profiles 選最小 artifact；
最終 source isolation 失敗可覆寫所有 profile 結果。

## 批次

1. curator 不看 retrieval，擴充 judgments；第二位 agent 獨立審核。
2. 凍結 suite、detached manifest、profiles、scoring contract 與 fail-closed tests。
3. 對凍結輸入只執行一次 disposable benchmark。
4. 獨立審查結果，產出英文權威報告與繁中 companion，再跑整合驗證。

## Rollback

刪除或封存 ignored benchmark directory；若不保留 harness，可 revert research
commits。Authority data 與 production schemas 未變，不需要 operator data rollback。

## 執行結果

固定的 84-query run 回傳 `NO_GO`。三個 profiles 全部未通過 `25%` storage gate，
最佳 ratio 為 `26.44%`；hybrid lexical nDCG@5 僅提升 `0.0347`，低於 `0.05`
門檻；最小 profile 另未通過 relative p95 latency gate。Production 維持
vector-only。詳見
[`../reports/runtime-asset-p1-search-evidence.zh-tw.md`](../reports/runtime-asset-p1-search-evidence.zh-tw.md)。
