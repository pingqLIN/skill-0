# SKILL-0-DASHBOARD — Monorepo

## OVERVIEW

Governance dashboard for skill-0. React frontend + FastAPI backend as separate apps.

## STRUCTURE

```
skill-0-dashboard/
├── apps/
│   ├── api/    # FastAPI governance API (Python)
│   └── web/    # React dashboard (TypeScript)
```

## WHERE TO LOOK

| Task | Location |
|------|----------|
| Add API endpoint | `apps/api/routers/` |
| Add UI component | `apps/web/src/components/` |
| Add page | `apps/web/src/pages/` |
| API schemas | `apps/api/schemas/` |

## COMMANDS

```bash
# API (from apps/api/)
uvicorn main:app --reload --port 8001

# Web (from apps/web/)
npm run dev      # Dev server
npm run build    # Production build
npm run lint     # ESLint
```

## NOTES

- API and Web are independent — no shared dependencies
- API uses parent's `skills.db` via relative path
- Web proxies API calls in dev mode
