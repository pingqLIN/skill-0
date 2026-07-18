# Runtime v4 Production Operations

This is the authoritative operator runbook for the Runtime v4 production boundary. See [runtime-production-operations.zh-tw.md](runtime-production-operations.zh-tw.md) for the Traditional Chinese companion.

All deployments must also satisfy the mandatory controls and external evidence
requirements in [`production-security-policy.md`](production-security-policy.md).

## Storage topology

Runtime v4 has three independent SQLite stores. A release is not production-ready when any store is missing.

| Store | Production path | Ownership |
|---|---|---|
| Search index | `/app/data/skills.db` | Core API read/write |
| Governance | `/app/governance/db/governance.db` | Dashboard API read/write; Core API read-only |
| Runtime ledger | `/app/runtime-data/runtime.db` | Core API read/write |

`docker-compose.prod.yml` gives the Runtime ledger its own named volume and mounts the governance volume read-only into the Core API. The Core API waits for the Dashboard API health check before its fail-closed startup doctor runs.

## Required production configuration

- `SKILL0_RUNTIME_BINDING_KEY`: independent secret, at least 32 characters, never equal to `JWT_SECRET_KEY`.
- `SKILL0_RUNTIME_DECISION_ACTORS`: explicit comma-separated JWT subjects.
- `SKILL0_RUNTIME_HITL_TTL_SECONDS`: 300–604800; production default is 86400.
- `SKILL0_RUNTIME_JOURNAL_MODE=WAL`.
- `SKILL0_RUNTIME_DB_PATH=/app/runtime-data/runtime.db`.
- `SKILL0_GOVERNANCE_DB_PATH=/app/governance/db/governance.db`.
- `SKILL0_RUNTIME_ALLOW_INITIALIZE=false` during normal operation.

The doctor reports only configuration names and structural findings. It never prints secret values.

## First start and upgrade

1. Restore or provision `skills.db` and `governance.db` before accepting traffic. A clean public checkout intentionally has neither production identity nor approvals.
2. Start the Dashboard API so the governance volume is present and its schema is current.
3. For the first intentional provisioning boot only, set `SKILL0_RUNTIME_ALLOW_INITIALIZE=true`. If the Runtime ledger is missing while this flag is false, startup fails instead of silently creating an empty history.
4. Start the Core API. Its entrypoint initializes or migrates `runtime.db`, then runs:

   ```bash
   python /app/scripts/runtime_doctor.py --production --json
   ```

5. Return `SKILL0_RUNTIME_ALLOW_INITIALIZE=false`, restart the Core API, and verify the doctor again.
6. Start the web service only after both APIs are healthy.

Legacy HITL rows without `expires_at` are treated as expired. Legacy execution bases without `governance_revision_id` are non-resumable. Do not rewrite those attestations: start a fresh run against the current approved canonical revision.

## HITL deadline

- Pending decisions and approved-but-unconsumed action approvals expire at `expires_at`.
- Expired items cannot be decided or claimed for resume and appear in the Dashboard `expired` queue.
- Rejecting, confirming recovery, or consuming an approval does not occur automatically.
- Changing the TTL affects newly created queue items only; persisted deadlines remain immutable.

## Backup and release gate

Back up all three stores together while the services are online:

```bash
SKILL0_DB_PATH=/path/to/skills.db \
SKILL0_GOVERNANCE_DB_PATH=/path/to/governance.db \
SKILL0_RUNTIME_DB_PATH=/path/to/runtime.db \
BACKUP_DIR=/secure/skill0-backups \
./scripts/backup_db.sh
```

Then validate WAL mode, recency, schema, parsed artifacts, and security configuration:

```bash
BACKUP_DIR=/secure/skill0-backups ./scripts/check_db_health.sh
python scripts/runtime_doctor.py \
  --production \
  --require-backups \
  --backup-dir /secure/skill0-backups \
  --json
```

The release gate fails when initialization remains enabled or any store, required Runtime/governance column, current backup, parsed corpus, actor allowlist, binding key, TTL, or production Runtime WAL contract is missing.

## Restore and restart rehearsal

Use only an isolated project name. The helper creates disposable volumes, initializes a rehearsal governance store, validates all three stores, performs online SQLite backup/restore verification, restarts the Core API, and reruns the doctor:

```powershell
pwsh -File scripts/rehearse_prod_compose.ps1
```

For a real restore:

1. Stop writers to all three stores.
2. Keep the damaged files for forensic recovery; do not overwrite the only copy.
3. Restore one matching `skills_*`, `governance_*`, and `runtime_*` backup set.
4. Start the Dashboard API, then Core API, then web.
5. Run the production doctor with `--require-backups` and verify API/web health.
6. Create a fresh governed dry run; do not resume a pre-restore approval unless its exact execution and governance basis is still present.

## Binding-key rotation

The Runtime binding key deliberately has no silent fallback key ring.

1. Freeze new Runtime runs and HITL decisions.
2. Drain approved items or wait for their immutable deadlines to expire.
3. Back up all three stores and pass the release gate.
4. Rotate `SKILL0_RUNTIME_BINDING_KEY` in the secret manager and restart the Core API.
5. Rerun the production doctor and a fresh governed dry run.

Approvals created under the previous key become non-resumable. This is fail-closed behavior, not data loss; the decision and event evidence remain in the ledger.

## Rollback

Rollback means restoring the matching three-store backup set and the previous application image/configuration. Never downgrade only the Runtime schema while keeping newer event data. If the rollback image cannot understand current governance revisions or HITL deadlines, leave Runtime disabled and preserve the stores for forward recovery.
