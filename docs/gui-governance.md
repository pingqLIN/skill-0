# Skill-0 GUI Governance Decision

Updated: `2026-05-04`
Status: `Implemented`

## Decision

`skill-0-GUI` remains a separate companion repository.

`skill-0` owns the canonical parser, schema, governance model, shared contracts, and cross-repository policy. `skill-0-GUI` owns the reviewer workbench, bridge runtime, standalone-compatible UI, and frontend verification.

This is a governance consolidation, not a Git tree merge.

## Repository Boundary

The active boundary is:

| Area | Owner |
|------|-------|
| Parser behavior | `skill-0` |
| Schema and parsed output contract | `skill-0` |
| Governance revision model | `skill-0` |
| Shared cross-repo docs | `skill-0/docs/shared/` |
| Dashboard API and dashboard web app | `skill-0/skill-0-dashboard/` |
| Review studio UI | `skill-0-GUI` |
| Bridge runtime and standalone fallback | `skill-0-GUI` |
| GUI mirrored contract docs | `skill-0-GUI/docs/shared/` |

The GUI should consume contracts from `skill-0`; it should not become a second parser authority.

## Why Not Import The GUI Now

Do not move `skill-0-GUI` under `skill-0` unless a later migration decision explicitly changes this boundary.

Current reasons:

- `skill-0` already contains its own dashboard monorepo under `skill-0-dashboard/`.
- `skill-0-GUI` has an independent React/Vite/Express runtime, CI surface, and release rhythm.
- Shared-doc mirroring already gives both repositories a machine-checkable contract boundary.
- Keeping the GUI independently shippable protects standalone demo and deployment paths.
- A direct copy would make `skill-0` carry two frontend applications with different product purposes.

## Accepted Integration Model

Use this model:

1. Update canonical contracts in `skill-0`.
2. Mirror stable shared docs into `skill-0-GUI`.
3. Implement parser/governance changes in `skill-0`.
4. Implement bridge/workbench changes in `skill-0-GUI`.
5. Verify both repositories before claiming cross-repo completion.

This keeps product work aligned without forcing every UI change through the core parser repository.

## Required Checks

From `skill-0`:

```bash
.venv/bin/python tools/check_shared_docs.py
.venv/bin/python tools/check_shared_docs_mirror.py --gui-root /home/miles/dev2/projects/skill-0-GUI --require-gui-root
```

From `skill-0-GUI`:

```bash
npm run docs:sync
npm run docs:check
npm test
npm run verify:build-size
npm run verify:public-build
```

Run the GUI commands in the WSL-native checkout when possible. The Windows-mounted checkout can be used for editor workflows, but WSL-native execution is the more reliable test path.

## Migration Rule

If the repositories are ever consolidated, use a history-preserving import such as `git subtree` into a clearly named path like `apps/review-studio/`.

Do not do an ad hoc file copy, do not replace the existing dashboard app, and do not drop `skill-0-GUI` history unless that history has been reviewed and intentionally discarded.

## Summary

`skill-0` is the source of truth for contracts and governance.
`skill-0-GUI` is a governed companion repo for reviewer and visualization workflows.
The correct current state is coordinated ownership, not a monorepo merge.
