# Skill-0 Production Admission Phase 2 Operator Checklist

This file is the authoritative human preparation checklist for Phase 2. See
[PHASE2_OPERATOR_CHECKLIST.zh-tw.md](PHASE2_OPERATOR_CHECKLIST.zh-tw.md) for the
Traditional Chinese companion.

Production Admission remains `WAITING_FOR_OPERATOR_EVIDENCE`. Every item below
must come from an authorized human operator and the exact production release.
Do not substitute test fixtures, repository examples, AI-generated values, local
image IDs, mutable tags, or historical evidence.

## Human-provided requirements

- [ ] Production environment identity.
- [ ] Trusted keyring location controlled independently from the evidence
  submitter.
- [ ] Immutable deployed image digests for the exact API, Dashboard, and Web
  images.
- [ ] Approved complete-tree model artifact digest observed for the mounted
  production artifact.
- [ ] Fresh security evidence bound to the exact release and environment.
- [ ] Fresh regression evidence for the exact release candidate.
- [ ] Fresh production rehearsal evidence for the exact release candidate and
  environment boundary.
- [ ] Signature from an authorized operator with the exact
  `production-admission-approver` role.

## Operator checks before signing

- [ ] The Git commit and tree are clean and match the release candidate.
- [ ] Policy, Compose, trusted keyring, model, and image digests match the
  release binding.
- [ ] Evidence is complete, current, untampered, environment-specific, and
  stored outside the repository in protected storage.
- [ ] The signer is not relying on repository test fixtures as production
  evidence.
- [ ] The existing verifier returns `VERIFIED` without bypass or exception.

## Prohibited substitutions

An AI agent must not create or sign `production-admission-package.json`, invent
operator identity or signatures, derive deployment digests from local examples,
or present synthetic evidence as production evidence. Missing evidence remains
blocked.
