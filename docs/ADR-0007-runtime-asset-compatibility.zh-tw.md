# ADR-0007 — Runtime Asset 術語與 Skill 相容性

**狀態：** P0 已接受

## 背景

Runtime 目前接收 canonical Skill 文件，但後續 catalog、search 與 revision 操作
需要通用 identity。全面改名會混淆 ARD 語意、歷史 Evidence 與既有 HTTP
contract。Runtime Asset envelope 與 ADR-0004 的 Evidence envelope 不同：Asset
描述 catalog identity；Evidence 描述 derived governance 與 execution provenance。

## 決策

`Runtime Asset` 是新增的 identity 與 provenance envelope。P0 僅支援
`asset_type=skill`；內嵌 payload 保持原 canonical Skill 文件，Actions、Rules、
Directives 仍是 decomposition ontology。

- P0 Skill 的 `asset_id` 就是 canonical `meta.skill_id`；
- `content_hash` 使用 `runtime.digest.canonical_digest(payload)`，與 Runtime
  governance 採用完全相同的穩定 JSON digest；
- Asset `revision_id` 為 `asset-revision:<content_hash>`，刻意與 governance
  `skill_revisions.revision_id` 區隔；
- `source_digest` 是 source bytes 的 SHA-256，只供 provenance，不能替代 admission；
- parser identity 由 `parser_id` 與 `parser_version` 明確記錄。

英文 schema 與 ADR 為權威版本；`.zh-tw.md` 是人類可讀參考。既有 Skill API
欄位、Runtime ledger 欄位、governance identifiers、歷史 events、migrations 與
fixtures 保留原名。新的 generic code 使用 Asset 術語；compatibility adapter
可以保留 Skill 術語。禁止全域搜尋取代。

## 相容與失敗行為

Canonical Skill 轉成 envelope 再轉回必須 lossless。Envelope v1 不執行資料
migration、不改動既有 Skill schema，也不提供執行授權。不支援的 Asset Type、
缺少或 namespace 混淆的 revision identity、錯誤 provenance、identity drift 或
digest mismatch 一律 fail closed。
