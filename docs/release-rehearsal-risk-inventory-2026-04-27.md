# Skill-0 Release Rehearsal Risk Inventory

Date: `2026-04-27`
Scope: `production compose config dry-run, env/CORS/auth/healthcheck/DB persistence risk inventory`
Status: `config dry-run complete; full compose up not executed`

---

## Evidence

Production config dry-run was verified with the example production env file:

```bash
docker compose --env-file .env.production.example -f docker-compose.prod.yml config
```

Observed CORS values in rendered config:

```text
CORS_ORIGINS: https://your-domain.com
```

Fail-fast behavior was also verified with the local `.env`, where `CORS_ORIGINS` is empty:

```bash
docker compose -f docker-compose.prod.yml config
```

Expected result:

```text
required variable CORS_ORIGINS is missing a value
```

This prevents production compose from silently starting with an empty CORS allowlist.

---

## Risk Inventory

| Area | Current Evidence | Risk | Next Action |
|---|---|---|---|
| CORS | `docker-compose.prod.yml` now requires non-empty `CORS_ORIGINS` | Wrong env file can still block startup | Keep fail-fast; document production env setup |
| Auth | `.env.production.example` still contains placeholder credentials/secrets | Compose config can render with placeholders | Add preflight script to reject `CHANGE_ME_*` before deploy |
| Healthchecks | Dockerfiles define healthchecks; prod compose depends on `service_healthy` for API/dashboard | Full service startup not rehearsed in this stage | Run full `docker compose --env-file <real-prod-env> -f docker-compose.prod.yml up --build` in a controlled environment |
| DB persistence | Named volumes exist for `skills.db` and `governance.db` | Backup/restore not rehearsed in this stage | Add backup/restore smoke test using named volumes |
| Dependency vulnerabilities | `docs/security/dependabot-vulnerability-inventory-2026-04-27.md` lists 7 advisories | Safe bumps not applied in this stage | Upgrade `vite`, `axios`, `postcss`; verify web tests/build |
| Dual DB identity | `skills.db` and `governance.db` remain separate stores | Skill identity drift can go unnoticed | Add identity drift report command |

---

## Minimum Future Rehearsal

Before claiming production readiness, run:

```bash
docker compose --env-file .env.production.example -f docker-compose.prod.yml config
docker compose --env-file <real-prod-env> -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps
curl -fsS http://127.0.0.1:${API_PORT:-8080}/health
curl -fsS http://127.0.0.1:${WEB_PORT:-3080}/
docker compose -f docker-compose.prod.yml down
```

Do not use `.env.production.example` for a real deployment; it is only a config-rendering fixture.
