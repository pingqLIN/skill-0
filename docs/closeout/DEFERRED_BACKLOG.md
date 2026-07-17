# Runtime v4 Deferred Backlog

Updated: `2026-07-17`

Every item below is explicitly non-blocking. None belongs in the current closeout TODO.

| ID | Deferred item | Reopen only when |
|---|---|---|
| D-01 | Full API router/service refactor | API churn is a measured bottleneck |
| D-02 | Persistent/distributed rate limiter | Multi-worker or multi-instance is approved |
| D-03 | Redis or PostgreSQL | Shared-state need is documented |
| D-04 | Kubernetes or HA | Availability SLO and operator capacity exist |
| D-05 | Real production action adapter | A separate threat model and certification project exists |
| D-06 | Non-dry-run Runtime API | Product decision and approval UX are complete |
| D-07 | New schema version | Failure case, migration, and fixture exist |
| D-08 | Complex-skill parser expansion | A separate milestone is approved |
| D-09 | Intent-router expansion | Operator demand is measured |
| D-10 | Dashboard redesign | Research identifies blocking UX defects |
| D-11 | OpenTelemetry/distributed tracing | Multiple instances need correlation |
| D-12 | Raise global coverage above 85% | A separate quality milestone is approved |
| D-13 | SBOM, image signing, provenance | Distribution policy requires them |
| D-14 | Dependency-management migration | Existing reproducibility demonstrably fails |
| D-15 | Mass historical-doc archive/move | A dedicated migration owns redirects and link checks |
| D-16 | Merge Core and `skill-0-GUI` | An architecture decision approves a monorepo |
| D-17 | External GUI mirror redesign | The GUI owner schedules it separately |
| D-18 | Performance/load benchmark | Capacity target and workload profile exist |
| D-19 | Multi-tenant auth/RBAC | A multi-tenant requirement is approved |
| D-20 | License/model asset SBOM | External distribution or model replacement requires it |

If any deferred item becomes necessary to pass a Core gate, stop and re-evaluate the release boundary before implementation.
