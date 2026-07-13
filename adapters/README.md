# Adapter Boundary

Framework adapters are deliberately excluded from the P0 merge target. The core scaffold uses protocols so each adapter can be added behind an independent feature flag.

## Required interface properties

- accept an already-resolved and policy-approved Action binding;
- never perform hidden planning or bypass Rule evaluation;
- receive `dry_run` explicitly;
- return structured outputs, external resource ID, and the smallest sufficient compensation parameters;
- propagate SKILL-0 run ID into framework tracing when supported;
- honor primary and compensation idempotency keys;
- never bypass `ACTION_PREPARED` before call or terminal ledger persistence before the next step;
- treat an exception after request submission as an unknown outcome unless the adapter can prove non-commit;
- redact sensitive inputs/outputs before trace export.

## Integration order

1. test/native adapter
2. MCP
3. OpenAI Agents SDK
4. LangGraph
5. command/sandbox adapter

A command adapter must not be enabled until OPA/sandbox/mount/network controls are implemented and tested.
