# Runtime v4 執行計畫

> 本文件是 [runtime-v4-execution-plan.md](runtime-v4-execution-plan.md) 的繁體中文參考版本；英文原文為權威版本。

## 目標成果

Runtime v4 把既有 ARD/runtime contract 轉成真實但僅限 dry-run 的執行介面，具備 deterministic evidence、durable human approval、精確 governance admission，以及 fail-closed production 維運契約。真正有外部副作用的 adapter 不在本計畫範圍內。

## 已交付批次

| Batch | 範圍 | 驗收證據 | Commit |
|---|---|---|---|
| A | 真實 run creation；只接受 test adapter 與 `dry_run=true` | Runtime contract/API tests | `58b2c06` |
| B | Deterministic event/evidence projection | Evidence schema 與 replay tests | `c7b7ce3` |
| C | Durable、action-scoped HITL、same-run resume、recovery/reconciliation | Concurrency、crash-gap、immutable decision tests | `ae2ec39` |
| D | 精確 current-revision governance admission 與 Runtime dashboard | 356 Python/API tests、34 web tests、production build、獨立 reviewer | `5c8e7ee` |
| E | Production storage、deadline、doctor、backup/restore/restart rehearsal 與 release gate | 365 Python/API tests、34 web tests、production build、Compose config、WSL 三庫 restore rehearsal、獨立 reviewer | 本 commit |

## Batch E 工作包

1. Runtime ledger 使用獨立持久化 volume，Core API 以唯讀方式掛載 governance DB。
2. 強制 production WAL、binding key 與 JWT key 分離、明確 decision actor，以及有上下限的 HITL TTL。
3. Pending 與已核准但未消耗的 HITL item 到期失效，不改寫歷史 decision。
4. Backup/health workflow 從兩庫擴充為三庫。
5. 增加唯讀 production doctor 與要求近期備份的 release gate。
6. 在隔離 Compose project 演練三庫 backup/restore 可讀性與 Core API restart persistence。
7. 執行完整 backend/frontend regression、production build、Compose static check 與獨立 review。

## Release 判定

Batch E 通過後，Runtime v4 可進入內部 dry-run pilot，但不代表可做真實外部寫入。後續 adapter certification 必須另行定義 credential、least privilege、idempotency、reconciliation probe、compensation evidence、rate limit 與逐 adapter 的 production approval。

完整 container build/rehearsal 仍是 operator acceptance item：本驗證環境沒有可重用的 Skill-0 image，而下載新的 image/dependency layer 超出已授權邊界。Compose rendering、script parser、本機三庫 rehearsal 與 reviewer gate 已通過；不可把尚未執行的 container build 描述成完成。

## Batch E 後的建議下一步

使用一個 canonical skill 與 test adapter 執行受控內部 pilot：

1. 把精確 parsed artifact 綁定目前 governance revision 並核准。
2. 建立會在單一 action approval 暫停的 dry run。
3. 在 Dashboard 記錄 decision，短暫等待後明確 resume 同一 run，再檢查 evidence。
4. 另測一次 expired approval，以及一次模擬 ambiguous outcome。
5. 保存 evidence summary 與 operator observation；暫不啟用真實 adapter。

下一份工程提案應聚焦 adapter certification，而不是擴大 autonomous execution。
