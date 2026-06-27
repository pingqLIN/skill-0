# Skill-0 and UniText Alignment

Updated: `2026-06-19`
Status: `Current boundary contract`

## Decision

Skill-0 and UniText should integrate through portable artifacts and governance checks, not through direct runtime configuration mutation.

Skill-0 remains the decomposition, schema, semantic search, and governance sidecar data layer. UniText remains the broader canonical registry, runtime projection, and governance backbone for shared skills and agent runtimes.

## Responsibility Boundary

| Area | Owner | Contract |
|---|---|---|
| Canonical skill registry | UniText | Export source skill artifacts and registry metadata |
| Runtime skill projection | UniText | Project selected skills into runtime-specific locations |
| Decomposition schema | Skill-0 | Validate parsed JSON against `schema/skill-decomposition.schema.json` |
| Search/index/governance sidecar | Skill-0 | Parse, validate, index, compare, scan, test, and audit imported artifacts |
| Agent instructions | AGENTS / repo-local overlays | Define local workflow and safety constraints |
| Runtime configuration changes | AI runtime governance process | Require simulation, backup, audit log, verification, and rollback |

## Integration Model

Use this flow for read-only or reviewer workflows:

1. UniText exports a registry snapshot or source skill artifact set.
2. Skill-0 ingests the artifact set through parser/normalizer tooling.
3. Skill-0 validates the generated parsed JSON against the live schema.
4. Skill-0 indexes and reviews the artifacts through search and governance surfaces.
5. Drift is reported through checksums, parsed artifact IDs, and identity reports.

This keeps Skill-0 useful to UniText without making Skill-0 depend on a specific local UniText path.

## Non-Goals

1. Do not hard-code `Q:\UniText`, `C:\Dev\AI_UNIFIED`, or any user-machine path as a Skill-0 product requirement.
2. Do not use Skill-0 to directly edit Codex, Claude, Gemini, VS Code, Windsurf, or other runtime settings.
3. Do not run AI runtime governance `-Apply` operations as part of a Skill-0 parse/index/review task.
4. Do not duplicate UniText registry rules into Skill-0 as normative copies.
5. Do not present Skill-0 fidelity, similarity, or coverage checks as strict equivalence proof.

## Compatible Governance Rules

Skill-0 work is compatible with UniText and AI runtime governance when it follows these rules:

1. Use read-only inventory and simulation before any cross-runtime change.
2. Keep source-of-truth ownership explicit in docs and reports.
3. Store local runtime evidence as artifacts, not hidden assumptions.
4. Treat path/config changes as a separate change plan with rollback.
5. Use `<repo-root>`, `<registry-root>`, or explicit user-provided paths in publishable docs.
6. Keep public docs free of private machine-specific state unless the file is clearly local-only.

## Risk Notes

| Risk | Why it matters | Resolution |
|---|---|---|
| Path coupling | Local paths can become false product assumptions | Use placeholders and import/export contracts |
| Authority drift | UniText and Skill-0 can both describe skill lifecycle | Keep UniText as registry authority and Skill-0 as sidecar analysis authority |
| Hidden mutation | Runtime governance scripts can mutate many tools | Require explicit change plan, backup, simulation, and rollback |
| Context bloat | Copying every governance rule into every repo increases agent overhead | Link to authority docs and keep repo entrypoints concise |
| Public/private leak | Runtime paths and planning notes may be private | Keep local evidence in ignored outputs or clearly scoped reports |

## Verification Gates

For Skill-0-side changes:

```powershell
.venv\Scripts\python.exe tools\validate_skill_schema.py parsed
.venv\Scripts\python.exe tools\check_doc_status_markers.py
.venv\Scripts\python.exe tools\check_shared_docs.py
.venv\Scripts\python.exe tools\report_db_identity_drift.py --allow-missing-db
```

For future UniText import snapshots:

```powershell
.venv\Scripts\python.exe tools\validate_skill_schema.py parsed
.venv\Scripts\python.exe -m vector_db.search --db skills.db --parsed-dir parsed index
.venv\Scripts\python.exe tools\report_db_identity_drift.py --allow-missing-db --format json
```

For any future runtime configuration change:

1. Produce a change plan with risk level.
2. Produce simulation output.
3. Create backups.
4. Apply only after explicit approval.
5. Verify post-state.
6. Record rollback instructions.

## Summary

The best alignment is layered cooperation: UniText governs registry/runtime projection; Skill-0 governs decomposition/search/review evidence; runtime governance governs actual tool configuration changes. The systems should exchange artifacts and reports, not silently mutate each other.
