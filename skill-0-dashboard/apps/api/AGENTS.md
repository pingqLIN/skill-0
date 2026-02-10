<<<<<<< Updated upstream
<<<<<<< Updated upstream
# DASHBOARD API — FastAPI Governance Backend

## OVERVIEW

REST API for governance dashboard: stats, skills, reviews, scans, audit.

## STRUCTURE

```
api/
├── main.py           # FastAPI app, CORS, router mounting
├── config.py         # Configuration
├── dependencies.py   # Dependency injection
├── routers/          # Endpoint modules
│   ├── stats.py      # /api/stats
│   ├── skills.py     # /api/skills
│   ├── reviews.py    # /api/reviews
│   ├── scans.py      # /api/scans
│   └── audit.py      # /api/audit
├── schemas/          # Pydantic models
└── services/         # Business logic
```

## WHERE TO LOOK

| Task | File |
|------|------|
| Add endpoint | `routers/{domain}.py` |
| Add request/response model | `schemas/{domain}.py` |
| Add business logic | `services/{domain}.py` |

## CONVENTIONS

- All routers mounted at `/api` prefix
- Pydantic v2 models
- Tags match router names for OpenAPI grouping

## COMMANDS

```bash
uvicorn main:app --reload --port 8001
# Docs: http://localhost:8001/docs
# ReDoc: http://localhost:8001/redoc
```
=======
=======
>>>>>>> Stashed changes
# DASHBOARD API — FastAPI Governance Backend

## OVERVIEW

REST API for governance dashboard: stats, skills, reviews, scans, audit.

## STRUCTURE

```
api/
├── main.py           # FastAPI app, CORS, router mounting
├── config.py         # Configuration
├── dependencies.py   # Dependency injection
├── routers/          # Endpoint modules
│   ├── stats.py      # /api/stats
│   ├── skills.py     # /api/skills
│   ├── reviews.py    # /api/reviews
│   ├── scans.py      # /api/scans
│   └── audit.py      # /api/audit
├── schemas/          # Pydantic models
└── services/         # Business logic
```

## WHERE TO LOOK

| Task | File |
|------|------|
| Add endpoint | `routers/{domain}.py` |
| Add request/response model | `schemas/{domain}.py` |
| Add business logic | `services/{domain}.py` |

## CONVENTIONS

- All routers mounted at `/api` prefix
- Pydantic v2 models
- Tags match router names for OpenAPI grouping

## COMMANDS

```bash
uvicorn main:app --reload --port 8001
# Docs: http://localhost:8001/docs
# ReDoc: http://localhost:8001/redoc
```
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
