# Knowledge Plane Extension Contract v1

- Status: **Accepted extension contract; retrieval implementation deferred**
- Version: `1.0.0`
- Effective date: `2026-07-18`
- Schema: [`../schema/knowledge-plane-extension-contract.schema.json`](../schema/knowledge-plane-extension-contract.schema.json)
- Architecture baseline: [`runtime-architecture-v1.md`](runtime-architecture-v1.md)
- Traditional Chinese companion: [`knowledge-plane-extension-contract.zh-tw.md`](knowledge-plane-extension-contract.zh-tw.md)

## 1. Purpose

The Knowledge Plane contract binds versioned, digest-addressed knowledge source
references to existing Directive IDs for bounded context use. It defines a safe
extension seam; it does not add a Runtime Asset type, a retrieval service, or an
authority source.

Version 1 is deliberately narrow:

- `asset_ref.asset_type` is always `skill`;
- every binding references an existing `d_NNN` Directive in the exact canonical
  Skill revision;
- source content remains outside the contract and is represented only by a
  stable reference, revision, digest, classification, and retrieval mode;
- all Knowledge Plane use is `context-only`;
- source and binding identities must be present in derived Evidence.

## 2. Contract boundary

```text
exact Skill Asset revision
  + existing Directive ID
  + bounded source references
  + availability policy
  + Evidence requirements
  -> context supplied to an allowed Runtime phase
```

The contract does not define tool calls, executable expressions, policy
decisions, approval decisions, action bindings, or database persistence. A
consumer may use the resolved context to inform planning or validation, but the
normal Rule, Governance, policy, and execution gates remain authoritative.

## 3. Required invariants

1. **Exact identity.** `asset_id`, `revision_id`, and `content_hash` must match
   the canonical Skill payload passed to validation.
2. **Directive ownership.** Every `directive_id` must exist in that payload.
   Duplicate binding IDs and duplicate source references fail closed.
3. **Context-only authority.** `usage` and every source `authority` are fixed to
   `context-only`. Knowledge output cannot approve, deny, resume, or execute a
   Runtime run.
4. **Bounded consumption.** Each binding declares `max_sources` and
   `max_characters`. The declared source count cannot exceed its budget.
5. **Classified provenance.** Each source declares a stable revision, SHA-256
   digest, classification, and retrieval mode. The contract never embeds source
   payloads or credentials.
6. **Closed required inputs.** A required binding must use `fail-closed` when a
   source is unavailable. Optional context may use `skip-binding`.
7. **Evidence trace.** Consumers must record binding IDs, source digests, and an
   event watermark in the derived Evidence projection.

## 4. Lifecycle

1. Resolve and validate the canonical `AssetRevision` from the immutable
   repository snapshot; do not reconstruct identity from a bare Skill payload.
2. Validate the Knowledge Plane contract schema and semantic cross-references.
3. Resolve only the declared source revisions within classification and budget
   controls supplied by the host.
4. Record the resolved binding IDs and source digests with the Runtime event
   watermark.
5. Treat any changed Skill payload, source revision, digest, or binding contract
   as a new validation basis. Prior approval or context is not reusable.

No resolver or retrieval adapter is enabled by this contract. A future
implementation must be separately reviewed for source authorization,
classification enforcement, prompt-injection handling, redaction, caching,
timeouts, and audit behavior.

## 5. Compatibility and non-goals

This extension preserves Runtime Architecture v1 because it:

- reuses the only supported Runtime Asset type, `skill`;
- references existing Directives without changing ARD;
- leaves Governance and the append-only ledger authoritative;
- requires no physical database migration;
- requires no Dashboard change; and
- does not integrate FTS5 or promote search output to authority.

It does not claim knowledge quality, factual correctness, retrieval completeness,
or agent improvement. Those claims belong to the Agent Evaluation benchmark
framework and must be supported by measured evidence.

## 6. Versioning

Additive optional fields may be proposed in a compatible minor version. Any
change that permits another Asset type, executable content, embedded source
payloads, authority-bearing Knowledge output, or weaker provenance requires a
new major contract and Architecture review.
