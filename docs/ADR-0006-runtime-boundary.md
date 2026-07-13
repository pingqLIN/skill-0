# ADR-0006 — Framework-neutral runtime boundary

**Status:** Proposed

## Decision

SKILL-0 core owns ARD references, governance decisions, effect metadata, event ledger, and evidence projection. MCP, OpenAI Agents SDK, LangGraph, OPA, and sandbox runtimes live behind adapters.

## Consequences

- Framework upgrades do not force base schema migrations.
- Tool guardrails and graph checkpoints complement, but do not replace, the runtime ledger.
- Adapter-specific traces carry `skill0_run_id` for correlation.
