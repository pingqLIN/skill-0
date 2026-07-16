# ADR-0006 — Framework-neutral runtime boundary

**Status:** Accepted

## Decision

SKILL-0 core owns ARD references, governance decisions, effect metadata, event ledger, and evidence projection. MCP, OpenAI Agents SDK, LangGraph, OPA, and sandbox runtimes live behind adapters.

Runtime admission is separate from action policy. A canonical parsed artifact must be explicitly bound to a governance skill and its current revision, and that exact artifact digest must be approved before a run can be created or resumed. Runtime contracts cannot self-declare approval.

## Consequences

- Framework upgrades do not force base schema migrations.
- Tool guardrails and graph checkpoints complement, but do not replace, the runtime ledger.
- Adapter-specific traces carry `skill0_run_id` for correlation.
- `skills.status` is only a mutable projection and is not Runtime authority; admission reads the current `skill_revisions` row.
- Governance skill UUIDs and canonical parsed skill IDs remain distinct identities linked by an explicit, unique binding.
