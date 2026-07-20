# Governance Authority Gate A Compatibility Design v1

- 狀態：**已 review 的設計；不授權實作**
- 日期：`2026-07-20`
- Decision proposal：[`governance-authority-lifecycle-proposal.md`](governance-authority-lifecycle-proposal.md)
- 現行 behavior：[`governance-authority-lifecycle.md`](governance-authority-lifecycle.md)
- 英文權威文件：[`governance-authority-gate-a-design.md`](governance-authority-gate-a-design.md)

## 目的與邊界

本 Gate A 文件定義 current-target enforcement 的 compatibility-only 實作形狀，並記錄 fresh reapproval 尚未決定的事項。它不授權 code change、不改 authority tuple、Runtime admission、Asset type、Dashboard design，也不允許 physical database migration。

Runtime authority 仍只來自 exact current approved Governance revision，以及相符的 canonical identity、artifact digest、version、approver、approval timestamp。Mutable projection、job、scan、Search、Knowledge、Evaluation 都不是 authority。

## 已驗證 baseline

- `approve_skill()` 已拒絕明確指定的 non-current revision。
- `reject_skill()` 與 `record_security_scan()` 仍接受 historical revision，且可能改變 `skills.status`，但不會改變 current Runtime authority。
- Dashboard action job 會保存 `target_revision_id`，但 scan execution 目前讀取執行當下的 current revision；retry 仍保存原 target。
- rejected current revision 可在沒有 new binding 或已定義 fresh-evidence packet 下重新 approve。
- Runtime create/resume 都會重新驗證 current exact authority；historical Runtime events 保持 append-only。

## A1 — current-target enforcement

在 `tools/governance_db.py` 新增一個 transaction-local private resolver。省略 `revision_id` 時，仍解析為 current revision，以維持 legacy caller；明確 target 若不是 current，必須在寫入 revision、projection、scan result、audit event 前 fail closed。

`reject_skill()`、authority-affecting `record_security_scan()` 與既有 `approve_skill()` 應共用此規則。Dashboard worker 必須把 job 保存的 `target_revision_id` 傳到 scan write。若 target 已 superseded，job 以 `STALE_TARGET_REVISION` 失敗，不得 retarget、更新 projection 或產生 successful scan evidence；retry 仍綁定原 target，operator 必須為新 revision 建立新 job。

Implementation batch 必須在改 public behavior 前，選定 explicit stale caller 的固定 mapping：domain exception、false result 或 structured service error。Gate A 不需要新增 HTTP request field；只有 service layer 無法容納 mapping 時，才考慮 router change，且不得 redesign UI。

### Candidate files

- `tools/governance_db.py`：current-target resolver 與 authority-affecting writes。
- `skill-0-dashboard/apps/api/services/governance.py`：傳遞 captured target，stale job 不 retarget。
- `skill-0-dashboard/apps/api/routers/skills.py`：只有需要 normalize response 時才修改。
- `tests/test_governance_revisions.py`、Dashboard API governance tests、`tests/test_runtime_api.py`：negative、retry、Runtime revalidation coverage。
- Lifecycle docs/JSON contract：只能與真正改變 verified behavior 的 implementation commit 同步更新。

## A2 — fresh reapproval preconditions

Gate A 不完整規範、也不授權 fresh reapproval。`decision_evidence` 目前只是 optional audit detail；identical binding 是 idempotent；new revision 也會繼承 scan/test projection。沒有 operator-defined evidence contract 時，這些事實無法證明 freshness。

最安全的 no-migration candidate 是：禁止 rejected current revision 直接 approve，要求 new revision、exact new binding，以及該 revision 專屬的新 evidence。但 Gate B 必須先決定 mandatory artifacts、digest linkage、revision registration 時需 reset 的欄位、retention/immutability，以及 reapproval 是否永遠需要 new revision，或可接受 authenticated fresh-evidence packet。

上述 decisions 完成前，direct reapproval 維持 documented gap，不得宣稱已 enforce fresh evidence。

## Implementation batch 的必要 negative tests

1. 對 explicit historical revision 執行 reject，或記錄 blocked security scan，不得改 revision、`skills.status`、scan record 或 audit event。
2. Queued scan 在 execution 前被 superseded，必須以 `STALE_TARGET_REVISION` 失敗；retry 不得 retarget。
3. 省略 revision identifier 的 caller 仍解析 current revision。
4. rejection、blocking、supersession、digest drift 後，Runtime create/resume 仍拒絕。
5. 若 Gate B 授權 fresh reapproval，rejected revision 不得直接 approve，且 new revision 不得繼承 freshness-sensitive evidence。

## Rollout 與 rollback

A1 應以單一、獨立 review 的 commit 實作，先跑 focused tests，再跑完整 Python/API regression。它不需要 schema/data migration；rollback 是反向 code commit，不改寫 Governance 或 Runtime history。

不得把 A1 與 fresh reapproval、expiry、revocation、quorum、cryptographic audit、FTS5、新 Asset type 或 Dashboard redesign 混入同一 batch。任何 unresolved Critical/Warning、stale-job ambiguity、partial-write test failure 或 Runtime regression 都是 stop condition。
