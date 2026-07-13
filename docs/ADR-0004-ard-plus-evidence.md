# ADR-0004 — Preserve ARD; model Evidence as an envelope

**Status:** Proposed

## Context

The project core defines mutually exclusive Action, Rule, and Directive elements. Previous drafts proposed Evidence as a fourth peer category.

## Decision

Retain ARD as the decomposition ontology. Evidence is a derived governance/provenance envelope that references ARD IDs and execution events.

## Consequences

- Existing parser/search/UI semantics remain stable.
- Evidence can evolve independently.
- Runtime execution history does not pollute skill decomposition.
- The external program name may remain ARDE for continuity, but schemas must state the distinction.
