# Shared Mode And Fidelity Contract

## Purpose

This document defines how both repositories should describe canonical mode, fallback mode, fidelity claims, and the stricter cases where equivalence can be asserted.

## Modes

### Canonical mode

Canonical mode means the result was produced by the `skill-0` parser implementation itself.

For `skill-0-GUI`, this normally means the bridge resolved the local `skill-0` repository and invoked the canonical parser path.

### Standalone mode

Standalone mode means the result was produced without calling the canonical parser implementation.

This mode may still be useful and intentionally deployable, but it must be described as compatibility-oriented unless formal equivalence evidence exists.

## Allowed fidelity language

### Safe to say

- uses the canonical `skill-0` parser
- preserves canonical parser output and adds visualization-only transforms
- provides a standalone compatibility path
- exposes structure compatible with the published contract
- maintains high fidelity to canonical parser output

### Not safe to say without evidence

- identical to `skill-0`
- equivalent to canonical output in all cases
- same parser behavior
- drop-in replacement

## Evidence threshold for strict equivalence

Strict equivalence claims require at least:

1. named test fixtures
2. expected canonical outputs
3. repeatable comparison rules
4. documented pass/fail results

Without that evidence, the correct wording is:

- fidelity under review
- fidelity score available
- equivalence unverified
- degraded path
- compatibility-oriented fallback

## Review rule

Any external review report, UI label, or operator note should state:

- which mode produced the result
- whether fidelity is being reported, and whether strict equivalence is asserted, compatible, degraded, or unverified
