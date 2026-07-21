# Knowledge Plane Extension Contract v1

- 狀態：**已接受的 extension contract；retrieval implementation deferred**
- 版本：`1.0.0`
- 生效日期：`2026-07-18`
- Schema：[`../schema/knowledge-plane-extension-contract.schema.json`](../schema/knowledge-plane-extension-contract.schema.json)
- Architecture baseline：[`runtime-architecture-v1.md`](runtime-architecture-v1.md)
- 英文權威文件：[`knowledge-plane-extension-contract.md`](knowledge-plane-extension-contract.md)

## 1. 目的

Knowledge Plane contract 把有版本、digest-addressed 的 knowledge source references 綁定到既有 Directive IDs，供 bounded context 使用。它定義安全的 extension seam；不新增 Runtime Asset type、retrieval service 或 authority source。

Version 1 刻意維持窄範圍：

- `asset_ref.asset_type` 永遠是 `skill`；
- 每個 binding 都指向 exact canonical Skill revision 中既有的 `d_NNN` Directive；
- source content 留在 contract 外，只記錄 stable reference、revision、digest、classification 與 retrieval mode；
- 所有 Knowledge Plane 使用都是 `context-only`；
- derived Evidence 必須包含 source 與 binding identity。

## 2. Contract 邊界

```text
exact Skill Asset revision
  + existing Directive ID
  + bounded source references
  + availability policy
  + Evidence requirements
  -> context supplied to an allowed Runtime phase
```

Contract 不定義 tool call、executable expression、policy decision、approval decision、action binding 或 database persistence。Consumer 可以用 resolved context 輔助 planning 或 validation，但正常的 Rule、Governance、policy 與 execution gates 仍是 authority。

## 3. 必要 invariants

1. **Exact identity。** `asset_id`、`revision_id` 與 `content_hash` 必須符合交給 validator 的 canonical Skill payload。
2. **Directive ownership。** 每個 `directive_id` 必須存在於該 payload。Duplicate binding ID 與 duplicate source reference 必須 fail closed。
3. **Context-only authority。** `usage` 與每個 source 的 `authority` 固定為 `context-only`。Knowledge output 不能 approve、deny、resume 或 execute Runtime run。
4. **Bounded consumption。** 每個 binding 宣告 `max_sources` 與 `max_characters`，declared source count 不得超過 budget。
5. **Classified provenance。** 每個 source 宣告 stable revision、SHA-256 digest、classification 與 retrieval mode。Contract 不嵌入 source payload 或 credentials。
6. **Closed required inputs。** Required binding 在 source unavailable 時必須使用 `fail-closed`；optional context 可使用 `skip-binding`。
7. **Evidence trace。** Consumer 必須把 binding IDs、source digests 與 event watermark 記錄在 derived Evidence projection。

## 4. Lifecycle

1. 從 immutable repository snapshot resolve 並驗證 canonical `AssetRevision`；不得從裸 Skill payload 重建 identity。
2. 驗證 Knowledge Plane contract schema 與 semantic cross-references。
3. 只在 host 提供的 classification 與 budget controls 內 resolve declared source revisions。
4. 連同 Runtime event watermark 記錄 resolved binding IDs 與 source digests。
5. Skill payload、source revision、digest 或 binding contract 任何改變都形成新的 validation basis；不得重用先前 approval 或 context。

本 contract 不啟用任何 resolver 或 retrieval adapter。未來 implementation 必須另行審查 source authorization、classification enforcement、prompt-injection handling、redaction、caching、timeouts 與 audit behavior。

## 5. Compatibility 與 non-goals

此 extension 保持 Runtime Architecture v1，因為它：

- 重用唯一支援的 Runtime Asset type `skill`；
- 引用既有 Directives 而不改變 ARD；
- 保持 Governance 與 append-only ledger 的 authority；
- 不需要 physical database migration；
- 不需要 Dashboard 變更；
- 不整合 FTS5，也不把 search output 升格為 authority。

它不宣稱 knowledge quality、factual correctness、retrieval completeness 或 agent improvement。這些主張屬於 Agent Evaluation benchmark framework，且必須由 measured evidence 支持。

## 6. Versioning

Additive optional fields 可以在 compatible minor version 提案。任何允許其他 Asset type、executable content、embedded source payload、authority-bearing Knowledge output，或弱化 provenance 的變更，都需要新的 major contract 與 Architecture review。
