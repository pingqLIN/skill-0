# Agent Evaluation Benchmark Framework v1.1

- Status: **Framework v1.1 accepted; foundation suite reviewed-frozen; checked-in replay is synthetic only**
- Version: `1.1.0`
- Effective date: `2026-07-21`
- Runner: [`../tools/agent_evaluation_benchmark.py`](../tools/agent_evaluation_benchmark.py)
- Schemas: `agent-evaluation-{suite,candidate,report}.schema.json`
- Frozen suite: [`../benchmarks/agent-evaluation-foundation-v1.json`](../benchmarks/agent-evaluation-foundation-v1.json)
- Traditional Chinese companion: [`agent-evaluation-benchmark-framework.zh-tw.md`](agent-evaluation-benchmark-framework.zh-tw.md)

## 1. Purpose

This framework evaluates recorded agent behavior against a reviewed, digest-
frozen suite. It provides deterministic scoring evidence for the exact claims
represented by a captured candidate; it does not execute an agent, call a
provider, choose a model, or authorize a Runtime run.

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
- requires digest-covered category coverage and exact per-case Evidence/claim
  allowlists, so unknown codes fail closed;
- requires complete independent-review scope metadata before freeze;
- validates capture source digest kind, attempts, retry disclosure, selection
  policy, extraction method/version, and attestation reference;
- fails the replay gate when a candidate uses retries, multiple attempts, or
  non-predeclared selection;
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
forbidden or unknown code. `code_allowlist_integrity` rejects any Evidence or
claim code outside that case's reviewed allowlists. `capture_selection_integrity`
rejects retries, multiple attempts, and non-predeclared selection. These hard
gates cannot be relaxed by suite thresholds. The framework reports both failed
checks and mismatched case IDs; it does not collapse a safety regression into an
aggregate average.

## 4. Freeze and replay protocol

1. Curate cases independently of candidate output. Do not derive expected values
   from the implementation under test.
2. Review case wording, expected outcomes, required and allowed Evidence,
   allowed and forbidden claims, required taxonomy coverage, non-empty safety
   assertions, and thresholds.
3. Set `freeze.state=reviewed-frozen`, record an `agent:*` reviewer and timestamp,
   the complete four-part review scope, `review_method=independent-agent-review`,
   and `review_attestation=unverified`; then recompute `suite_digest` over the
   entire document except that digest field.
4. Capture one complete candidate record for every frozen case. Record the exact
   `benchmark_id`, `suite_digest`, source digest kind, attempts, retry policy,
   selection policy, extraction method/version, and attestation reference.
5. Run the scorer. Preserve the suite, externally verified candidate provenance,
   command, exit code, and report together. The report itself remains marked
   `candidate_provenance=unverified` until a separate attestation contract exists.
6. Any case, threshold, freeze, or expected-value change creates a new digest and
   invalidates prior candidate replays.

The checked-in foundation suite is `reviewed-frozen`. Its checked-in candidate
is deliberately a synthetic fixture sourced from the canonical suite, not an
agent/provider capture.

For `synthetic-fixture`, `capture.source_digest_kind=canonical-suite` means the
digest is computed from the canonical JSON suite basis, not raw file bytes.
External capture artifacts use `sha256-bytes`.

## 5. Checked-in foundation replay evidence

| Artifact | Frozen value |
|---|---|
| Suite digest | `sha256:3edf2a4d0ee9636c4ccf5eaba73fb5356ef385b79aed4bb1af6286dc0de788cd` |
| Independent reviewer | `agent:item5-evidence-reviewer` |
| Candidate | [`../benchmarks/agent-evaluation-foundation-v1-replay-fixture.json`](../benchmarks/agent-evaluation-foundation-v1-replay-fixture.json) |
| Candidate kind | `synthetic-fixture`; one predeclared attempt; no retries |
| Report | [`../benchmarks/agent-evaluation-foundation-v1-replay-report.json`](../benchmarks/agent-evaluation-foundation-v1-replay-report.json) |
| Runner result | Exit `0`; 6/6 cases; all five metrics `1.0`; replay gate passed |
| Authority/provenance | `evaluation-evidence-only`; candidate `unverified`; real-model performance `unknown` |

```powershell
.\.venv\Scripts\python.exe tools\agent_evaluation_benchmark.py `
  --suite benchmarks\agent-evaluation-foundation-v1.json `
  --candidate benchmarks\agent-evaluation-foundation-v1-replay-fixture.json
```

This passing gate proves only that the deterministic scorer and frozen synthetic
fixture conform to the reviewed contract. It is not an Agent, model, provider,
production, or provenance acceptance result.

## 6. Interpretation

A passing report supports only the claims represented by that exact suite and
candidate capture. It does not prove general intelligence, factual correctness,
strict Skill equivalence, production safety, or permission to execute. Benchmark
output cannot change Asset, Governance, or Runtime authority.

Comparisons require the same suite digest and compatible capture provenance.
Missing capture provenance, undisclosed retries, manual cherry-picking, or an
unfrozen suite makes the result `UNKNOWN`, not passing evidence.

For `external-agent` candidates, retries, multiple attempts, or manual selection
make `capture_selection_integrity` fail. Even a clean single-attempt replay gate
remains replay conformance only: the report stays
`candidate_provenance=unverified` and `real_model_performance=unknown` until a
separate attestation contract verifies the capture.

## 7. Explicit exclusions

Framework v1.1 does not:

- call external or local model providers;
- persist results to an operator database;
- add an Asset type;
- use or integrate FTS5;
- modify the Dashboard;
- perform physical database migration;
- enable real adapter execution; or
- promote evaluation output to Governance authority.
