# Governance Authority Gate B Fresh Reapproval Design v1

- 狀態：**Gate B 已實作並完成 RC independent review；production 仍受 production security policy gate 約束**
- 日期：`2026-07-21`
- Policy identifier：`governance.fresh-reapproval.v1`
- 前一個 gate：[`governance-authority-gate-a-design.md`](governance-authority-gate-a-design.md)
- Lifecycle contract：[`contracts/governance-authority-lifecycle-v1.json`](contracts/governance-authority-lifecycle-v1.json)
- 英文權威文件：[`governance-authority-gate-b-design.md`](governance-authority-gate-b-design.md)

## 決策與範圍

Gate B 採用 Gate A 中最安全的 no-migration 選項。Rejected current revision 永遠
不能直接 approve；復原流程必須建立 new current revision、重新完成 exact
binding，並產生該 revision 專屬的 scan、equivalence-test、review 與 decision
artifacts。不接受直接對 rejected revision 提交 fresh packet 的替代路徑。

本 batch 不改 Runtime authority tuple、不新增 table／column、不執行 physical
database migration、不加入 expiry／revocation／quorum、不 redesign Dashboard、
不啟用 real adapter，也不改寫 historical Runtime evidence。
本 implementation 不需要 schema 或 data migration。

## 強制順序

```text
reject R1
  -> register R2 as pending/unbound
  -> exact runtime_bind for R2 and its canonical artifact digest
  -> binding 後為 R2 寫入 non-blocking scan event + row
  -> binding 後為 R2 寫入 passing equivalence-test event + row
  -> approval transaction 內建立 authenticated review event
  -> 為 R2 建立 approve decision event
```

`approve_skill()` 在同一個 `BEGIN IMMEDIATE` transaction 強制此順序。Evidence
IDs 由 application 從 server-written audit events 解析，caller 不能選擇 scan／test
IDs。每個 evidence row 必須符合相同 Governance Skill 與 exact current revision；
binding audit event 的 `artifact_digest` 也必須等於 current digest。Missing、failed、
blocked、stale、pre-binding 或 cross-revision evidence 都會 fail closed，且不建立
approval 或 review event。

現有 authenticated Dashboard route 維持相容：request body 仍只有 `reason`，
reviewer 來自 JWT subject。Local CLI caller 位於 operator boundary；fresh
reapproval 時 database 要求 non-empty actor 與 reason。

## Revision reset contract

`register_revision()` 保存 historical rows，但會清除 new revision 的：

- artifact binding 與 approval actor／time；
- scan timestamp／version／risk／findings projections；
- equivalence timestamp／scores／pass projection；
- installed path／time workflow projection；
- inherited creation time、source checksum 與 provenance serialization。

New revision 從 `pending`、`risk_level=unknown`、unbound 開始，並依新 payload
重新計算 source checksum 與 provenance。Prior revisions、scan/test rows、
approval/rejection events 與 Runtime history 都不會被修改。

## Review 與 decision artifacts

Fresh reapproval 時，application 會在 approval 的同一 transaction 內建立
`review` audit event，記錄 exact revision、digest、binding event、scan ID、test
ID、reviewer 與 reason。後續 `approve` event 是 decision artifact，並透過
server-derived `fresh_reapproval` packet 引用該 review event。

Initial approval 維持 backward compatibility，不新增 post-rejection packet 要求。
對已 approved current revision 重複 approve 也保留現行行為。Rejected revision 的
identical binding 仍只是 idempotent no-op，不能繞過 direct-reapproval denial。

Generic revision-state helper 不能 approve 或 reject；唯一允許的 transition 是
application remediation 的 `blocked` to `pending`。Reset 後要 approve，必須在
reset 後重新寫入 non-blocking scan 與 passing test；block／reset 前的 evidence
不能恢復 authority。

## Retention 與 integrity boundary

Application code 沒有更新或刪除 historical revisions、scan/test evidence、audit
events 的路徑；Gate B workflow 只會 append 新 evidence。Operator 至少要在相關
Governance 與 Runtime evidence 的有效期間內保存這些 records，並把
`governance.db` 納入已驗證的 backup/restore policy。

本 no-migration batch **不**提供 database-level tamper resistance、cryptographic
chain，也不能阻止 out-of-band SQLite writer。這些仍是明確 gaps；若要實作，必須
另行核准 persistence design、migration、recovery rehearsal 與 rollback plan。
不得把 application append-only behavior 描述成 physical immutability。

## 驗證與 rollback

必要檢查包含：direct reapproval 與 generic-state bypass 零副作用拒絕、freshness state reset、拒絕
pre-binding evidence、missing/failed evidence、post-block reset evidence、R1-to-R2 positive sequence、exact
audit references、rejection／supersession／drift 後 Runtime denial、既有 stale-job
行為、full regression 與 independent review。

Rollback 是反向 code/document commit；不刪除或改寫 Gate B 啟用期間新增的
review／approval audit events。任何 unresolved Critical/Warning、partial write、
Runtime authority regression，或 database-level immutability 的錯誤宣稱，都是
stop condition。
