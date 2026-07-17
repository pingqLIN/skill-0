# Runtime v4 Known Limitations

Updated: `2026-07-17`

These are accepted limits of the governed pilot, not release blockers.

- Runtime execution is deterministic simulation and dry-run only. No real action adapter is present.
- Deployment is one host and one Docker Compose project; multi-node, HA, and Kubernetes are unsupported.
- State is split across three SQLite stores. Backup and restore treat the set as one operational recovery unit.
- Runtime initialization is allowed only for first provisioning and must be disabled for the release doctor and steady-state restart.
- Rate limiting is process-local. It resets on restart and is not consistent across multiple workers or instances.
- The `skill-0-GUI` mirror remains an external companion and is not part of the Core Runtime gate.
- Embedding/model-cache availability can affect indexing or semantic-search maintenance, but not the recorded Runtime v4 dry-run rehearsal.
- The pilot makes no throughput, load, multi-tenant, or availability-SLO claim.
