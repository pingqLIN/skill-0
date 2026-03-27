# Skill-0 Schema Compatibility Note

Updated: `2026-03-27`

## Purpose

This note documents the main legacy-to-canonical mappings used during the `2.4.x` contract recovery effort.

The live schema remains:

- [`schema/skill-decomposition.schema.json`](<repo-root>/schema/skill-decomposition.schema.json)

The compatibility logic lives in:

- [`tools/schema_contract.py`](<repo-root>/tools/schema_contract.py)

## Legacy To Canonical Mapping

### Meta

- legacy `claude__name` style identifiers are normalized to `claude__skill__name`
- legacy `mcp__name` style identifiers are normalized to `mcp__tool__name` or `mcp__server_internal__name` based on `skill_layer`
- legacy `schema_version` values are updated to the live canonical schema version during normalization

### Actions

- legacy `type` is mapped to canonical `action_type`
- missing `name` is derived from `description` or `content`
- missing `description` falls back to `content` or `name`
- missing `deterministic` defaults to `true`
- missing `side_effects` defaults to `[]`

### Rules

- legacy `condition` is mapped to canonical `condition_expression`
- legacy `output` is mapped to canonical `returns`
- missing `name` is derived from `description` or `condition`
- `condition_type` is inferred from wording when absent
- non-canonical `fail_action` values are mapped onto the allowed enum

### Directives

- legacy `type` is mapped to canonical `directive_type`
- missing `name` is derived from `description`
- missing `description` falls back to `content` or `name`

### Execution Paths

- missing `path_id` is backfilled by stable enumeration
- missing `condition` falls back to `path_name`, `description`, or `default`
- missing `expected_outcome` falls back to `description`

## Boundary

Compatibility helpers exist to migrate legacy artifacts. They are not permission to keep emitting legacy shapes forever.

New parser work should emit canonical fields directly.

## Validation

Use:

```bash
.venv/bin/python tools/validate_skill_schema.py parsed
```

If a file only passes after local custom handling outside `tools/schema_contract.py`, that handling is not part of the accepted compatibility layer and should be treated as drift.
