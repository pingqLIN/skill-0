# Skill-0 Phase 1 Freeze & Handoff Guide

This file is the authoritative entry point for the Phase 1 Freeze & Handoff
Package. See [HANDOFF_README.zh-tw.md](HANDOFF_README.zh-tw.md) for the
Traditional Chinese companion.

## Where the project is now

Production Admission Phase 1 is `COMPLETE` at freeze source commit
`71ce496baa3c1076679f244c82700c3bf65d1297`. The repository contains the active
admission contract, schema, fail-closed verifier, direct tests, security
integration, bilingual operator handoff, and recovery documentation.

Production Admission Phase 2 is `WAITING_FOR_OPERATOR_EVIDENCE`. No production
environment has been admitted by this package.

## Read in this order

1. [CURRENT_STATE.md](CURRENT_STATE.md) — compact current state and limitations.
2. [PHASE1_FREEZE_RECORD.md](PHASE1_FREEZE_RECORD.md) — frozen scope and
   verification record.
3. [PHASE2_OPERATOR_CHECKLIST.md](PHASE2_OPERATOR_CHECKLIST.md) — human-only
   requirements for the next gate.
4. [Runtime Production Admission v1](docs/contracts/runtime-production-admission-v1.md)
   — authoritative admission contract.
5. [Production Operator Handoff](docs/production-operator-handoff.md) and
   [Recovery Runbook](docs/production-admission-recovery.md) — protected evidence
   workflow and fail-closed re-entry.

## What the next agent must not modify

Do not modify the verifier logic, schema, security model, production admission
contract, Runtime authority boundary, or ARD/Evidence semantics as part of this
handoff. Do not add a real adapter, enable non-dry-run execution, deploy, expose
a public route, or create a production package.

Any future functional change requires a separately scoped, reviewed change set.
It is not part of the Phase 1 freeze package.

## What the next agent may do

- Explain or verify the frozen repository state using the linked authoritative
  files.
- Re-run repository tests and schema validation without inventing evidence.
- Help an authorized operator understand the Phase 2 checklist.
- Validate the structure of operator-supplied artifacts only after the operator
  provides them through an approved protected workflow.
- Record genuine verification results with exact source and evidence state.

## What requires human intervention

- Identify the production environment.
- Provide the independently controlled trusted keyring location.
- Observe and provide the exact deployed image and mounted model digests.
- Supply fresh security, regression, rehearsal, and external-control evidence.
- Review and sign as an authorized `production-admission-approver`.
- Decide whether a verified package authorizes deployment or promotion.

An AI agent is not the production approver and must not sign or fabricate any of
these items.

## Verification commands

From the repository root on Windows:

```powershell
.\.venv\Scripts\python.exe -m pytest tests skill-0-dashboard\apps\api\tests -q --timeout=120
.\.venv\Scripts\python.exe -m pytest tests\test_runtime_admission_check.py -q --timeout=120
.\.venv\Scripts\python.exe tools\validate_skill_schema.py parsed
git diff --check
```

Frontend validation runs from `skill-0-dashboard/apps/web`:

```powershell
npm.cmd run lint
npm.cmd test
npm.cmd run build:ci
```

These commands validate repository behavior only. They do not produce or
replace production evidence.

## Stop conditions

Stop and report `WAITING_FOR_OPERATOR_EVIDENCE` if any required human evidence
is missing. Treat stale, mismatched, tampered, revoked, wrong-environment,
wrong-release, synthetic, or unauthorized evidence as blocked. Never promote an
unknown result to `VERIFIED`.
