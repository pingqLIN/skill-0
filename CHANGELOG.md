# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added (2026-02-07)
- **Vercel Labs Skills Comparison**: Comprehensive analysis comparing skill-0 with Vercel Labs Skills project
  - Full comparison document in Chinese ([vercel-skills-comparison.md](docs/vercel-skills-comparison.md))
  - English version ([vercel-skills-comparison.en.md](docs/vercel-skills-comparison.en.md))
  - Quick reference guide ([vercel-skills-comparison-quick.md](docs/vercel-skills-comparison-quick.md))
  - Architecture diagram with Mermaid visualization
  - Key findings: Projects are complementary (Skill-0 = depth, Vercel = breadth)
  - Proposed integration pathways: SKILL.md converter, Analysis API, Marketplace integration
  - Updated README files with comparison links

## [v2.5.0] - 2026-02-02 - Agent-Lightning Inspired Enhancements ⚡

- **New Feature**: Distributed skill processing architecture inspired by [Microsoft Agent-Lightning](https://github.com/microsoft/agent-lightning)
  - **Coordination Layer** (`src/coordination/`): Central SkillStore hub for task management
  - **Parser Abstraction** (`src/parsers/`): Unified SkillParser interface for extensibility  
  - **Worker Pool**: Parallel execution with SkillWorker for 4x speedup
- **Technical Comparison**: 17KB comprehensive analysis document comparing Agent-Lightning and Skill-0 architectures
- **Documentation**: Usage guide and working examples for distributed parsing
- **Test Suite**: 9 comprehensive tests validating all new components (100% passing)
- **Performance**: 4x faster parallel processing with 4 workers
- **Scalability**: Foundation for distributed, horizontal scaling

## [v2.4.0] - 2026-01-30 - GitHub Skills Discovery & Resource Dependencies

- **Schema Update**: v2.1.0 → v2.2.0
  - Added `resource_dependency` definition type with 8 resource categories
  - Resources can be defined at meta (global) and action levels
  - Support for database, API, filesystem, GPU, memory, credentials, network, environment
  - Includes specification details, fallback strategies, and required flags
- **GitHub Skills Search**: Discovered 75+ repositories aligning with skill-0 goals
  - Top 30 projects documented (MCP servers, Claude skills, AI frameworks)
  - MCP ecosystem: 4,509 repositories found
  - Top repository: awesome-mcp-servers (79,994 ⭐)
  - License analysis and compatibility verification
- **New Documentation**:
  - `docs/github-skills-search-report.md` - Comprehensive search report
  - `docs/github-skills-search-results.json` - Structured project data
  - `examples/database-query-analyzer-with-resources.json` - Resource example
  - `tools/github_skill_search.py` - GitHub search utility

## [v2.3.0] - 2026-01-28 - Testing & Quality Assurance

- **New Feature**: Comprehensive automated test suite
  - 32 tests covering all helper utilities
  - Tool equivalence verification (validator consistency)
  - Code equivalence verification (converter determinism)
  - Integration workflow testing
  - Error handling and edge case coverage
- Test fixtures and documentation in `tests/`
- pytest configuration in `pyproject.toml`
- CI/CD ready test infrastructure

## [v2.2.0] - 2026-01-28 - Documentation & Tooling

- **New Feature**: Comprehensive documentation suite
  - `CLAUDE.md` - Claude best practices guide
  - `SKILL.md` - Complete tool portal and workflow
  - `reference.md` - Full schema reference
  - `examples.md` - 7 detailed skill examples
  - `AGENTS.md` - AI agent guidelines
- **New Tool**: `scripts/helper.py` - Utility for validation, conversion, and testing
  - Template generation
  - Markdown to JSON conversion
  - Schema validation
  - Execution path testing
  - Complexity analysis
- Integration with agents.md format standard
- Test results documentation in `docs/helper-test-results.md`

## [v2.1.0] - 2026-01-26 - Stage 2

- **New Feature**: Semantic search with vector embeddings
  - `vector_db` module with SQLite-vec integration
  - `all-MiniLM-L6-v2` embedding model (384 dimensions)
  - K-Means clustering for skill grouping
  - CLI tool: `python -m vector_db.search`
- Expanded to 32 skills (+21 from awesome-claude-skills)
- Performance: 0.88s indexing, ~75ms search

## [v2.0.0] - 2026-01-26

- **Breaking Change**: Redefined ternary classification
  - `core_action` → `action` (ID: `ca_XXX` → `a_XXX`)
  - `mission` → `directive` (ID: `m_XXX` → `d_XXX`)
- Added `directive_type` support: completion, knowledge, principle, constraint, preference, strategy
- Added `decomposable` and `decomposition_hint` fields
- Added `action_type`: `await_input`
- Schema structure optimization
- Added 19 new skills from ComposioHQ/awesome-claude-skills

## [v1.1.0] - 2026-01-23

- Initial version
