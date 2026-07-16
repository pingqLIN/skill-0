# ADR-0006 — Framework-neutral Runtime 邊界

> 本文件是 [ADR-0006-runtime-boundary.md](ADR-0006-runtime-boundary.md) 的繁體中文參考版本；英文原文為權威版本。

**狀態：** 已接受

## 決策

SKILL-0 core 擁有 ARD reference、governance decision、effect metadata、event ledger 與 Evidence projection。MCP、OpenAI Agents SDK、LangGraph、OPA 與 sandbox runtime 都位於 adapter 後方。

Runtime admission 與 action policy 是兩個不同邊界。Canonical parsed artifact 必須明確綁定 governance skill 與其 current revision，而且該 exact artifact digest 必須已核准，才可建立或 resume run。Runtime contract 不可自行宣告已核准。

## 影響

- Framework 升級不會強迫 base schema migration。
- Tool guardrail 與 graph checkpoint 可補強、但不能取代 Runtime ledger。
- Adapter-specific trace 以 `skill0_run_id` 建立關聯。
- `skills.status` 只是 mutable projection，不是 Runtime authority；admission 讀取 current `skill_revisions` row。
- Governance skill UUID 與 canonical parsed skill ID 保持為不同 identity，並透過 explicit unique binding 連結。
