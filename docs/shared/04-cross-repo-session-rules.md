# Cross-Repo Session Coordination Rules

Updated: `2026-03-24`

## Purpose

This document defines how agents should work across:

- `skill-0`
- `skill-0-GUI`

It exists to prevent cross-repo drift, duplicated reasoning, and mixed implementation sessions that blur ownership.

## Relationship Between The Repositories

The current relationship is:

1. `skill-0` is the canonical parser, schema, governance, and contract repository
2. `skill-0-GUI` is the bridge, reviewer workbench, and standalone-compatible visualization repository
3. `docs/shared/` in `skill-0` is the cross-repo documentation source of truth
4. `skill-0-GUI/docs/shared/` contains mirrored copies of selected contract documents

This means the repositories are separate, but they are not independent in meaning.

## Source Of Truth Rules

Use these rules unless a document explicitly says otherwise:

- parser behavior contracts belong to `skill-0`
- schema and parser output shape belong to `skill-0`
- canonical vs standalone mode wording is shared, but the source of truth is still `skill-0/docs/shared/`
- GUI rendering and reviewer workflow behavior belong to `skill-0-GUI`
- mirrored docs in `skill-0-GUI/docs/shared/` are not independently authored

If there is a conflict, prefer:

1. `skill-0/docs/shared/*`
2. live parser/runtime behavior
3. repo-specific explanatory docs

## When To Use One Session

Use one session across both repositories when the task is primarily about:

- cross-repo architecture
- parser/bridge contract changes
- shared terminology
- canonical vs standalone semantics
- review methodology that affects both parser output and GUI wording
- planning, risk review, or dossier/report alignment

These are coordination-heavy tasks. Splitting them too early usually creates terminology drift.

## When To Split Sessions

Use separate implementation sessions when the task is primarily local to one repository.

Open a `skill-0`-focused session for:

- Python parser work
- schema changes
- governance logic
- API behavior
- parser fixtures and tests
- ingestion or vector-layer work

Open a `skill-0-GUI`-focused session for:

- React UI work
- bridge runtime behavior
- reviewer surface presentation
- frontend tests
- build and bundle issues
- standalone-mode UX or deployment

## Recommended Working Model

The preferred operating model is:

1. one cross-repo coordination session
2. one `skill-0` implementation session
3. one `skill-0-GUI` implementation session

The coordination session should decide:

- contract changes
- wording changes
- sequencing
- shared risk framing

The implementation sessions should then execute on their own repository with minimal unrelated context.

## Session Handoff Rules

When handing off from one repository session to another:

1. state which repo is the current source of truth for the change
2. state whether the change is designed, implemented, or only planned
3. list the affected contract files
4. list the affected runtime files
5. state whether mirrored docs must be synced
6. state what verification was already run

Do not hand off with only a prose summary like "GUI needs to catch up."

## Cross-Repo Change Order

When a change touches both repositories, use this order unless there is a strong reason not to:

1. update the canonical contract or design in `skill-0`
2. update `skill-0` implementation if needed
3. update shared mirrored docs in `skill-0-GUI`
4. update `skill-0-GUI` runtime or UI
5. run repository-specific verification in both repos

This prevents the GUI from silently inventing contract behavior ahead of the parser.

## Shared Docs Sync Rule

If a change affects anything documented under `skill-0/docs/shared/`, then after updating the source document:

1. run `npm run docs:sync` in `skill-0-GUI`
2. run `npm run docs:check` in `skill-0-GUI`

Do not manually edit mirrored files unless fixing a sync failure, and even then the source document should remain authoritative.

## Status Marker Rule

For cross-repo design/spec documents, use one of these markers near the top:

- `Implemented`
- `Designed`
- `Planned`

This is required when a document could otherwise be mistaken for live behavior.

## Verification Rule

Do not claim a cross-repo change is complete unless both of these are clear:

1. parser/bridge contract correctness was verified
2. GUI consumption or presentation was verified

For example:

- a parser field added in `skill-0` is not "done" if the GUI still ignores it
- a GUI card is not "contract complete" if the bridge is fabricating data with no parser-side basis

## Conflict Resolution Rule

If `skill-0` implementation and `skill-0-GUI` expectations diverge:

- do not patch over the mismatch only in GUI wording
- do not silently reinterpret parser payloads without documenting it
- fix the contract mismatch explicitly

If urgent compatibility is required, label the GUI behavior as compatibility or fallback behavior, not canonical behavior.

## Working Directory Awareness

Agents should explicitly note which repository they are currently operating in before making cross-repo changes.

Minimum expectation:

- say whether the next edits are in `skill-0`
- say whether the next edits are in `skill-0-GUI`

This reduces accidental mixed commits and mistaken file references.

## Summary

Treat the repositories as:

- separate codebases
- shared contract ecosystem

Discuss together when designing or aligning.
Implement separately when executing.
Use `skill-0` as the canonical contract source, and mirror stable cross-repo rules into `skill-0-GUI`.
