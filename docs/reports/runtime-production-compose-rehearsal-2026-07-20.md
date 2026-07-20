# Runtime Production Compose Rehearsal Evidence

- Date: `2026-07-20`
- Status: **TECHNICAL_REHEARSAL_PASS / PRODUCTION_NO_GO**
- Authority: English version; see the Traditional Chinese companion for reference
- Remediation commit: `0b3acbb`

## Scope

This report records a local, isolated execution of the production Compose
contract. It validates repository-controlled startup, storage, health, governed
dry-run, backup/restore, restart, and cleanup behavior. It is not a deployment,
public-exposure approval, vulnerability exception, or operator production
decision.

The rehearsal used a unique Compose project, free loopback ports `28080` and
`23080`, synthetic rehearsal-only credentials and origins, and disposable named
volumes. It did not read a real production environment file or create a public
route.

## Discovered image-boundary defect

The first live run failed while seeding the disposable Governance volume because
the Dashboard image contained the repository-local `governance/db/governance.db`.
Docker volume copy-up imported that operator state into the new named volume, so
the rehearsal seed collided with an existing canonical identity.

Commit `0b3acbb` removed `COPY governance/` from `Dockerfile.dashboard`, excluded
`governance/db/` from the Docker build context, added a regression guard, and
documented the empty-volume provisioning boundary. No database contents or
schema were changed.

## Verified rerun

The clean rerun used:

```powershell
pwsh -NoProfile -File scripts\rehearse_prod_compose.ps1 `
  -ProjectName skill0-rehearsal-20260720-1913 `
  -ApiPort 28080 `
  -WebPort 23080
```

| Gate | Evidence |
|---|---|
| Compose build and startup | API, Dashboard, and Web images built; services reached their expected health states |
| Production doctor | `healthy`; all three SQLite stores passed `quick_check`; Runtime used WAL; parsed corpus count was `196` |
| Governed Runtime | Synthetic current revision approved; dry-run status `succeeded` |
| Evidence projection | Two reads were byte-identical; no rehearsal password, JWT secret, Runtime binding key, or bearer token appeared in public Evidence/events |
| Persistence | Runtime sentinel remained present after API restart |
| Backup/restore | Online backup and restore of Index, Governance, and Runtime stores each returned `quick_check=ok`; restored Runtime sentinel matched |
| Cleanup | After `down --volumes --remove-orphans`, project containers, volumes, and networks each counted `0` |

Repository verification after the remediation reported:

- focused production contract tests: `7 passed`;
- full Python/API regression: `505 passed, 76 warnings`;
- schema validation: `196 passed, 0 failed`;
- changed-scope audit: no forbidden path, added DDL, or secret-like finding.

## Remaining production boundary

The rehearsal satisfies the repository-controlled technical rehearsal portion of
the production policy, but production remains `NO_GO`:

- the current dependency report records one Critical and two High findings in the
  API base image without a fixed Bookworm version;
- offline `local://` scans verified Dashboard at 1 Critical / 2 High and Web at
  1 Critical / 9 High after all production image stages were digest-pinned;
- external TLS, network ACL, secret-manager, host-volume, encrypted-backup, and
  monitoring evidence is outside this rehearsal; and
- no public push, release, deploy, production secret use, or risk exception was
  authorized.

The explicit exclusions remain unchanged: no FTS5 production integration,
Dashboard redesign, new Asset Type, or physical database migration.
