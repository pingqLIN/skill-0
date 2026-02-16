# Skill-0 vs Claude Code Simplifier

A concise comparison focused on positioning, workflow, data model, and how the two can be used together.

## Positioning

- **Skill-0**: A parser and semantic index for skill/tool instructions. It turns skill definitions into structured JSON for analysis and search.
- **Claude Code Simplifier**: A code-focused helper that analyzes project code (and recent changes) to propose simplified edits.

## Workflow Comparison

| Dimension | Skill-0 | Claude Code Simplifier |
|-----------|---------|------------------------|
| **Input** | Skill descriptions, tool instructions | Project code and recent changes |
| **Core Flow** | Parse -> classify -> index -> search | Analyze -> simplify -> output edits |
| **Output** | Structured JSON, semantic search results | Simplified code changes |
| **Primary Goal** | Knowledge extraction and discovery | Readability and simplification of code |

## Data Model

- **Skill-0**: JSON schema with Actions, Rules, and Directives (plus optional provenance).
- **Claude Code Simplifier**: Code diffs or suggested edits (no shared schema implied).

## Pros and Cons

**Skill-0**
- Pros: Explicit, structured data model; repeatable indexing; good for governance and retrieval.
- Cons: Requires skill definitions as input; not a code-editing assistant by itself.

**Claude Code Simplifier**
- Pros: Directly improves code readability and complexity in a project context.
- Cons: Focused on code changes; not designed for skill or instruction indexing.

## Complementarity and Integration Guidance

- Use **Skill-0** to curate and search instruction sets (skills, tool prompts, policies).
- Use **Claude Code Simplifier** to apply code simplifications in the target repo.
- Combined workflow: capture best-practice instructions in Skill-0, then apply them as simplification goals when running the Code Simplifier plugin.

> [!WARNING]
> This comparison is based on the public plugin listing and Skill-0 repository materials. Plugin behavior may change over time.

## Sources

- Claude plugin directory: https://claude.com/plugins
- Claude Code Simplifier plugin page: https://claude.com/plugins/code-simplifier
