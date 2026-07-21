# Runtime Asset Production Admission v1

Status: `ACTIVE CONTRACT`

This document is the authoritative release manifest and admission contract for
the supported Runtime Asset production boundary. See
[runtime-production-admission-v1.zh-tw.md](runtime-production-admission-v1.zh-tw.md)
for the Traditional Chinese companion.

The contract makes production admission deterministic and auditable. It does
not deploy a release, observe a host independently, authorize real adapters, or
expand the Runtime beyond the existing dry-run-only, single-host Docker Compose
boundary.

## Admission chain

An admission package proves one immutable chain:

```text
Git commit and tree
  -> production Compose and policy
  -> deployed api/dashboard/web image digests
  -> approved model artifact digest
  -> security, regression, and rehearsal evidence
  -> signed external-control evidence
  -> signed operator approval
  -> production admission result
```

The package is a manifest of evidence. A `PASS` proves that the supplied,
signed claims are authentic, current, unrevoked, and bound to the checked
release. It does not replace live deployment observation by the operator.

## Canonical package

`production-admission-package.json` must validate against
[`production-admission-package.schema.json`](../../schema/production-admission-package.schema.json).
Real packages and their referenced evidence must remain in an access-controlled
location outside the repository.

The package must contain:

- a unique `admission_id`, human release ID, release creation time, and exact
  production environment identity;
- the clean Git commit and tree, production Compose digest, production policy
  digest, independently trusted keyring digest, approved model artifact digest,
  and exact `api`, `dashboard`, and `web` deployed image digests;
- digest-addressed security scan, regression test, and production rehearsal
  evidence;
- the existing signed external-control bundle ID, path, and digest;
- operator identity, authorized role, approval and expiry timestamps, and a
  reference to the root Ed25519 signature; and
- the root Ed25519 signature over the canonical JSON package with `signature`
  omitted.

Paths in the package are POSIX-style paths relative to one protected evidence
root. Absolute paths, traversal segments, missing files, digest mismatches, and
duplicate reuse of one artifact for multiple mandatory evidence categories fail
closed.

## Evidence authority

Evidence producers may be CI jobs, security scanners, build systems, rehearsal
operators, or deployment operators. They may create only evidence for the
operation they actually observed. Repository checks cannot assert external TLS,
network ACL, secret-manager, host, backup, or logging state.

External-control evidence must be signed by an actor and key authorized for the
named environment under the separately administered trusted keyring. The final
package must be signed by a keyring-authorized operator whose exact role is
`production-admission-approver`; external-control-only roles cannot approve it.
The keyring trust-anchor digest must come from protected runner configuration
that the evidence submitter cannot modify.

The v1 verifier validates authorization and signatures but does not claim
approval quorum. Organizations should separate evidence production and final
approval when their policy requires independent review.

## Mandatory evidence and freshness

All clocks are evaluated in UTC. A naive, malformed, future, expired, or
otherwise uncertain timestamp fails closed.

| Evidence | Mandatory rule |
|---|---|
| Security scan | At least one digest-addressed result; observed no more than 168 hours before verification; still unexpired; validity window no more than 168 hours. |
| Regression test | Same 168-hour freshness and validity limits; result must cover the release-bound test scope. |
| Production rehearsal | Same 168-hour freshness and validity limits; must concern the named production topology and release. |
| External controls | Existing external-control schema and verifier apply; observation no more than 24 hours old and signed validity no more than 168 hours. |
| Operator approval | Approved no more than 24 hours before verification, not before release creation, still unexpired, and valid for no more than 168 hours. |

Every evidence observation must predate the final operator approval. Evidence
expiry, approval expiry, release/environment drift, a changed digest, or a new
Git commit requires a new admission attempt and a new signature.

## Verification and decision

Run [`runtime_admission_check.py`](../../tools/runtime_admission_check.py) from
the exact clean checkout being admitted. The verifier:

1. validates the package and keyring schemas;
2. authenticates the keyring through
   `SKILL0_EXTERNAL_CONTROL_TRUSTED_KEYRING_SHA256`;
3. verifies approval freshness, operator authorization, package signature, and
   revocation state, including the required `production-admission-approver`
   role;
4. recomputes the current Git, Compose, and policy bindings;
5. resolves and hashes every referenced evidence artifact;
6. requires exact package-to-external-bundle Git, image, model, environment,
   and evidence ID binding; and
7. invokes the existing external-control verifier for its signature, control
   set, attachment, freshness, authorization, and revocation checks.

Only a complete result returns JSON `status: PASS` and exit code `0`. Any
missing, invalid, stale, revoked, mismatched, unavailable, or unknown check
returns `status: FAIL`, `release_gate: BLOCKED`, and exit code `2`.

## Revocation

The trusted keyring is the current revocation authority. Admission package IDs
and external evidence IDs use the keyring's `revoked_evidence_ids` namespace.
An operator must add the affected ID when an approval or evidence bundle is
withdrawn. Revoking the signing key invalidates every package or bundle that
depends on it. The protected trust-anchor digest must then be updated through
the independently administered runner process.

Revocation never edits or deletes the original package. Preserve the package,
verifier result, reason, keyring revision/digest, and replacement attempt as an
append-only audit history.

## Admission checklist

- [ ] Release checkout is clean and points at the intended commit and tree.
- [ ] All three values are immutable deployed image digests, not mutable tags or local image IDs.
- [ ] The model digest is the approved complete-tree artifact digest.
- [ ] Security, regression, rehearsal, and external-control evidence is real, current, accessible, and digest-addressed.
- [ ] Environment identity describes the actual production target.
- [ ] Keyring trust anchor is injected independently and no private key is present in the repository or runner output.
- [ ] Operator signs the final canonical package after all evidence is fixed.
- [ ] Verifier returns `PASS` with no failed or unknown checks.
- [ ] Package, verifier report, and referenced evidence are retained under operator audit policy.

## Rollback and re-entry

Admission requires an operator-approved rollback path for the prior application
images/configuration and the matching three-store backup set. A rollback must
not downgrade only the Runtime schema while retaining newer event data. If the
previous release cannot interpret current authority or event state, Runtime
remains disabled and the stores are preserved for forward recovery.

A `BLOCKED` result is not overwritten. Follow
[`production-admission-recovery.md`](../production-admission-recovery.md),
collect replacement evidence, create a new `admission_id`, rerun every gate,
and retain the complete attempt history.
