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

`ActionAdapter.execute()` receives the ledger-claimed primary idempotency key
explicitly. A production adapter must not reconstruct a different key from
parameters or ignore that claim.

## Certification candidate

`local-pdf-filesystem/adapter-certification.json` defines the first isolated
candidate, `skill0.local-pdf-filesystem`. Its executable probes cover a
credential-free least-privilege boundary, replay and conflict idempotency,
post-commit reconciliation, recoverable `.del` compensation evidence, a
SQLite-backed rate limit, and exact-scope production approval.

Passing these probes does not activate the adapter. The public Runtime API
continues to load only the simulation adapter and accept `dry_run=true`.
Production execution also requires an unexpired, signed, environment-specific
approval whose artifact, manifest, evidence, and operation digests match the
runtime candidate.

## Integration order

1. test/native adapter
2. MCP
3. OpenAI Agents SDK
4. LangGraph
5. command/sandbox adapter

A command adapter must not be enabled until OPA/sandbox/mount/network controls are implemented and tested.
