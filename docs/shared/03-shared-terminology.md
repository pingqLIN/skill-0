# Shared Terminology

## Purpose

This glossary keeps `skill-0` and `skill-0-GUI` aligned on the same vocabulary.

## Terms

### Canonical parser

The parser implementation owned by `skill-0`.

### Bridge

The integration layer that allows another runtime, such as `skill-0-GUI`, to call the canonical parser.

### Standalone fallback

A local parser or compatibility path that keeps a consumer usable when the canonical parser is unavailable.

### Equivalence

A verified statement that two parsing paths produce results that match under a defined comparison method.

### Fidelity

A weaker statement that the current output remains meaningfully close to canonical behavior or structure, without proving strict equivalence.

### Compatibility

A weaker claim that a fallback path remains useful and structurally aligned, without asserting identical behavior.

### Transformation layer

Any logic that consumes parser output and adds:

- visualization
- ranking
- metrics
- warnings
- editor affordances

without becoming the canonical parser itself.

### Evidence-based warning

A finding presented with:

1. finding
2. evidence
3. risk
4. recommended action

### Shared document

A stable contract or glossary document that is intentionally mirrored between repositories.

### Repository-specific document

A document whose content depends on one repository's runtime, deployment, roadmap, or current worktree state.
