# Production Admission Operator Handoff

This is the human handoff for Runtime Asset Production Admission v1. See
[production-operator-handoff.zh-tw.md](production-operator-handoff.zh-tw.md) for
the Traditional Chinese companion and
[`runtime-production-admission-v1.md`](contracts/runtime-production-admission-v1.md)
for the authoritative contract.

Current state:

- Repository Gate: `GO`
- Production Admission: `WAITING_FOR_OPERATOR_EVIDENCE`

The repository supplies the schema and fail-closed verifier. A human production
operator must supply the actual deployment identity, observations, and
signatures. An AI agent cannot generate or substitute these facts.

## Human-supplied inputs

The operator must obtain all of the following from authoritative production or
release systems:

1. A separately administered trusted keyring matching
   [`production-external-control-keyring.schema.json`](../schema/production-external-control-keyring.schema.json).
2. The exact SHA-256 of that keyring, injected as
   `SKILL0_EXTERNAL_CONTROL_TRUSTED_KEYRING_SHA256` by a protected runner or
   equivalent control that the evidence submitter cannot change.
3. A real signed external-control bundle and every digest-addressed attachment
   required by
   [`production-external-control-evidence.schema.json`](../schema/production-external-control-evidence.schema.json).
4. The stable identity of the actual production environment.
5. The immutable deployed registry/content digest for each of `api`,
   `dashboard`, and `web`. Tags and local image IDs are not sufficient.
6. The approved complete-tree model artifact digest observed for the mounted,
   read-only production model.
7. Current security scan, regression test, and production rehearsal artifacts,
   each with its real digest, observation time, and expiry.
8. A production admission operator whose key is authorized for the environment
   with the exact `production-admission-approver` role, plus the operator's
   Ed25519 signature over the final package. An external-control-only role is
   insufficient.
9. Security/release approval and an actionable rollback path for the prior
   application images/configuration and matching three-store backup set.

Do not send private keys, credentials, cookies, tokens, secret-manager output,
private topology exports, raw logs containing private data, or a real keyring to
an AI agent. Do not commit the package, keyring, bundle, attachments, private
operator ID, or trust-anchor configuration to this repository.

## Build the protected package

Create `production-admission-package.json` in the protected evidence location,
not in the Git checkout. Populate it only after the release commit, deployed
digests, model digest, evidence artifacts, and environment identity are final.
Validate its structure against
[`production-admission-package.schema.json`](../schema/production-admission-package.schema.json).

The root `signature` is Ed25519 over the UTF-8 canonical JSON package with the
entire root `signature` property omitted, keys sorted, and separators set to
`,` and `:` without extra whitespace. The resulting base64 signature, key ID,
operator metadata, approval time, and expiry belong in the final package. Use a
controlled signing service or operator-held key; the repository intentionally
does not provide a command that handles the private key.

The existing external-control bundle is signed separately under its own schema.
Its release binding must be byte-for-byte equal to the package release binding,
including Git commit/tree, Compose/policy/keyring, model, and all image digests.

## Run the gate

Use a dedicated clean checkout at the exact commit being admitted. The current
development checkout, a dirty worktree, or a checkout containing untracked
release inputs will fail closed.

```powershell
$env:SKILL0_EXTERNAL_CONTROL_TRUSTED_KEYRING_SHA256 = '<protected-runner-value>'

python tools/runtime_admission_check.py `
  C:\secure-evidence\production-primary\production-admission-package.json `
  --keyring C:\secure-keyring\skill0-production-keyring.json `
  --evidence-root C:\secure-evidence\production-primary `
  --repo-root C:\release-checkouts\skill-0
```

Set the environment variable through the protected runner's secret/configuration
facility; do not paste its real value into chat, source files, logs, or shell
history. The command prints one machine-readable JSON object.

- Exit `0`, `status: PASS`: the supplied package is cryptographically and
  structurally eligible for admission within the existing dry-run-only Runtime
  boundary.
- Exit `2`, `status: FAIL`, `release_gate: BLOCKED`: do not admit or reuse the
  package. Follow
  [`production-admission-recovery.md`](production-admission-recovery.md).

Archive the package, referenced evidence, trusted keyring revision/digest,
verifier output, runner identity, and decision in the operator-controlled audit
system. Redact only presentation copies; retain the original signed bytes under
the applicable retention and access policy.

## What an AI agent cannot provide

An AI agent cannot truthfully provide or manufacture:

- an operator signature or private signing key;
- a trusted keyring or its protected trust-anchor configuration;
- a real production environment identity;
- a deployed image digest observed from the production registry/runtime;
- a mounted model artifact digest observed in production;
- proof that physical security controls are present; or
- a human security/release approval.

Synthetic signatures and digests are permitted only inside isolated automated
tests. They are never production admission evidence.
