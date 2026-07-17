# ADR-0007 — Runtime Asset terminology and Skill compatibility

**Status:** Accepted for P0

## Context

The Runtime currently receives canonical Skill documents while future catalog,
search, and revision operations need generic identity. A broad rename would blur
ARD semantics, historical evidence, and existing HTTP contracts. The Runtime
Asset envelope is distinct from ADR-0004's Evidence envelope: Asset describes
catalog identity, while Evidence describes derived governance and execution
provenance.

## Decision

`Runtime Asset` is an additive identity and provenance envelope. P0 supports
only `asset_type=skill`; the embedded payload remains the canonical Skill
document and Actions, Rules, and Directives remain the decomposition ontology.

Identity is deterministic:

- P0 Skill `asset_id` is the exact canonical `meta.skill_id`;
- `content_hash` is `runtime.digest.canonical_digest(payload)`, the same stable
  JSON digest implementation used by Runtime governance;
- Asset `revision_id` is `asset-revision:<content_hash>`, deliberately distinct
  from governance `skill_revisions.revision_id`;
- `source_digest` is the SHA-256 digest of source bytes and is provenance only,
  never an admission substitute;
- parser identity is explicit in `parser_id` and `parser_version`.

The English schema and ADR are authoritative. `.zh-tw.md` companions are
human-readable references. Existing Skill API fields, Runtime ledger fields,
governance identifiers, historical events, migrations, and fixtures retain
their names. Generic new code uses Asset terminology, while compatibility
adapters may use Skill terminology. Global search-and-replace is prohibited.

## Compatibility and migration

Mapping a canonical Skill into an envelope and back must be lossless. Envelope
v1 introduces no data migration, changes no existing Skill schema, and does not
authorize execution. Governance approval of the exact current revision and
artifact digest remains the Runtime admission authority.

## Failure behavior

Unsupported asset types, missing or namespace-confused revision identity,
malformed provenance, identity drift, or digest mismatch fail closed with a
classified contract error. No fallback may select another revision or silently
normalize payload content.

## Consequences

- Existing Skill behavior remains stable through an explicit adapter.
- A second asset type requires its own evidence and P1 decision.
- Asset, Evidence, ARD, governance revision, and Runtime ledger identities remain
  separate contracts.
