# Skill-0 vs Taste-Skill

A comparison of two AI skill definition projects: **Skill-0** (structured skill decomposition and semantic search) and **Taste-Skill** (high-agency frontend design instructions). This document evaluates similarities, differences, adoptable advantages, and potential market cooperation.

## Positioning

- **Skill-0**: A ternary classification system that parses AI skill/tool instructions into structured JSON (Actions, Rules, Directives), stores them in SQLite with vector embeddings, and provides semantic search, clustering, governance, and a dashboard API.
- **Taste-Skill**: A single-file (`SKILL.md`) prompt engineering system that instructs AI coding assistants (Cursor, Claude Code, Codex, etc.) to generate high-end, modern frontend UI code by enforcing design rules, anti-patterns, and configurable style dials.

## Workflow Comparison

| Dimension | Skill-0 | Taste-Skill |
|-----------|---------|-------------|
| **Input** | Skill/tool definitions (Markdown/JSON) | A single `SKILL.md` file placed in the project root |
| **Core Flow** | Parse → Classify → Index → Search | AI reads rules → Generates constrained frontend code |
| **Output** | Structured JSON, semantic search results, clusters | High-quality frontend code (React/Next.js + Tailwind) |
| **Primary Goal** | Knowledge extraction, discovery, and governance of skill definitions | Eliminate generic AI-generated UI ("slop") and enforce premium design taste |
| **User Interaction** | CLI, REST API, dashboard | Direct prompt to AI assistant with `@SKILL.md` reference |

## Similarities

1. **Both Are "Skill" Systems**: Both projects define structured instructions that shape AI behavior — Skill-0 for analysis/indexing, Taste-Skill for code generation quality.
2. **Rule-Based Architecture**: Both rely on explicit rules. Skill-0 uses a formal `Rules` classification (condition_type, output). Taste-Skill uses numbered design rules (typography, color, layout, interactivity).
3. **Anti-Pattern Awareness**: Both define what AI should NOT do. Skill-0 documents side effects and failure consequences. Taste-Skill has Section 7 ("100 AI Tells") listing forbidden patterns.
4. **Markdown-First**: Both use Markdown as the primary authoring format for skill definitions.
5. **Target AI Coding Assistants**: Both aim to improve how AI tools work — Skill-0 by structuring knowledge, Taste-Skill by constraining output quality.

## Differences

| Aspect | Skill-0 | Taste-Skill |
|--------|---------|-------------|
| **Scope** | General-purpose skill decomposition (any domain) | Frontend UI/UX only (React/Next.js ecosystem) |
| **Complexity** | Full-stack system: parser, vector DB, API, dashboard, schema | Single file, zero infrastructure |
| **Schema** | Formal JSON Schema v2.2.0 with versioning | No formal schema; structured Markdown with numbered sections |
| **Searchability** | Semantic search with vector embeddings (384-dim) | Not searchable; consumed directly by AI at prompt time |
| **Configurability** | Schema extensions, custom skill layers | 3 numeric dials (DESIGN_VARIANCE, MOTION_INTENSITY, VISUAL_DENSITY) |
| **Governance** | Review workflows, audit logs, security scanning | Community feedback via GitHub issues/PRs |
| **Technology Stack** | Python, FastAPI, SQLite-vec, sentence-transformers | None (pure Markdown instructions) |
| **Decomposition** | Ternary: Actions / Rules / Directives | Flat sections: Architecture, Rules, Anti-Slop, Performance, Reference |
| **Audience** | Platform builders, AI researchers, skill curators | Frontend developers using AI coding assistants |
| **Skill Count** | 32+ parsed skills, 171 imported | 1 monolithic skill file |

## Adoptable Advantages from Taste-Skill

### 1. Parameterized Control Dials
Taste-Skill's 3 configurable dials (`DESIGN_VARIANCE`, `MOTION_INTENSITY`, `VISUAL_DENSITY`) with 1–10 scales provide an elegant UX for adjusting behavior. Skill-0 could adopt a similar concept:
- Add optional `parameters` or `control_dials` to the schema, allowing skill authors to define tunable numeric ranges that modify execution behavior.
- This would make skills more flexible and user-friendly without altering the core ternary classification.

### 2. Explicit Anti-Pattern Catalogs
Taste-Skill's "100 AI Tells" (Section 7) is a comprehensive catalog of forbidden patterns with concrete alternatives. Skill-0's Rules support `failure_consequence` but lack a dedicated negative-pattern catalog. Adding an `anti_patterns` field to skill definitions would strengthen quality constraints.

### 3. Zero-Setup Distribution Model
Taste-Skill's "download one file and reference it" approach is remarkably accessible. Skill-0 could offer a lightweight export mode — a standalone `SKILL.md` file generated from parsed JSON — enabling users to consume skills without running the full infrastructure.

### 4. Performance Guardrails as First-Class Rules
Taste-Skill dedicates Section 5 to performance guardrails (DOM cost, hardware acceleration, z-index restraint). Skill-0 could formalize performance constraints as a rule sub-type, making them searchable and enforceable across skill definitions.

### 5. Creative Inspiration Arsenal
Taste-Skill's Section 8 ("Creative Arsenal") provides a categorized library of UI patterns (navigation, layout, cards, scroll, typography, micro-interactions). This "pattern library" concept could be adapted as a new directive type or a linked resource in Skill-0, providing curated implementation references alongside skill definitions.

## Market Role Analysis

### Skill-0: Infrastructure Layer
- **Role**: Backend knowledge infrastructure for AI skill management
- **Value**: Structure, searchability, governance, and lifecycle management of skill definitions
- **Market**: Enterprise AI platforms, tool registries, skill marketplaces, AI governance teams

### Taste-Skill: Creative Constraint Layer
- **Role**: Frontend quality enforcement for AI-generated code
- **Value**: Immediately elevates AI output quality with zero infrastructure overhead
- **Market**: Individual developers, design-conscious teams, rapid prototyping ("vibe coding")

### Competition

Direct competition is **minimal** because they operate at different layers:
- Skill-0 is a **meta-system** (manages and indexes skills); Taste-Skill is a **specific skill** (instructs AI behavior for one domain).
- Taste-Skill could actually be parsed and indexed BY Skill-0 as one of many skills in its database.

### Cooperation Opportunities

1. **Taste-Skill as a Skill-0 Entry**: Parse `taste-skill/SKILL.md` into Skill-0's ternary format. This would create a structured, searchable representation of the frontend design skill, demonstrating Skill-0's parsing capabilities on a real-world, popular skill definition.

2. **Skill-0 as Distribution Platform**: Skill-0's semantic search and API could serve as a discovery layer for skills like Taste-Skill, allowing developers to find and download domain-specific instruction files.

3. **Parameterized Skill Export**: Combine Skill-0's structured schema with Taste-Skill's dial concept to generate configurable `SKILL.md` files that AI assistants can consume directly — bridging the gap between structured governance and zero-setup usage.

4. **Quality Metrics Pipeline**: Skill-0's analysis tools could evaluate and score skill files like Taste-Skill based on structural completeness, rule coverage, and anti-pattern documentation — providing quality metrics for a potential skill marketplace.

## Summary Matrix

| Dimension | Skill-0 | Taste-Skill | Synergy Potential |
|-----------|---------|-------------|-------------------|
| Architecture | Full-stack platform | Single file | Skill-0 indexes Taste-Skill |
| Flexibility | Any domain | Frontend only | Complement, not compete |
| UX | CLI/API/Dashboard | Copy file + prompt | Export structured skills to SKILL.md |
| Governance | Built-in workflows | Community-driven | Skill-0 provides governance for skill ecosystem |
| Adoption Barrier | Requires setup | Zero setup | Skill-0 offers lightweight export mode |
| Configurability | Schema extensions | 3 dials (1-10) | Add dial concept to Skill-0 schema |

> [!WARNING]
> This comparison is based on Skill-0 repository (commit 9d9de81) and Taste-Skill repository (https://github.com/Leonxlnx/taste-skill) as of 2026-02. Project features and positioning may change over time.

## Sources

- Skill-0 repository: https://github.com/pingqLIN/skill-0
- Taste-Skill repository: https://github.com/Leonxlnx/taste-skill
- Taste-Skill SKILL.md: https://github.com/Leonxlnx/taste-skill/blob/main/SKILL.md
