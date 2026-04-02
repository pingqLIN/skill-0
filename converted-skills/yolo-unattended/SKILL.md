---
name: yolo-unattended
description: Unattended execution protocol for the Skill-0 repository. Use when asked to keep developing this project autonomously with minimal interruptions until a user-specified local cutoff such as 06:00 or 07:00, while following the live execution plan, checkpoint-based delivery, validation commands, and dirty-worktree safety rules.
---
# Skill-0 YOLO Unattended Protocol

Use this skill only inside the Skill-0 repository when the user wants continuous project execution with minimal back-and-forth.

## Activation Signals

- "keep going until 06:00"
- "keep going until 07:00"
- "work unattended"
- "continue the repo on your own"
- "follow the project plan without stopping"
- "YOLO mode for this repo"

## Required Startup Pass

1. Read `AGENTS.md` and the current repo instructions before choosing work.
2. Read the live execution plan at `docs/planning/executable-dev-plan-2026-03-31.zh-TW.md`.
3. Check `git status --short` and treat the worktree as dirty unless proven otherwise.
4. Choose the smallest reviewable slice that moves the current checkpoint plan forward.

## Default Priority Order

1. Finish active convergence work before opening new feature surface.
2. Prefer repo plan items already marked as incomplete or partially landed.
3. Prefer fixes with direct evidence and clear validation commands.
4. Delay broad expansion work until current baseline risks are closed.

For this repository, that usually means:

- worktree-safe slices first
- governance/runtime hardening before new expansion
- validation and regression protection before polish

## Operating Loop

1. Pick one concrete slice with a clear acceptance check.
2. Gather only the local context needed to implement it safely.
3. Make the change end-to-end instead of stopping at analysis.
4. Run the narrowest relevant validation immediately after the change.
5. If the slice is complete and safe, move to the next highest-value slice.

Keep updates short and factual. Report checkpoints, blockers, and validation results, then continue working.

## Cutoff Handling

- Treat the user-provided cutoff, such as `06:00` or `07:00`, as local repository time unless the user gives a different timezone.
- If current local time is already past the requested cutoff, do not invent a new deadline; ask for a new cutoff or stop after the current safe checkpoint.
- Do not start a cross-cutting or high-blast-radius change in the last 20 minutes before cutoff.
- Use the final 20 minutes for validation, cleanup, and a precise handoff note.

## Safe Assumptions

- Make reversible assumptions when the ambiguity is low-risk and local.
- Ask one direct question only when the unknown would change architecture, external behavior, or destructive operations.
- Do not wait for user confirmation on small implementation details that can be validated locally.

## Repository Safety Rules

- Never revert user changes or unrelated dirty files.
- Never edit `parsed/*.json` by hand; generate or normalize via tooling.
- Never treat mutable skill rows as the governance source of truth.
- Never describe fidelity as strict equivalence without benchmark evidence.
- Never rely on dev-only CORS settings in production reasoning.
- Never use destructive git commands unless the user explicitly asks for them.

## Definition of Progress

Count work as progress only if it leaves one of these behind:

- merged code changes in the working tree
- validated generated artifacts
- updated repo documents that change execution clarity
- reproducible command output that closes a checkpoint

Notes without implementation do not count as progress unless the task is explicitly documentation-only.

## Validation Baseline

Run the narrowest relevant checks for the slice you changed. Use repo-local executables.

When updating a single skill, prefer targeted regeneration over full-corpus parsing:

```bash
.venv/bin/python scripts/auto_parse.py --force --skills <skill-name> --validate
```

For this skill itself:

```bash
.venv/bin/python scripts/auto_parse.py --force --skills yolo-unattended --validate
```

Core schema/data work:

```bash
.venv/bin/python tools/validate_skill_schema.py parsed
```

Python/API work:

```bash
.venv/bin/python -m pytest tests skill-0-dashboard/apps/api/tests -q
```

Frontend work:

```bash
cd skill-0-dashboard/apps/web && npm test && npm run build
```

When only one new parsed file is added, validate that file directly before running wider checks.

## Stop Conditions

Stop only at a clean checkpoint when one of the following is true:

- local time reached the cutoff
- the next step needs credentials, approvals, or external facts not available locally
- the remaining work would require touching unrelated dirty areas with high merge risk

Before stopping, leave a concise handoff that states:

1. what was finished
2. what was validated
3. what remains highest priority next
