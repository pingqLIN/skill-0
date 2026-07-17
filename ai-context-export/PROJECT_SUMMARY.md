# Skill-0 Runtime v4 Project Summary

Skill-0 decomposes skills and MCP tools into a canonical schema, validates and indexes the parsed corpus, exposes Core and Dashboard APIs, and provides revision-aware governance.

Runtime v4 adds an append-only event ledger, evidence projection, recovery data model, deterministic simulation, and authenticated dry-run API. The closeout release is deliberately limited to one-host Docker Compose with `skills.db`, `governance.db`, and `runtime.db`.

Unsupported: real action execution, non-dry-run adapters, multi-node/HA, Redis/PostgreSQL, Kubernetes, new schema/parser features, UI redesign, and major architecture or dependency migrations.

Current authority starts at [`CURRENT_STATE.md`](CURRENT_STATE.md), [`../docs/README.md`](../docs/README.md), and [`../docs/closeout/FINAL_REPORT.md`](../docs/closeout/FINAL_REPORT.md).
