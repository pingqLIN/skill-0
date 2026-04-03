# Governance P1 Async Job And Retry Spec

Updated: `2026-04-03`
Implementation status: `🟢 Implemented through DB-backed durable MVP on 2026-04-03`
Scope: `skill-0-dashboard/apps/api governance scan/test actions`

Status note: The dashboard API now exposes async batch scan/test job endpoints, persists job/item state into `governance.db`, supports manual retry flows, and re-enqueues unfinished queued/running work during service startup. Treat this document as the design record plus the remaining hardening gap list beyond the durable MVP.

## 1. Purpose

本文件把 `docs/planning/governance-phase2-pending.md` 中尚未落地的 P1 項目，收斂成可直接實作的規格：

1. 批次 `scan/test` 非同步化
2. retry 機制
3. 與現有 `ActionReadiness` / `ActionResult` / revision-aware governance 的相容策略

這份規格不直接引入外部 queue 基礎設施，而是先定義一版可在現有 FastAPI + governance DB 架構上實作的最小可用方案。

## 2. Current Baseline

截至 `2026-03-31`，現況如下：

1. 單技能 `scan/test` 已可同步執行。
2. 批次 `run_scan_batch()` / `run_test_batch()` 仍為同步迴圈。
3. API `POST /api/skills/scan`、`POST /api/skills/test` 目前直接返回最終 `ActionResult`。
4. 前端 hooks `useTriggerScan()` / `useTriggerTest()` 只支援單技能同步結果。
5. revision-aware governance 已存在，因此 batch job 的結果必須繫結到當時的 target revision，而不是模糊地繫在 skill latest row。

## 3. Problem Statement

目前 batch 行為有三個主要問題：

1. 一次處理多個技能時，請求生命週期過長，容易 timeout。
2. 當單一項目失敗時，沒有標準化 retry 模型。
3. UI 與 audit 無法區分「工作已排入」、「工作執行中」、「部分失敗但可重試」。

## 4. Goals

P1 要達成的是：

1. 批次操作改為 enqueue-first。
2. API 先回 `job_id`，由前端輪詢 job 狀態。
3. job 與 item 結果具 revision traceability。
4. failed item 可做單項 retry 或 job 級 retry。
5. 保留單技能同步入口，避免一次性破壞現有 UI/測試。

## 5. Non-Goals

本階段不做：

1. Redis / Celery / 外部 broker 佈署。
2. 跨 process / 跨 machine 的分散式 worker 保證。
3. 任意複雜優先權排程。
4. 取代現有單技能同步 action。

## 6. Proposed Execution Model

### 6.1 Job types

- `scan_batch`
- `test_batch`

### 6.2 Job statuses

- `queued`
- `running`
- `completed`
- `completed_with_failures`
- `failed`
- `cancelled`

### 6.3 Item statuses

- `queued`
- `running`
- `succeeded`
- `failed`
- `skipped`
- `retrying`

### 6.4 Retry policy

預設只 retry `runtime/transient` 類錯誤，不 retry 明確配置錯誤：

- 可 retry：
  - `SCAN_RUNTIME_ERROR`
  - `TEST_RUNTIME_ERROR`
  - 未分類但被標註為 transient 的 worker failure
- 不 retry：
  - `PATH_NOT_FOUND`
  - `SOURCE_PATH_MISSING`
  - `SOURCE_PATH_NOT_ALLOWED`
  - `INSTALLED_PATH_MISSING`
  - `INSTALLED_PATH_NOT_ALLOWED`

預設 retry policy：

- `max_attempts = 2`
- backoff: `immediate` for manual retry, `5s` for automated retry
- automated retry 預設關閉；P1 先支援 manual retry 與 schema-ready policy 欄位

## 7. API Contract

### 7.1 Keep existing synchronous endpoints

保留現有：

- `POST /api/skills/scan?skill_id=...`
- `POST /api/skills/test?skill_id=...`

這兩條仍回 `ActionResult`，作為單技能即時操作路徑。

### 7.2 New async batch endpoints

新增：

- `POST /api/skills/scan-jobs`
- `POST /api/skills/test-jobs`

request body:

```json
{
  "skill_ids": ["claude__local__example_a", "claude__local__example_b"],
  "selection_mode": "explicit",
  "requested_by": "reviewer",
  "max_attempts": 2
}
```

response:

```json
{
  "job_id": "job_scan_20260331_001",
  "job_type": "scan_batch",
  "status": "queued",
  "queued_items": 2
}
```

### 7.2.1 Authorization rules

P1 建議明確限制以下權限邊界：

1. 只有已驗證且具 reviewer / admin 權限的使用者可建立 batch job。
2. 一般登入使用者若無治理權限，不可呼叫 `scan-jobs` / `test-jobs` / retry endpoints。
3. job status 至少需 reviewer 權限可讀；若未來引入 multi-tenant actor，還需再補 owner visibility rule。

若 P1 尚未導入細緻 RBAC，最低要求也要在文件與 router guard 中標明「governance-authenticated only」。

### 7.3 Job status endpoints

新增：

- `GET /api/skills/action-jobs/{job_id}`
- `GET /api/skills/action-jobs/{job_id}/items`

`GET /api/skills/action-jobs/{job_id}` response sketch:

```json
{
  "job_id": "job_scan_20260331_001",
  "job_type": "scan_batch",
  "status": "running",
  "requested_by": "reviewer",
  "queued_at": "2026-03-31T10:00:00Z",
  "started_at": "2026-03-31T10:00:02Z",
  "completed_at": null,
  "summary": {
    "total": 12,
    "queued": 4,
    "running": 1,
    "succeeded": 6,
    "failed": 1,
    "retrying": 0,
    "skipped": 0
  }
}
```

### 7.4 Retry endpoints

新增：

- `POST /api/skills/action-jobs/{job_id}/retry-failures`
- `POST /api/skills/action-jobs/{job_id}/items/{item_id}/retry`

規則：

1. 只允許對 `failed` items 觸發 retry。
2. 若 error code 屬於 non-retriable，API 回 `409`.
3. retry 需建立新的 job item attempt，不覆寫舊紀錄。

## 8. Data Model

建議新增兩張資料表：

### 8.1 `governance_action_jobs`

欄位：

- `job_id`
- `job_type`
- `status`
- `requested_by`
- `selection_mode`
- `requested_payload_json`
- `max_attempts`
- `queued_at`
- `started_at`
- `completed_at`
- `error_code`
- `error_message`

### 8.2 `governance_action_job_items`

欄位：

- `item_id`
- `job_id`
- `skill_id`
- `target_revision_id`
- `action_type`
- `status`
- `attempt_number`
- `max_attempts`
- `started_at`
- `completed_at`
- `result_json`
- `error_code`
- `error_message`
- `retry_of_item_id`

關鍵原則：

1. `target_revision_id` 在 enqueue 時即凍結。
2. job item 不應在執行時改綁到更新的 revision。
3. retry 產生新的 item row，但保留 `retry_of_item_id` 關聯。

## 9. Worker Model

P1 建議採用 repo 內可先落地的 worker 模型：

1. API enqueue job
2. 背景 worker loop 撈取 `queued` job items
3. 逐項執行現有 `run_scan()` / `run_test()` 的核心能力
4. 寫回 item 結果與 job summary

最小實作建議：

- 使用 `asyncio.create_task()` 啟動單 process background runner
- 實際重工作業用 `asyncio.to_thread()` 包裝，避免阻塞 event loop
- 僅保證單 instance 可靠；多 instance 情境列為 P2+

### 9.1 Single-instance safety rules

即使 P1 只支援單 instance，也要先定義最小安全規則：

1. worker 取 item 時必須先做原子狀態轉移：`queued -> running`。
2. 同一個 `item_id` 在同一時間只允許一個 runner 持有。
3. 若 process restart 時留下 `running` item，系統啟動後需把它們回收為：

## 10. Outcome Note (`2026-04-02`)

Implemented in the dashboard API MVP:

1. `POST /api/skills/scan-jobs`
2. `POST /api/skills/test-jobs`
3. `GET /api/skills/action-jobs/{job_id}`
4. `GET /api/skills/action-jobs/{job_id}/items`
5. `POST /api/skills/action-jobs/{job_id}/retry-failures`
6. `POST /api/skills/action-jobs/{job_id}/items/{item_id}/retry`

Current implementation characteristics:

- job state is persisted in `governance.db` via durable job / item tables
- background execution still uses an in-process daemon thread runner
- workers now atomically claim `queued/retrying` items from DB before execution, so duplicate item execution is blocked even if multiple API instances start runners for the same job
- service startup recovers unfinished `queued/running` jobs and re-enqueues incomplete items
- job items freeze `target_revision_id` at enqueue time when available
- manual retry allowed only for retriable failure codes
- existing synchronous `POST /api/skills/scan` and `POST /api/skills/test` remain unchanged

Still not implemented from the original design:

- full lease / heartbeat policy for long-running items
- automated retry backoff worker policy
- actor/RBAC refinement beyond existing authenticated dashboard access
- richer telemetry, cancellation semantics, and queue prioritization

Validated with:

```bash
.venv/bin/python -m pytest skill-0-dashboard/apps/api/tests/test_governance.py skill-0-dashboard/apps/api/tests/test_skills.py -q
```
   - `queued`，若無任何完成證據
   - 或 `failed` + `error_code=WORKER_ABORTED`，若要保守處理
4. job summary 重建時以 item table 為 source of truth，不信任記憶體中的暫存狀態。

P1 建議採用第 3 種中的保守版本：

- restart recovery: `running -> failed(WORKER_ABORTED)`
- reviewer 可透過 retry endpoint 重新排入

## 10. UI Contract

前端新增需求：

1. 單技能操作維持既有 UX。
2. 批次操作改為：
   - submit job
   - 取得 `job_id`
   - poll `GET /api/skills/action-jobs/{job_id}`
   - 顯示 job summary / failed items / retry CTA
3. Skill detail 若屬於 batch job 來源，可顯示 latest related job item 狀態。

建議新增型別：

- `ActionJobSummary`
- `ActionJobItem`
- `ActionJobSubmitResult`

## 11. Error Semantics

job-level 失敗代表：

1. enqueue 失敗
2. worker 無法啟動
3. job summary 組裝失敗

item-level 失敗代表：

1. 該技能執行失敗
2. 其他 items 不一定失敗

因此：

- job `completed_with_failures` 應是常態化可接受狀態，不應被視為系統錯誤
- UI 與文件不得把 `partial` 與 infrastructure failure 混為一談

## 12. Tests

最小測試矩陣：

1. enqueue batch job returns `job_id`
2. job status transitions `queued -> running -> completed`
3. job status transitions `queued -> running -> completed_with_failures`
4. item retry creates new attempt row
5. non-retriable error returns `409`
6. `target_revision_id` is frozen at enqueue time
7. single-skill sync endpoints remain backward compatible
8. unauthorized caller cannot submit batch job
9. restart recovery converts orphaned `running` item to deterministic terminal state

## 13. Suggested Delivery Order

1. schema / response model additions
2. DB migration for jobs + items
3. enqueue + status read API
4. background worker loop
5. retry endpoints
6. frontend polling + status UI
7. integration tests and docs refresh
