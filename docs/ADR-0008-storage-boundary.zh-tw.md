# ADR-0008 — Registry、Index 與 Runtime storage boundary

**狀態：** P0 已接受

## 決策

P0 建立三個邏輯 boundary，同時保留實體檔名：Registry 管理 Asset identity 與
approved revision；Index 是 `skills.db` 的 derived/disposable search projection；
Runtime `runtime.db` 保持 append-only execution evidence。

Repository 維持 SQLite-specific 且範圍狹窄。每個 unit of work 建立具名 policy
connection；migration 必須有順序、transaction 與 checksum；API import 絕不
自動 migrate operator database。

P0 在 `skills.db` 只允許新增 `schema_migrations` 與 `asset_index_state`，且必須先
preview、建立可驗證 backup，再通過 L3 checkpoint。Governance 與 Runtime 的
operator store 不執行 DDL。Index 絕不是 execution authority。

## Snapshot freshness

每個 process 持有一份 immutable、versioned corpus snapshot。Runtime create 或
resume 前必須檢查 live-corpus digest；不同時以 `stale_source_snapshot` fail
closed，只有 doctor 報告並不足夠。Authenticated reload 驗證完整 replacement
map 後 atomic swap。Ambiguous canonical ID 以 conflict 保存，不能任選其中一筆。

## Index-state lifecycle

Index identity 由 Asset ID、Asset revision ID、representation version、embedding
model ID/version 唯一決定，並綁定實際 `skills.id` 與 vector row。Vector mutation
和 state update 必須同一 transaction。Clear/reindex、filename reuse、source
disappearance、interrupted/orphan state 都要有明確處理與 doctor 分類。

實體 DB 改名、拆分、合併與 authority rows 搬移延後至 P1。Derived state 可重建；
operator DDL 若需 rollback，回復已驗證 backup，不原地 drop table。
