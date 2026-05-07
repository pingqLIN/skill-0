# Skill-0 Docs Agent Rules

These rules apply when working under `docs/`.

## Test Stage Guard

- Run verification from `/home/miles/dev2/projects/skill-0` unless a command explicitly requires a subdirectory.
- Treat untracked issue-log imports such as `docs/skill-0_issue-log.*` as input artifacts; do not mix them into unrelated commits.
- If a test or verification command is blocked by a missing program, runtime binary, or dev dependency, stop that verification line instead of installing or working around it.
- This applies to missing `git`, `docker`, `node`, `npm`, `tsx`, `vitest`, `tsc`, `pytest`, `uvicorn`, and MCP/container runtime binaries.
- When pausing, report the missing dependency, the blocked command, the recommended repair command, whether escalated approval is needed, and the next verification command after repair.
- Use existing repo-local `.venv` or `node_modules` normally. If project dependencies are missing, prefer repo-local restore such as `npm ci`; if a system-level program is missing, ask for confirmation first.
- If an MCP/container runtime is missing a binary, identify the runtime location before proposing the smallest PATH, mount, image rebuild, or container restart fix.
