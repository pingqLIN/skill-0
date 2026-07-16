# Adapter Certification

This document is the authoritative certification and operator-approval contract for side-effecting Runtime v4 adapters. See [adapter-certification.zh-tw.md](adapter-certification.zh-tw.md) for the Traditional Chinese companion.

## Current decision

`skill0.local-pdf-filesystem` is the single certification candidate. Its isolated technical probes pass, but its production approval is intentionally `pending_human_approval`.

No production approval record was issued during certification. The `/api/runs` surface still accepts only the simulation adapter and `dry_run=true`; this batch does not expose a real adapter or authorize an external write.

## Certified scope

The candidate covers only the local filesystem side-effect boundary for canonical skill `claude__anthropic__pdf`, action `a_006`, operation `create_pdf`.

| Control | Contract | Technical evidence |
|---|---|---|
| Credential and least privilege | No secret is accepted. A dedicated OS process identity may create files only under the configured output root, write its SQLite receipt store, and move owned artifacts into the root-local `.del` sink. Network, subprocess, overwrite, traversal, and secret access are denied. | Constructor has no credential input; traversal is rejected; the sandbox observes no effect outside the output root. Production OS identity and ACL evidence remain an operator approval prerequisite. |
| Idempotency | The Runtime ledger claims the primary key and passes it to the adapter. The adapter stores only its SHA-256 digest. Same key plus same request returns the original result without another effect; same key plus different request fails as a conflict. | Replay produces one PDF; a conflicting replay leaves the original digest unchanged. |
| Reconciliation | A read-only probe compares the SQLite claim, root-local receipt marker, resource identity, and content digest. Outcomes are `not_found`, `applied`, `compensated`, `diverged`, or `unknown`. `unknown` never permits automatic retry. | A timeout injected after file commit but before terminal DB receipt reconciles to `applied`, finds exactly one effect, and performs zero retries. |
| Compensation | The adapter moves only its owned artifact and receipt marker into `.del`; it never permanently deletes them. Compensation has its own idempotency key. | Evidence contains original resource ID, content digest, quarantine resource ID, compensation-key digest, and completion time. A repeated compensation returns the original evidence. |
| Rate limit | SQLite fixed window, two new effects per 60 seconds, one concurrent call. Replays do not consume a new-effect slot. | The third new effect is rejected with `retry_after_seconds` and is recorded as a proven pre-effect `ACTION_FAILED`, not an ambiguous outcome; a request after the window succeeds. Any limit change changes the manifest digest and requires recertification and a new approval. |
| Production approval | Default deny. Approval binds adapter ID/version, source artifact digest, manifest digest, certification evidence digest, exact environment, exact operations, reviewer, and expiry. | Exact signed scope is accepted; operation drift and expiry are rejected. The attestation is included in the keyed execution basis. |

## Compensation boundary

The canonical PDF decomposition currently has no separate delete or rollback Action. The adapter compensation primitive is therefore technically certified, but it must remain behind `human_intervention` in the Runtime contract. It must not be advertised as automatic ARD compensation until a reviewed canonical compensation Action and cross-reference exist.

## Evidence generation

Run the isolated probes from the repository root:

```powershell
python tools\certify_adapter.py --manifest adapters\local-pdf-filesystem\adapter-certification.json --output audit\adapter-certification-local-pdf.json
```

The command uses temporary local directories, no external credential, and no network. The output is ignored by Git. A passing document still says `pending_human_approval`.

## Human production approval gate

Approval is an L3 runtime gate. Before issuing it, the operator must verify all of the following for the target environment:

1. The certification evidence is `passed` and all seven required probes are present.
2. The live adapter artifact and manifest digests match the evidence.
3. A dedicated OS identity and filesystem ACL restrict the adapter to the exact output and state roots.
4. The SQLite receipt store is persistent, backed up, and writable only by the runtime identity and operators.
5. Output quota, `.del` retention, monitoring, incident ownership, and reconciliation escalation are documented.
6. The environment, allowed operation, reviewer identity, and expiry are deliberately chosen.
7. The approval signing key is distinct from JWT, Runtime binding, and other application keys; it is injected by the environment secret manager and is never printed, logged, or committed.

After that review, an operator may issue one environment-specific record:

```powershell
python tools\adapter_approval.py issue --manifest adapters\local-pdf-filesystem\adapter-certification.json --evidence audit\adapter-certification-local-pdf.json --environment <environment-name> --approved-by <reviewer-id> --expires-at <ISO-8601-timestamp> --output <pre-provisioned-approval-path>
```

`SKILL0_ADAPTER_APPROVAL_KEY` must already be available to the process through the target secret manager. The tool refuses a key shorter than 32 characters and refuses to overwrite an existing approval file.

Verify the live manifest and approval together:

```powershell
python tools\adapter_approval.py verify --approval <approval-path> --manifest adapters\local-pdf-filesystem\adapter-certification.json --environment <environment-name>
```

Create a signed replacement revocation without overwriting the original record:

```powershell
python tools\adapter_approval.py revoke --approval <approval-path> --revoked-by <reviewer-id> --output <pre-provisioned-revocation-path>
```

Removing the configured approval path, configuring the signed `revoked` replacement, expiry, artifact drift, manifest drift, operation drift, or environment drift all fail closed. Preserve receipts and `.del` artifacts during rollback so reconciliation evidence is not lost.

## Remaining production boundary

An approval record alone does not load this adapter into `/api/runs`. A later, separately approved loader batch must provision the dedicated identity and roots, pass the approval gate into the orchestrator, retain the existing HITL boundary, and prove backup/restart behavior with the adapter state store. Until that batch passes, production execution remains disabled.
