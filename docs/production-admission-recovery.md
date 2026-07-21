# Production Admission BLOCKED Recovery

This runbook defines re-entry after a Runtime Asset Production Admission v1
attempt returns `FAIL` / `BLOCKED`. See
[production-admission-recovery.zh-tw.md](production-admission-recovery.zh-tw.md)
for the Traditional Chinese companion.

`BLOCKED` is a safe terminal decision for one admission attempt. It is not an
instruction to weaken a verifier, reuse stale evidence, edit a signed package,
or force deployment.

## Immediate response

1. Do not deploy, promote, or continue using the blocked package.
2. Preserve the exact package bytes, referenced evidence, verifier JSON result,
   keyring revision/digest, runner identity, and timestamp.
3. Record the failed `admission_id`, `release_id`, reason codes, and decision in
   the operator audit system.
4. If deployment already occurred, stop further promotion and apply the approved
   rollback or containment procedure. Do not delete the affected stores or the
   only forensic copy.

## Classify the blocker

| Check or reason family | Required response |
|---|---|
| `schema_validation`, `input_loading` | Rebuild the package from authoritative source records. Never patch a signed package in place. |
| `keyring_trust_anchor`, `operator_signature`, `revocation_state` | Contact the keyring/signing authority. Replace or reauthorize through the protected process; never bypass or override trust. |
| `commit_binding`, `release_binding` | Return to the exact clean release checkout. Rebuild and redeploy from the intended commit if the observed release differs. |
| `image_digest_binding`, `model_artifact_binding` | Re-observe the deployed immutable image or complete-tree model digest. Reconcile the deployment or build a new release package. |
| `evidence_references`, `evidence_freshness` | Collect new artifacts from the authoritative scanner, test, or rehearsal system; hash them and set real observation/expiry times. |
| `external_control_evidence` | Have an authorized operator produce a fresh, complete external-control bundle and attachments for the exact release and environment. |
| `verifier_execution` | Treat the result as unknown. Repair the verifier environment and rerun; do not infer success. |

Authentication, authorization, permission, policy, or protected-runner failures
must be escalated to the responsible human owner. They are not retryable by
loosening controls.

## Re-entry procedure

1. Collect every missing or replacement evidence item from the system that
   actually observed it.
2. Confirm the intended Git commit/tree, production environment identity,
   deployed `api`/`dashboard`/`web` digests, model digest, Compose/policy
   digests, and trusted keyring digest.
3. Rerun the underlying security scan, regression test, rehearsal, external
   control, and repository gates whose evidence is missing, expired, revoked,
   or release-bound to a different target.
4. Create a new package with a new `admission_id`. Do not edit, overwrite, or
   reuse the blocked package.
5. Obtain a new operator approval and signature only after all replacement
   evidence is fixed and current.
6. Run `tools/runtime_admission_check.py` from the exact clean release checkout.
7. Record the new verifier result as a separate admission attempt.
8. Admit only when the result is exit `0`, `status: PASS`, with no failed or
   unknown checks. Otherwise record a rejection and repeat from step 1 only
   after the cause changes.

Acknowledgement, timeout, missing output, partial output, or an unavailable
review is not approval.

## Audit history

Retain an append-only chain for every attempt:

- admission and release IDs;
- source commit/tree and all release digests;
- package digest and signature/key ID;
- evidence IDs, paths or protected object IDs, and digests;
- keyring revision/digest and revocation state;
- verifier version/commit, output, exit code, and run timestamp;
- operator decision, reason, and actor identity under the applicable privacy
  policy; and
- replacement or rollback relationship to earlier attempts.

Never delete or rewrite a rejected attempt to make a later attempt appear to be
the original approval. Redacted reporting copies must remain traceable to the
retained signed bytes.

## Rollback after a blocked deployed release

Use the operator-approved rollback procedure from
[`runtime-production-operations.md`](runtime-production-operations.md):

1. stop writers to all three stores;
2. preserve damaged or suspect files for forensic recovery;
3. restore one matching `skills.db`, `governance.db`, and `runtime.db` backup set;
4. restore the matching prior application images and configuration;
5. start Dashboard API, Core API, and web in the documented order;
6. rerun the production doctor with current backup requirements; and
7. create a fresh governed dry run before reopening the admitted boundary.

Never downgrade only the Runtime schema while retaining newer event data. If
the rollback release cannot interpret current governance revisions or HITL
deadlines, keep Runtime disabled and preserve the stores for forward recovery.
