# Skill-0 Contract Decision

Updated: `2026-03-27`
Status: `accepted`

## Decision

The authoritative schema contract for `skill-0` is:

- [`schema/skill-decomposition.schema.json`](<repo-root>/schema/skill-decomposition.schema.json)

The canonical normalization and compatibility helpers for that contract are:

- [`tools/schema_contract.py`](<repo-root>/tools/schema_contract.py)
- [`tools/validate_skill_schema.py`](<repo-root>/tools/validate_skill_schema.py)
- [`tools/normalize_parsed_skills.py`](<repo-root>/tools/normalize_parsed_skills.py)

## Scope

This decision applies to:

- parser output
- checked-in `parsed/*.json`
- search/embedder consumers
- CI schema validation
- repo documentation that states schema shape, version, or field semantics

## Source Of Truth Order

When conflicts exist, resolve them in this order:

1. Live schema in `schema/skill-decomposition.schema.json`
2. Canonical normalization logic in `tools/schema_contract.py`
3. Parser output and checked-in parsed dataset
4. Search/governance/dashboard consumers
5. README / AGENTS / review docs

Docs do not override code or schema.

## Required Canonical Expectations

- `meta.schema_version` must reflect the live schema version.
- `meta.skill_id` must use canonical `(claude|mcp)__[scope]__[name]` form.
- `decomposition.actions[*]` must expose canonical `name`, `action_type`, `description`, `deterministic`, and `side_effects`.
- `decomposition.rules[*]` must expose canonical `name`, `condition_expression`, `condition_type`, and `returns`.
- `decomposition.directives[*]` must expose canonical `name`, `directive_type`, and `description`.

## Implementation Rule

If a parser or imported artifact produces a legacy shape, it must be normalized before it is treated as contract-compliant.

That means:

- parsers should emit canonical fields directly when practical
- normalization may backfill legacy artifacts during migration
- CI must validate the final artifact shape, not the pre-normalized intermediate shape

## Consumer Rule

Search, governance, and dashboard code should consume canonical fields first.

Compatibility aliases may exist during migration, but new work should not introduce fresh dependencies on legacy field names.

## Verification Gate

The minimum repo gate for contract drift is:

```bash
.venv/bin/python tools/validate_skill_schema.py parsed
```

CI already runs this validation against `parsed/`.
