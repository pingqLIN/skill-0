# Runtime v4 Closeout Baseline

Recorded at: `2026-07-17T10:01:10+08:00`
Risk level: `L2` (closeout evidence only; no production source changed)

## Repository

```yaml
repository_root: Q:/Projects/skill-0/.worktrees/runtime-v4-next
remote: https://github.com/pingqLIN/skill-0.git
source_branch: codex/skill0-runtime-v4-next
source_commit: 81fd2a9d22cb55a9fb6079eb9b338dfeed71f990
source_remote_commit: 81fd2a9d22cb55a9fb6079eb9b338dfeed71f990
source_ahead_behind: 0/0
working_branch: codex/skill0-v4-closeout
dirty_files_before_start: []
untracked_files_before_start: []
```

The separate primary checkout at `Q:/Projects/skill-0` was on `main` and had a pre-existing untracked `audit/` directory. This closeout uses the dedicated Runtime v4 worktree and does not read, modify, stage, or remove that directory.

## Handoff integrity

All nine files listed in `SHA256SUMS.txt` matched their expected SHA-256 digest before execution. The handoff identifies the same repository, source branch, closeout branch, release boundary, phase order, and change budget used here.

## Toolchain

| Tool | Observed version | Gate state |
|---|---|---|
| Python (system default) | 3.14.6 | Available; not used for release tests |
| Python (repo-local venv) | 3.12.10 | Available; release test interpreter |
| pip (repo-local venv) | 26.1.2 | Available |
| Node.js | 24.14.1 | Available; differs from CI 20.19.0 |
| npm | 11.11.0 | Available |
| Git | 2.55.0.windows.2 | Available |
| Docker | 29.6.1 | Available |
| Docker Compose | 5.2.0 | Available |
| PowerShell | 7.6.3 | Available |

## Local state

```yaml
existing_venv: Q:/Projects/skill-0/.venv (Python 3.12.10)
existing_worktree_node_modules: true
existing_primary_checkout_node_modules: true
repo_model_cache: Q:/Projects/skill-0/.hf-cache
user_huggingface_cache_present: true
network_available: true  # github.com:443 TCP check
```

The existing repo-local venv in the primary checkout is reused from this nested worktree. No global package or system binary installation is authorized or required for C0.

## Freeze and release boundary

- Runtime v4 remains dry-run only.
- Deployment remains single-host Docker Compose.
- Storage remains three independent SQLite stores: `skills.db`, `governance.db`, and `runtime.db`.
- No new feature, runtime dependency, service, database, framework, production adapter, schema feature, large refactor, or historical-document migration is in scope.
- Only a reproduced `CORE_BLOCKER` may justify production-source changes.

## C0 gate decision

`PASS`

- Correct remote and immutable source SHA proven.
- Source branch matches its remote exactly.
- Working branch created from the recorded source commit.
- Initial source-worktree dirty and untracked state recorded as empty.
- Pre-existing user-owned untracked content in the primary checkout preserved.
- Required system binaries are present.
- No production source changed.
