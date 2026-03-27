# Shared Parser Contract

## Purpose

This document defines the contract between the canonical parser in `skill-0` and downstream consumers such as `skill-0-GUI`.

## Canonical implementation

The canonical parser implementation lives in:

- `scripts/auto_parse.py`

Downstream consumers may call the parser directly, shell out to it, or vendor compatible fallback logic, but only `skill-0` owns the canonical implementation contract.

## Stable contract surface

Downstream consumers may rely on the following properties:

1. A skill source is transformed into a structured JSON-like decomposition result.
2. The result distinguishes structured entities such as actions, rules, and directives.
3. The result includes parser metadata sufficient to explain which implementation produced it.
4. The result is intended to be validated against the published schema.

## Consumer obligations

A consumer such as `skill-0-GUI` should:

1. preserve parser metadata in downstream results
2. avoid claiming strict equivalence when fallback logic is used unless equivalence has been tested, and prefer fidelity wording otherwise
3. distinguish raw parser output from visualization-only derived metrics
4. document any transformation layer that changes interpretation, ranking, or display semantics

## Non-contract details

The following may evolve without downstream consumers treating them as API breakage by default:

- internal heuristics
- implementation language details
- non-essential field ordering
- additional derived metrics added by presentation layers

## Change rule

If the parser changes in a way that alters:

- entity semantics
- required fields
- schema compatibility
- metadata meaning

then this shared document should be updated before or with the implementation change, and downstream mirrors should be resynced.
