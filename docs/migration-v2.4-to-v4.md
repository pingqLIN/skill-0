# Migration: SKILL-0 v2.4 decomposition to v4 runtime governance

## Compatibility model

A v2.4 skill remains valid without a runtime contract. Runtime execution is opt-in.

## Steps

1. Parse/validate the original skill unchanged.
2. Generate a separate runtime contract referencing ARD IDs.
3. Run schema validation.
4. Run ARD cross-reference validation.
5. Review effects, risk, idempotency, and compensation metadata.
6. Keep `real_execution=false` during dry-run evidence collection.
7. Promote only after governance review and failure-injection tests.

## Evidence migration

Map existing quality signals, success criteria, failure patterns, and Directive provenance into the evidence projection. Do not copy these into a fourth `decomposition.evidence` list.
