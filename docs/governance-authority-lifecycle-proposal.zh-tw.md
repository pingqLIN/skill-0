# Governance Authority Lifecycle Decision Proposal v1

- 狀態：**Gates A／B 已部分實作；其餘提案不授權實作**
- 日期：`2026-07-20`
- 現行 lifecycle：[`governance-authority-lifecycle.md`](governance-authority-lifecycle.md)
- Runtime boundary：[`ADR-0006-runtime-boundary.md`](ADR-0006-runtime-boundary.md)
- 英文權威文件：[`governance-authority-lifecycle-proposal.md`](governance-authority-lifecycle-proposal.md)

## 目的

本提案把已文件化的 Governance authority gaps 轉成明確的 operator decisions。它不改變 Runtime admission、不新增 Asset type、不啟用 resolver 或 real adapter、不擴張 Dashboard scope，也不授權 physical database migration。

現行 authority unit 仍是 exact current approved revision、bound canonical Asset identity、matching artifact digest、approver 與 approval timestamp；Runtime create/resume 持續重新驗證此 tuple。

## Decision boundary

以下仍未實作：approval expiry、專用 append-only revocation decision、quorum/separation of duties，以及 cryptographic Governance audit chain。在有經核准的實作關閉前，它們必須維持 gap 的描述。Gates A／B 已在沒有 schema migration 下實作 current-target enforcement 與 fresh reapproval。

| Decision | Candidate direction | 現況 | 需要的獨立授權 |
|---|---|---|---|
| Current-target enforcement | 對 approve/reject/scan/test write 強制 captured current target。 | **Gate A 已實作：** stale job 不寫 evidence/projection，且不可 retry。 | 完成；擴張需新的 focused review。 |
| Fresh reapproval | rejection 後要求 new exact bind 與 revision-scoped scan/test/review/decision evidence。 | **Gate B 已實作：** direct rejected-revision approval 被拒絕；database-level tamper resistance 仍不存在。 | Application enforcement 完成；physical immutability 需要獨立 persistence gate。 |
| Approval expiry | 為 approval 加入 explicit expiry rule，期滿後 Runtime admission fail closed。 | 沒有 renewal clock。 | Time semantics、operator policy、persistence design。 |
| Revocation | 新增專用 append-only revocation decision，在不改寫歷史下結束 authority。 | 現有只能靠 rejection、blocking、supersession、drift。 | Incident authority 與 persistence design。 |
| Quorum / separation of duties | 對 bind、evidence review、approval、emergency revoke 使用不同 authenticated roles。 | Actor separation 只是 deployment policy。 | Identity source 與 role governance decision。 |
| Audit chain | 將 Governance decisions 綁入可驗證 chain，保留既有 Runtime ledger boundary。 | `audit_log` 沒有 cryptographic chain。 | Retention、key custody、migration design。 |

## 必要的 operator decisions

實作前，authorized operator 必須決定並記錄：需納入下個 release boundary 的 lifecycle changes；expiry policy 與 clock uncertainty；approve/revoke/override actor 與 quorum；reapproval 所需的 fresh evidence 與 retention；以及是否准許 persistence changes。任何 data-model change 都需要獨立核准的 migration plan、backup/restore rehearsal 與 rollback procedure；本提案不授權上述任何一項。

缺少 decision 是 `UNKNOWN`，不是放寬 Runtime admission 或靜默保留 authority 的許可。

## 建議順序

1. **Gate A — compatibility-only implementation：** [`governance-authority-gate-a-design.md`](governance-authority-gate-a-design.md) 記錄已實作的 current-target enforcement；fresh-evidence semantics 因 evidence/retention rules 尚未決定，保留到 Gate B。
2. **Gate B — authority semantics decision：** [`governance-authority-gate-b-design.zh-tw.md`](governance-authority-gate-b-design.zh-tw.md) 已選定 reapproval mandatory new-revision fresh evidence，並明確延後 expiry、revocation、quorum、cryptographic chain 與 physical immutability。
3. **Gate C — migration and recovery decision：** 若 Gate B 需要新的 persisted lifecycle facts，另行提出 staged copy、integrity check、backup/restore、current-revision reconciliation、backward compatibility、rollback 的 migration proposal。獨立核准前不得開始 physical migration。
4. **Gate D — implementation batches：** 依 current-target、fresh reapproval、expiry、revocation、quorum、audit chain 拆成各自 batch；每個 batch 都要有 focused negative tests、Runtime create/resume tests、independent review 與可回復 commit。

## 不可放寬的 invariants

- ARD 保持 ternary，Evidence 維持 orthogonal。
- exact current Governance revision/artifact digest 仍是 Runtime admission authority；Search、Dashboard、Knowledge、Evaluation、mutable projections 不是 authority。
- Runtime events/decision history 保持 append-only，不得改寫來假裝 revocation、renewal、continuity。
- Runtime HITL approval 與 Governance authority 分離。
- 系統維持 `asset_type=skill`、dry-run-only、single-host、three-store。本提案不授權 FTS5 integration、Dashboard redesign、新 Asset type、real adapter 或 database migration。

## 未來實作的 acceptance evidence

未來 accepted batch 必須提供 exact before/after authority-state/audit-event tests（含 stale、non-current、rejected、blocked、drifted、expired）、每個 authority-ending event 後 Runtime create/resume denial tests、crash/retry failure-injection evidence、若儲存狀態改變則 backup/restore/doctor evidence、無 unresolved Critical/Warning 的 independent review，以及 legacy record/rollback behavior 的明確聲明。

在條件滿足前，lifecycle 文件與 Production Security Policy 仍是現況 behavior/gaps 的權威說明。
