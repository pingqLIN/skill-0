# Runtime v4 Governance Admission

> 本文件是 [runtime-governance.md](runtime-governance.md) 的繁體中文參考版本；英文原文為權威版本。

Runtime v4 有兩個不同的治理邊界：

1. **Run admission**：證明 exact canonical parsed JSON 就是 current approved governance revision 所代表的 artifact。
2. **Action policy 與 HITL**：決定已通過 admission 的 run 是否能執行或復原各 action。

兩者不能互相取代。

## Identity 與 authority

- `skills.skill_id` 是 governance 內部 UUID。
- `skills.canonical_skill_id` 是連到 `parsed/*.json -> meta.skill_id` 的 explicit unique link。
- `skill_revisions.artifact_digest` 是完整 parsed JSON 的 canonical SHA-256。
- `skills.current_revision_id` 指向 authoritative revision。
- Runtime admission 讀取 `skill_revisions.status`，不會使用 mutable `skills.status` projection 作為授權依據。
- Runtime contract 不含 governance approval 欄位。

沒有 canonical identity 或 artifact digest 的 legacy row，會刻意保持不可執行。

## Binding 與核准流程

綁定 Runtime identity 時，current revision 必須仍是 `pending`：

```http
POST /api/reviews/{governance_skill_id}/runtime-bind
Authorization: Bearer <core-issued-jwt>
Content-Type: application/json

{
  "canonical_skill_id": "claude__skill__example"
}
```

Dashboard governance API 會在 server-side 載入相符的 canonical JSON、計算 digest，並由 JWT `sub` 記錄 reviewer。Request 不能提供 actor 或 digest。

綁定後，再使用既有 governance approval endpoint。建立新 revision 時會把 approval 與 artifact binding 重設為 `pending`／未綁定，因此必須重新 bind 與 review。

## Create 與 resume 語意

Core Runtime gate 在 create 與 resume 都要求：

- exact canonical skill ID binding；
- current revision ownership 與 `is_current=1`；
- current revision status 為 `approved`；
- exact canonical artifact digest；
- version 相符；
- approver identity 與 timestamp 完整。

Governance revision ID 會保存於 `runtime_execution_bases`，並透過 preflight attestation 納入 keyed execution digest。若核准被撤銷、revision 被取代，或 canonical JSON 發生 drift，resume 會在消耗一次性 claim 前被拒絕。

## Dashboard 邊界

Web Dashboard 使用獨立 authenticated client 直接呼叫 core `/api/runs/*`，不透過 Dashboard API proxy Runtime decision，也不把 Runtime decision 複製進 `governance.db`。

- Skill/revision approval 的 authority 在 `governance.db`。
- Runtime HITL decision 的 authority 在 `runtime.db`。
- 兩個 API 都接受 core-issued JWT；Runtime decision actor 另受 `SKILL0_RUNTIME_DECISION_ACTORS` 限制。
- Approve／confirm 只記錄 decision；UI 不會自動 resume 或 recover run。

Per-run Evidence 包含 `governance_ref`，operator 不必直接讀取任何 SQLite 檔案，也能核對 admission revision。
