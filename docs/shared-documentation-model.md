# Shared Documentation Model For `skill-0` And `skill-0-GUI`

Updated: `2026-04-21`
Implementation status: `🟢 Source-of-truth model, ownership boundaries, and cross-repo mirror validation are enforced from skill-0 CI`

Status note: This file defines the canonical shared-doc ownership model in `skill-0`. The source set under `docs/shared/` is live, repo-local ownership/provenance wording is now checked in CI, mirrored copies in `skill-0-GUI/docs/shared/` are checked from `skill-0` CI, and the remaining hardening question is whether `skill-0-GUI` should also enforce the same contract independently in its own workflow.

## Purpose

This note explains how the `skill-0` repository should share stable documentation with `skill-0-GUI` without turning the two repositories into a tightly coupled mono-repo.

## Decision

The shared-documentation model is:

1. `skill-0` owns the source documents
2. shared source files live in `docs/shared/`
3. `skill-0-GUI` mirrors selected files into its own `docs/shared/`
4. repository-specific notes remain in their own repositories

This is intentionally a **source-of-truth plus mirrored copies** model.

It is not:

- a symlink-based model
- a submodule-based model
- a "copy files manually and hope they stay aligned" model

## Why this model

This approach is the best fit for the current project shape:

- the repositories are separate GitHub repos
- the GUI can run in standalone mode and should remain independently deployable
- Windows/WSL and GitHub hosting make symlink-heavy workflows fragile
- most cross-repository documents are contract documents, not runtime code

The goal is to share stable meaning, not to force both repositories into identical structure.

## What belongs in shared docs

Only place stable cross-repository contracts in `docs/shared/`.

Good candidates:

- parser contract
- schema contract
- canonical vs standalone mode semantics
- shared terminology
- evidence/risk wording used by both review surfaces

Bad candidates:

- project progress reports
- roadmap snapshots
- deployment procedures tied to one runtime
- dashboard-only operations
- GUI-only workbench walkthroughs

## Current shared source files

The initial shared source set is:

1. `docs/shared/README.md`
2. `docs/shared/01-parser-contract.md`
3. `docs/shared/02-mode-and-equivalence-contract.md` (mode + fidelity / strict equivalence contract)
4. `docs/shared/03-shared-terminology.md`
5. `docs/shared/04-cross-repo-session-rules.md`

These documents are meant to be stable, high-signal, and safe to mirror.

## How `skill-0-GUI` consumes them

`skill-0-GUI` contains:

- `shared-docs.manifest.json`
- `scripts/sync-shared-docs.mjs`
- mirrored output under `docs/shared/`

The GUI repo can refresh its mirrored copies with:

```bash
npm run docs:sync
```

It can verify that mirrored copies are current with:

```bash
npm run docs:check
```

The sync script resolves `SKILL0_ROOT` first, then common local repository paths.

## Update workflow

When a shared contract changes, use this order:

1. update the source file in `skill-0/docs/shared/`
2. review whether the change affects canonical/fallback wording or downstream assumptions
3. run `npm run docs:sync` in `skill-0-GUI`
4. review the mirrored output in `skill-0-GUI/docs/shared/`
5. commit the source change and the mirrored change in their respective repos

## Authoring rule

If a document starts drifting into:

- current implementation status
- local deployment instructions
- repo-specific file maps
- unfinished roadmap detail

then it should probably leave `docs/shared/` and become repository-specific documentation instead.

## Future hardening

Further hardening can still add:

1. a `skill-0-GUI`-side CI self-check so mirrored-doc enforcement does not depend only on `skill-0`
2. fixture-based strict-equivalence notes for canonical vs standalone mode language
3. a shared version marker or manifest checksum for easier auditability

## Summary

`skill-0` remains the source of truth for stable parser and contract documentation.
`skill-0-GUI` stays independently shippable, but mirrors the shared contract documents so external reviewers and operators can read one local copy without guessing whether terminology has drifted.
