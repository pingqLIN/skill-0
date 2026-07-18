# Runtime Architecture v1 基線

- 狀態：**已接受的 stable foundation**
- 版本：`1.0.0`
- 生效日期：`2026-07-18`
- 機器可讀基線：[`contracts/runtime-architecture-v1.json`](contracts/runtime-architecture-v1.json)
- 英文權威文件：[`runtime-architecture-v1.md`](runtime-architecture-v1.md)

## 1. 目的

本文件在 P0 與 P1 證據週期後，凍結目前支援的 Runtime Asset 架構。它把已實作的相容性基礎轉為有版本的穩定基線，不授權另一輪 feature development。

此基線疊加在已接受的 Runtime v4 邊界上。Runtime Asset 是既有 Skill payload 外層的 identity 與 revision envelope。Action、Rule、Directive 仍是 decomposition ontology；Evidence 仍是基於 immutable facts 的正交 projection。

## 2. 穩定邊界

```text
Skill source corpus
  -> SkillParserAdapter
  -> immutable Runtime Asset snapshot（僅 Skill）
  -> read-only Asset 與 legacy Skill compatibility APIs
  -> derived search Index

exact Asset revision + canonical payload digest
  -> Governance current-revision approval
  -> Runtime contract 與 deterministic policy gates
  -> dry-run-only executor
  -> append-only Runtime event ledger
  -> Evidence projection
```

架構包含五個 logical planes：

| Plane | 職責 | Authority |
|---|---|---|
| Asset | Canonical Skill-backed identity、revision、provenance 與 immutable process snapshot | Canonical parsed payload 與 deterministic envelope mapping |
| Index | 可重建的 search projection 與 bounded query execution | 無；Index result 永遠不能授權 run |
| Governance | Asset-to-governance binding、current revision、approval provenance 與 admission decision | Current approved `skill_revisions` row 加上 exact artifact digest |
| Runtime | Planning、policy evaluation、effect sequencing、HITL、recovery 與 reconciliation | Append-only Runtime events；run status 只是 projection |
| Evidence | Deterministic per-run 與 aggregate projections | Source event watermark 與 immutable source facts |

Knowledge Plane 與 Agent Evaluation surface 是 extension points。它們可以使用本基線的 stable identities 與 evidence references，但不能成為 authority source，也不能隱含修改本基線。

## 3. Identity 與 authority 規則

1. v1 唯一支援的 Runtime Asset type 是 `asset_type=skill`。
2. Asset revision 採 content-addressed identity，並 deterministic 地對應一份 canonical Skill payload；ambiguous identity 必須 fail closed。
3. Governance approval 綁定特定 revision。Mutable Skill status、search rank、benchmark score、similarity 或 evaluator output 都不能授予 admission。
4. Runtime admission 綁定 canonical Asset identity、payload digest、governance revision、runtime contract、input 與 preflight basis。
5. Runtime events 為 append-only。`runtime_runs.status`、HITL queue state 與 Evidence documents 都是 query projections，而非獨立真相。
6. External write 必須有 durable identity、idempotency key、logical lock key、declared risk，以及 recovery 或 reconciliation path。
7. Unknown policy、risk、effect outcome、authority 或 snapshot freshness 一律 fail closed。

## 4. Storage 邊界

Version 1 保留現有 physical topology：

| Store | Logical role | Mutation rule |
|---|---|---|
| `skills.db` | Derived Asset search Index | 只能透過 explicit、guarded Index maintenance 重建 |
| `governance.db` | Governance binding 與 revision authority | 只能透過 Governance workflow 變更 |
| `runtime.db` | Append-only Runtime ledger 與 Runtime projections | 只能透過 Runtime ledger transaction 變更 |

本基線不包含 physical database rename、split、merge、authority-row copy 或 Runtime history rewrite。未來 topology 變更必須另立 migration proposal，完成 backup/restore rehearsal、rollback proof，並取得 explicit operator approval。

## 5. Execution 邊界

- Architecture v1 僅允許 dry-run；它不包含可用或已授權的 real adapter execution path。
- 既有 adapter certification 與 production-approval structures 是 dormant infrastructure，不是 execution authority。啟用 non-dry-run execution 必須另行核准 architecture baseline、security gate 與 release decision；approval artifact 本身不足以授權執行。
- Framework integration 必須留在 adapter 後方。MCP、agent framework 與 graph checkpoint 不能取代 Runtime ledger。
- Ambiguous adapter outcome 必須進入 reconciliation，不得 blind retry、compensate 或回報 success。
- Recovery 採 strict LIFO；只有 terminal ledger event 能證明 recovery 成功。

## 6. Compatibility guarantees

在 v1 期間：

- 既有 canonical Skill documents 維持有效且 byte-unmodified；
- ARD identifiers 與 semantics 不變；
- legacy Skill API surfaces 維持 compatibility projections；
- Runtime contract 對非 runtime Skill use 仍是 additive 且 optional；
- Asset Index 保持 derived 與 replaceable；
- Core Runtime 的使用不得依賴 Dashboard redesign。

任何不相容的 identity、authority、ledger 或 evidence 變更都必須建立新的 major architecture baseline。Additive extension contract 若遵守上述所有規則，可獨立升版而不改變 Architecture v1。

## 7. 明確排除項目

本基線不授權：

- FTS5 integration 或 hybrid search promotion；
- 新 Runtime Asset type；
- Dashboard redesign；
- physical database migration；
- 任何 non-dry-run execution；
- 把 search、Knowledge Plane 或 benchmark output 當成 Runtime authority；
- 把 Evidence 視為第四種 ARD category。

## 8. Change control 與 verification

任何聲稱相容 Runtime Architecture v1 的變更都必須：

1. 指出受影響的 plane 與 authority source；
2. 保留 `docs/contracts/runtime-architecture-v1.json` 的 machine-readable invariants；
3. 為行為變更加入 focused tests；
4. 通過採用本基線時的 repository regression baseline（459 tests）；
5. commit 前完成 independent review。

若 proposed change 無法符合任一 invariant，必須建立新 architecture version，不得暗中弱化 v1。
