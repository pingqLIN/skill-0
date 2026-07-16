# Runtime 狀態機

> 本文件是 [runtime-state-machine.md](runtime-state-machine.md) 的繁體中文參考版本；英文原文為權威版本。

```text
CREATED -> PLANNED -> PREFLIGHT
  -> AWAITING_APPROVAL | READY | DENIED
AWAITING_APPROVAL -> READY（核准）| DENIED（拒絕）
READY -> ACTION_PREPARED -> ACTION_STARTED
ACTION_STARTED -> ACTION_SUCCEEDED | ACTION_FAILED | ACTION_OUTCOME_UNKNOWN
ACTION_OUTCOME_UNKNOWN -> RECONCILIATION_REQUIRED
ACTION_SUCCEEDED -> 下一個 action | VALIDATING -> SUCCEEDED
已有外部效果的已知失敗 -> RECOVERY_PENDING -> COMPENSATING
COMPENSATING -> COMPENSATED | HITL_REQUIRED
HITL_REQUIRED -> RECOVERY_PENDING（確認單一 action 已復原）| DENIED（拒絕）
```

## 當機語意

- 呼叫 adapter 前，以 `ACTION_PREPARED` 記錄 idempotency 所有權。
- `ACTION_STARTED` 後若沒有 action 終止事件，代表外部結果不明。
- 結果不明時必須進入 reconciliation，不可直接重試或補償。
- 執行下一個有副作用的步驟前，`ACTION_SUCCEEDED` 會保存 external resource ID 與最小必要復原資料。
- 只有 `RUN_COMPENSATED` 能證明所有待處理的自動補償已完成。

每次轉移都由 append-only event 表示；`runtime_runs.status` 只是最新相關事件的查詢投影。

## Human-in-the-loop 不變條件

- `APPROVAL_REQUIRED` event 與 pending queue item 必須在同一個 SQLite transaction 中提交。
- 決策要求已驗證 JWT 的 subject 同時存在於 server-side decision-actor allowlist，之後只記錄該 subject、allowlist 中的 decision，以及固定 reason code；request body 不能指定 actor 或 approved action IDs。
- 核准只把原 run 改成 `READY`，不會呼叫 adapter。
- Resume 沿用原本的 `run_id`、在同一原子操作提交一次性 item claim 與 `RUN_RESUME_STARTED`、重新計算 keyed execution basis，並跳過已有成功事件的 action。若 attempt 後沒有 durable outcome，則轉入 reconciliation。
- canonical skill、contract、input、preflight basis 或 action 順序只要改變，就不能重用核准。
- 只有 recovery coordinator 明確標記為可確認的人工復原邊界，才會建立 confirmation item。Confirmation 只關閉該 action；coordinator 必須處理完所有剩餘 candidate，才能產生 `RUN_COMPENSATED`。外部結果不明仍停在 `RECONCILIATION_REQUIRED`，不可拿 approval 取代 reconciliation。
- HITL decision 與 execution basis 都不可變；queue item status 是可更新的查詢投影。
