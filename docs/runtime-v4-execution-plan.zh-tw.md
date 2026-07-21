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
| E | Production storage、deadline、doctor、backup/restore/restart rehearsal 與 release gate | 365 Python/API tests、34 web tests、production build、完整三庫 Compose rehearsal、獨立 reviewer | `1021d8e`、`c95f2b3` |
| F | 單一 adapter certification contract 與 fail-closed production admission | 七類隔離 probes 加 focused Runtime regression；人工 production approval 尚未核發 | `8e24d61` |

## Batch E 工作包

1. Runtime ledger 使用獨立持久化 volume，Core API 以唯讀方式掛載 governance DB。
2. 強制 production WAL、binding key 與 JWT key 分離、明確 decision actor，以及有上下限的 HITL TTL。
3. Pending 與已核准但未消耗的 HITL item 到期失效，不改寫歷史 decision。
4. Backup/health workflow 從兩庫擴充為三庫。
5. 增加唯讀 production doctor 與要求近期備份的 release gate。
6. 在隔離 Compose project 演練三庫 backup/restore 可讀性與 Core API restart persistence。
7. 執行完整 backend/frontend regression、production build、Compose static check 與獨立 review。

## Release 判定

Runtime v4 已於 2026-07-17 通過 operator acceptance 與受控內部 dry-run pilot。完整 production image build 與隔離 Compose rehearsal 已驗證 service health、production doctor、三個 SQLite store、online backup/restore，以及 API restart 後的 Runtime persistence。最終 regression 通過 365 項 Python/API tests、34 項 web tests、production web build 與全部 196 個 canonical schema 驗證。

此結果不代表可做真實外部寫入。Batch F 已針對單一 `skill0.local-pdf-filesystem` candidate 定義 credential-free least privilege、end-to-end idempotency-key delivery、reconciliation、可回復 compensation evidence、rate limit，以及簽署的逐 adapter／逐 environment production admission。Technical certification 已通過，但尚未簽發人工 production approval。

Batch F verification 通過 373 項 Python/API tests、34 項 web tests、production web build、全部 196 個 canonical schema 驗證，以及七類隔離 adapter probes。

## Production Admission Phase 1 完成狀態

Production Admission 的 Phase 1 實作已於 2026-07-21 完成。Commit
`167f23f` 新增具備簽章、精確發布版本綁定與 fail-closed 特性的 admission
package verifier（准入套件驗證器），並包含對應 schema（結構描述）、operator
handoff（操作員交接）、recovery（復原）文件及直接的回歸測試覆蓋。

本次完成閘門已通過 16 項 admission 專項測試、完整 571 項 Python/API
回歸測試、frontend lint（前端程式碼檢查）、36 項前端測試、production web
建置，以及 bundle-size guard（套件大小閘門）。Canonical parsed corpus
（標準解析語料庫）仍須持續遵守專案的 schema validation gate（結構描述驗證閘門）。

此處的完成狀態僅涵蓋 Phase 1 的 contract（契約）、verifier（驗證器）、文件與
測試介面。Production Admission 仍為 `WAITING_FOR_OPERATOR_EVIDENCE`：本次
驗證未使用或授權任何真實 operator evidence（操作員證據）、特定環境的人工核准、
credential（憑證）、external write（外部寫入）、service start（服務啟動）、
deployment（部署）或 public exposure（公開暴露）。

## 內部 pilot 結果與下一步

受控 pilot 使用 canonical PDF skill 的 `a_006` 建檔 action、test adapter 與 `dry_run=true`：

1. 精確 parsed artifact 已綁定目前 governance revision 並完成核准。
2. bounded-write action 在 action-scoped approval 暫停；Dashboard decision 記錄後，明確 resume 同一 run，最終為 `succeeded`，並產生 11-event evidence stream。
3. 以 process-local clock 推進模擬第二個 approval 到期；decision 被拒絕，且未留下 decision record。
4. 模擬 `action_started` 後 timeout，正確產生 `action_outcome_unknown` 與 `reconciliation_required`，沒有自動重試。
5. Evidence 與 operator observation 已保存於本機 ignored audit artifact；未啟用真實 adapter、外部 credential 或外部寫入。

Certification contract 與隔離 candidate 已完成實作，詳見 [adapter-certification.zh-tw.md](adapter-certification.zh-tw.md)。下一個 gate 是帶有 OS identity 與 ACL evidence 的 environment-specific human approval，再進入另行核准的 loader/rehearsal batch。在此之前，`/api/runs` 仍只接受 test adapter 與 `dry_run=true`。
