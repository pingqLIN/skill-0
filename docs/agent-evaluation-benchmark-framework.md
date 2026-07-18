# Agent Evaluation Benchmark Framework v1

- Status: **Accepted framework; foundation suite remains draft until reviewed and frozen**
- Version: `1.0.0`
- Effective date: `2026-07-18`
- Runner: [`../tools/agent_evaluation_benchmark.py`](../tools/agent_evaluation_benchmark.py)
- Schemas: `agent-evaluation-{suite,candidate,report}.schema.json`
- Draft suite: [`../benchmarks/agent-evaluation-foundation-v1.json`](../benchmarks/agent-evaluation-foundation-v1.json)
- Traditional Chinese companion: [`agent-evaluation-benchmark-framework.zh-tw.md`](agent-evaluation-benchmark-framework.zh-tw.md)

## 1. Purpose

This framework evaluates recorded agent behavior against a reviewed, digest-
frozen suite. It provides deterministic evidence for Runtime foundation claims;
it does not execute an agent, call a provider, choose a model, or authorize a
Runtime run.

The separation is intentional:

```text
external capture adapter (out of scope)
  -> structured candidate replay
reviewed + frozen benchmark suite
  -> deterministic scorer
  -> evidence-only report
```

## 2. Trust boundary

The scorer accepts only structured outcome, Evidence codes, claim codes, and an
optional latency measurement. Free-form model output must be converted by a
separately governed capture/extraction process. A candidate artifact is input
data, not trusted evidence, until its provenance and suite digest are verified
by the caller.

The scorer:

- always uses repository-owned schemas;
- recomputes the suite digest and rejects drift;
- scores only `reviewed-frozen` suites;
- rejects missing, duplicate, or unknown candidate cases;
- binds the report to a canonical candidate digest and preserves the candidate's
  timestamp under the accurate name `candidate_produced_at`;
- marks candidate provenance `unverified` because capture attestation is outside
  the scorer boundary;
- emits a schema-validated report with `authority=evaluation-evidence-only`;
- performs no network, model, database, Governance, Runtime, or Dashboard work.

## 3. Metrics and gate

| Metric | Meaning |
|---|---|
| `outcome_accuracy` | Exact expected outcome across all cases |
| `evidence_recall` | Required Evidence codes observed across all cases |
| `forbidden_claim_rate` | Fraction of cases emitting at least one forbidden claim code |
| `safety_outcome_accuracy` | Exact outcome accuracy for `safety_critical=true` cases |
| `safety_case_pass_rate` | Safety cases with correct outcome, complete required Evidence, and no forbidden claim |

All four configurable thresholds are suite-owned and digest-covered. Thresholds
are compared against unrounded values; rounding is presentation-only. In
addition, `safety_case_integrity` is a non-configurable hard gate requiring every
safety case to have the correct outcome, complete required Evidence, and no
forbidden claim. The framework reports both failed checks and mismatched case
IDs; it does not collapse a safety regression into an aggregate average.

## 4. Freeze and replay protocol

1. Curate cases independently of candidate output. Do not derive expected values
   from the implementation under test.
2. Review case wording, expected outcomes, required Evidence, forbidden claims,
   taxonomy coverage, and thresholds.
3. Set `freeze.state=reviewed-frozen`, record an `agent:*` reviewer and timestamp,
   then recompute `suite_digest` over the entire document except that digest field.
4. Capture one complete candidate record for every frozen case. Record the exact
   `benchmark_id` and `suite_digest`.
5. Run the scorer. Preserve the suite, externally verified candidate provenance,
   command, exit code, and report together. The report itself remains marked
   `candidate_provenance=unverified` until a separate attestation contract exists.
6. Any case, threshold, freeze, or expected-value change creates a new digest and
   invalidates prior candidate replays.

The checked-in foundation suite is deliberately `draft`; it cannot be scored
until its case content receives an independent content review and freeze.

## 5. Interpretation

A passing report supports only the claims represented by that exact suite and
candidate capture. It does not prove general intelligence, factual correctness,
strict Skill equivalence, production safety, or permission to execute. Benchmark
output cannot change Asset, Governance, or Runtime authority.

Comparisons require the same suite digest and compatible capture provenance.
Missing capture provenance, undisclosed retries, manual cherry-picking, or an
unfrozen suite makes the result `UNKNOWN`, not passing evidence.

## 6. Explicit exclusions

Framework v1 does not:

- call external or local model providers;
- persist results to an operator database;
- add an Asset type;
- use or integrate FTS5;
- modify the Dashboard;
- perform physical database migration;
- enable real adapter execution; or
- promote evaluation output to Governance authority.
