# MiniMe Agent

## Overview

**MiniMe Agent** is a global GitHub file system operations agent that can be summoned in any GitHub repository to perform file operations.

### Key Features

- ✅ **Global Availability**: Not limited to specific projects, usable in any GitHub repository
- ✅ **Full Permissions**: Create repositories, delete files, review tasks
- ✅ **Explicit Activation**: Must be activated via message or email command
- ✅ **Auto-Shutdown**: Automatically releases resources after task completion
- ✅ **Content Protection**: Does not review/modify file contents (unless procedural issues exist)
- ✅ **Cross-Repository**: Can access and operate on any repository with proper permissions
- ✅ **Safety First**: Multiple validation rules and security checks

## Skill Classification

Based on skill-0 ternary classification system:

- **20 Actions**: File operations, GitHub API calls, activation/shutdown
- **12 Rules**: Validation, permission checks, safety verification
- **14 Directives**: Principles, constraints, completion states

## Usage Scenarios

### 1. Clean Up Old Files
Remove outdated test files across multiple repositories.

### 2. Batch Create Repositories
Create multiple related repositories for a new project.

### 3. Procedural Fixes
Fix format issues causing CI failures.

### 4. Cross-Repository Refactoring
Standardize file structures across multiple repositories.

## Execution Paths

1. **Standard Activation**: Verify signal → Check authorization → Review task
2. **Create Repository**: Validate name → Check space → Create repository
3. **Safe Delete**: Check existence → Safety validation → Path validation → Delete
4. **Cross-Repo Access**: Verify token → Check permissions → Validate repository → Access
5. **Webhook-Triggered**: Receive webhook → Verify → Access → Delete → Commit/push

## Security

All operations are protected by:
- Activation verification (r_001)
- Path safety validation (r_008)
- Permission checks (r_003, r_011)
- Delete safety verification (r_004)

## Requirements

- **GitHub API**: Valid Personal Access Token
- **Permissions**: Configured based on operation needs (repo, delete_repo, admin:org)
- **Network**: Internet connection for GitHub API access
- **Storage**: Disk space for clone/operations

## Limitations

1. **Content Non-Interference**: Only modifies content if procedural issues block execution
2. **Explicit Activation**: Does not auto-start or respond to unauthorized requests
3. **Permission Boundary**: Can only operate on repositories with proper permissions
4. **One-Time Execution**: Shuts down immediately after task completion

## Technical Specifications

- **Schema Version**: 2.2.0
- **Skill ID**: `github__global__minime_agent`
- **Skill Layer**: `claude_skill`
- **Total Actions**: 20
- **Total Rules**: 12
- **Total Directives**: 14
- **Execution Paths**: 10

## Documentation

- [Usage Guide (Traditional Chinese)](minime-agent-usage.md) - Detailed usage guide
- [Skill Definition](../data/parsed/minime-agent-skill.json) - Complete JSON definition
- [Schema](../schema/skill-decomposition.schema.json) - skill-0 schema v2.2.0

## License

MIT

---

**Note**: MiniMe Agent is a conceptual skill definition designed on the skill-0 framework, demonstrating how to use the ternary classification system (Actions/Rules/Directives) to decompose complex autonomous agent behavior.
