# Governance Authority Lifecycle v1

- 狀態：**已接受的 stable-foundation authority model**
- 版本：`1.2.0`
- 生效日期：`2026-07-21`
- Machine-readable lifecycle：[`contracts/governance-authority-lifecycle-v1.json`](contracts/governance-authority-lifecycle-v1.json)
- Runtime admission：[`runtime-governance.md`](runtime-governance.md)
- 英文權威文件：[`governance-authority-lifecycle.md`](governance-authority-lifecycle.md)

## 1. 目的

本文件定義 Governance revision 何時具有 Runtime admission authority、authority 如何開始與結束，以及哪些 records 只是 evidence 而非 authority。它把現有 implementation 文件化為 stable foundation；不建立新的 database lifecycle，也不授權 physical migration。

## 2. Evidence state

### VERIFIED implementation

- `skills.skill_id` 是 Governance identity；`skills.canonical_skill_id` 是連到 canonical Skill Asset identity 的 unique binding。
- `skills.current_revision_id` 選定一筆 current `skill_revisions` row。
- 新 revision 成為 current 時使用 `status=pending`，並清除其 Runtime artifact binding 與 approval provenance。
- Runtime artifact binding 只允許 pending current revision，並記錄 exact canonical artifact digest。
- Approval 需要 canonical identity 與 artifact digest，並把 current revision 更新為 `status=approved`、`approved_by`、`approved_at`。
- Runtime admission 讀取 current revision 與 exact digest；不把 mutable `skills.status` projection 當成 authority source。
- Create 與 resume 都重新評估 Governance。Supersession、current-revision rejection 或 blocking、missing provenance 或 artifact drift 都拒絕 admission。
- `approve_skill()` 會拒絕 rejected current revision。Fresh reapproval 必須建立 new pending revision、重新 exact bind、在 binding 後寫入 non-blocking scan 與 passing equivalence-test events，並在同一 transaction 建立 authenticated review 與 approval decision packet。
- Register new revision 會清除 scan、test、risk、approval、binding 與 installation workflow projections；historical revisions 與 evidence rows 保持不變。
- Approve、reject、security scan 與 equivalence test write 都在同一 write transaction 解析 exact current revision。Explicit stale target 會在任何 revision、projection、evidence 或 audit write 前失敗。
- Dashboard scan/test job 會把 captured `target_revision_id` 保留到 execution。Superseded job 以 `STALE_TARGET_REVISION` 失敗且不可 retry；operator 必須為 current revision 建立新 job。
- Governance decisions 追加到 `audit_log`；Runtime decisions 與 execution history 留在獨立 Runtime ledger。

### INFERRED stable interpretation

- Approval 的 authority 只屬於一個 exact tuple，不屬於 mutable Skill name 或所有 future revisions。
- Register 新 revision 會終止舊 revision 的 authority，即使舊 approval fields 為 audit 保留。
- Current revision 被 reject 或 block 會終止 admission authority，但不刪除 revision 或改寫 prior Runtime evidence。
- Canonical payload drift 形成 derived `drifted` condition；即使 stored row 未改 state，Runtime admission 仍必須 fail closed。

### UNKNOWN / current gaps

- Governance approval 尚無 implemented expiry 或 renewal clock。
- 沒有專用 append-only `revoked` decision type；目前 authority 由 rejection、blocking、supersession 或 exact admission failure 結束。
- Actor separation-of-duties 與 quorum 是 deployment policy，目前 schema 未強制。
- `skills.status` 與 revision status 是 mutable projections；`audit_log` 記錄 decisions，但沒有 cryptographic chain。
- Application history 依 workflow convention 為 append-only，但 database 沒有 trigger、cryptographic chain 或 out-of-band writer protection。

不得把這些剩餘 gaps 描述成已實作 controls。Production policy 可以針對 gaps fail closed；任何 future persistence change 仍需要獨立核准的 design 與 migration。

## 3. Authority unit

Runtime authority 是以下條件的 exact conjunction：

```text
governance_skill_id
+ current revision_id and is_current=1
+ revision status=approved
+ canonical Asset identity binding
+ exact canonical artifact_digest
+ matching Skill version
+ non-empty approved_by and valid approved_at
```

任一元素 absent、stale、ambiguous 或 mismatched，revision 就沒有 authority。Search results、Asset Index rows、`skills.status`、Dashboard state、Knowledge Plane context、benchmark reports、Runtime contracts 與 prior run success 都不能取代這個 tuple。

## 4. Lifecycle states

| State | 意義 | Runtime authority |
|---|---|---|
| `pending-unbound` | Current revision 存在，但缺少 exact canonical identity 與／或 digest binding | 無 |
| `pending-bound` | Current revision 已綁 exact Asset identity 與 digest，等待 decision | 無 |
| `approved-current` | Exact bound current revision 有 approval actor 與 timestamp | **有，但 create/resume 仍須 revalidation** |
| `rejected-current` | Current revision 有 explicit rejection decision | 無 |
| `blocked-current` | Current revision status 被 Governance workflow 設為 blocked | 無 |
| `superseded` | Historical revision 已非 current | 無 |
| `drifted` | Stored approval 不再符合 canonical Asset content、version、identity 或 currentness | 無 |

只有 `approved-current` 具有 admission authority。Non-current revision 的 approval 無效；historical approval fields 只是 evidence。

## 5. Transitions 與 gates

### Register

建立 Governance Skill 時，revision 1 是 `pending-unbound`。Register 後續 revision 會 atomically 把它設為 current、把 prior revisions 設為 non-current，並把新 revision reset 為 pending/unbound。Approval 不會 carry forward。

### Bind

Binding 是針對 pending current revision 的 server-side operation。Server 載入 canonical Skill payload、resolve canonical Asset identity、計算 digest，並記錄 authenticated actor。Request input 不能提供 trusted actor 或 digest。只有 identity 或 digest 不同時，approved revision 的 rebind 才會被拒絕。相同 identity 與 digest 會在 status check 前 idempotent success，因此 approved、rejected 或 blocked current revision 也會成功回傳；該回傳不改變 revision authority state。

### Review 與 decide

Scans、tests 與 review packets 是 decision evidence，本身不授予 authority。Initial approval 只有在 exact binding 後才建立 `approved-current`。Rejected 或 blocked current revision 都不能由 normal approval call 直接回到 `approved-current`。

Rejection 後，必須先 register new revision 並完成 exact binding，scan/test evidence 才可符合 fresh reapproval 資格。Approval 從 application-written audit events 解析符合資格的 evidence IDs，在同一 transaction 建立 authenticated `review` event，並依 `governance.fresh-reapproval.v1` 記錄 decision。Missing、failed、pre-binding 或 cross-revision evidence 都會拒絕 write，且不留下 partial review／approval event。

Generic revision-state 唯一允許的 transition 是 application remediation 的 `blocked` to `pending`；不能設定 `approved`，也不能清除 rejection。完成 blocked remediation 後，必須提供 reset 後新寫入且符合資格的 scan/test evidence 才能 approve。

只有 targeted revision 是 current 時，rejection 才建立 `rejected-current`。只有 security scan 寫入 current revision 時，blocking 才建立 `blocked-current`。Non-current reject、scan、equivalence target 會在任何 projection/evidence write 前失敗。單獨 `skills.status` projection change 不是 authority，不能自行授予或移除 Runtime admission。

### Supersede、revoke effect 與 drift

- 新 current revision 立即讓 prior revision 成為 `superseded`。
- Reject 或 block current revision 會結束其 admission authority；authority-affecting 與 evidence write 不能 target historical revision。
- Exact identity、version、digest、currentness 或 approval-provenance mismatch 在 admission 時形成 `drifted` 並 fail closed。
- 因為沒有專用 revocation event，operator 必須保存 audit decision 並使用已實作的 state change；文件不得聲稱有獨立 revocation mechanism。

### Re-approve

Rejected current revision 的 direct reapproval 一律拒絕。唯一支援的流程是 `register new revision -> exact bind -> fresh scan -> fresh passing test -> authenticated review -> approve`。Initial approval 維持相容，Runtime authority 仍是同一個 exact approved-current tuple。本 control 不實作 approval expiry、quorum、dedicated revocation、cryptographic audit chain 或 database-level tamper resistance。

## 6. Runtime interaction

1. **Create：** admission 讀取 exact current approved revision 與 canonical digest。Failure 不建立 authorized execution basis。
2. **Persist：** admitted run 把 Governance revision identity 存入 keyed execution basis，並在 append-only ledger 記錄 attestation。
3. **Resume：** 在消耗 one-time resume claim 前，再次檢查 Governance 與 canonical identity；authority 改變就拒絕 resume。
4. **History：** 後續 rejection、blocking、drift 或 supersession 不會改變已 appended events 或 derived historical Evidence。
5. **HITL：** Runtime approval 與 recovery decisions 是獨立的 Runtime-ledger authority；不能建立 Governance approval 或修復 stale revision。

## 7. Ownership 與 actor boundary

| Actor/surface | 可以做 | 不得視為 |
|---|---|---|
| Parser / Asset repository | Resolve canonical payload、identity、revision、digest | Governance approver |
| Governance service | Bind、scan、test、approve、reject、block、audit | Runtime effect ledger |
| Authenticated reviewer | 透過 authorized server workflow 提交 decision | Client-provided trusted digest/actor 的來源 |
| Core Runtime gate | Read 並 attest exact current Governance authority | Governance approval mutator |
| Runtime HITL actor | Approve bounded action 或 confirm recovery | Governance revision approver |
| Dashboard | 呈現 workflows 並送出 authenticated requests | Authority database 或 policy engine |
| Knowledge / Evaluation planes | 提供 context 或 evidence-only measurements | Admission authority |

## 8. Audit 與 retention

每個影響 authority 的 decision 都要保留 Governance Skill ID、revision ID、canonical Asset ID、artifact digest、actor、timestamp、reason、decision evidence reference、previous state 與 new state。Fresh reapproval 還要保存 binding event、scan ID、test ID、review event 與 policy identifier。不得刪除 historical revisions，也不得改寫 Runtime events 來製造 current state 連續的假象。

Application 沒有 history update/delete workflow，但這不等於 physical immutability。Database-level tamper resistance 仍是必須另行 gate 的 persistence change。

Incident review 必須能回答：

- admission 時是哪一個 exact revision current 且 approved；
- 檢查了哪個 canonical digest；
- 誰用哪個 authenticated subject 做 decision；
- 哪個後續 transition 結束 authority；
- resume 是否在該 transition 後被拒絕。

## 9. Change control

改變 authority tuple 或 current-target semantics、hardening re-approval、新增 approval expiry、revocation/quorum 或改變 persistence semantics，都需要 focused tests、independent review；若 storage 改變，還需要 explicit migration plan。Runtime Architecture v1 本身不授權這些變更。

[`governance-authority-lifecycle-proposal.md`](governance-authority-lifecycle-proposal.md) 記錄實作這些 gaps 前所需的 operator decisions 與 staged design gates。
