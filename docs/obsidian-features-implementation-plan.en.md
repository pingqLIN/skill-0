# Obsidian-Inspired Features Implementation Plan

**Author**: pingqLIN  
**Date**: 2026-02-08  
**Version**: 1.0.0  
**Status**: In Progress

---

## 1. Motivation & Background

### 1.1 Origin

Based on the analysis in "Obsidian Database Architecture Research & Skill-0 Applicability Evaluation" (`docs/obsidian-architecture-evaluation.md`), several core Obsidian mechanisms have high reference value for the Skill-0 project. This plan targets items rated **4 stars (⭐⭐⭐⭐) or higher** for implementation.

### 1.2 Target Items

| Item | Rating | Obsidian Prototype | Skill-0 Target |
|------|--------|-------------------|---------------|
| **Bidirectional Links** | ⭐⭐⭐⭐⭐ | Bidirectional Links / Backlinks | Inter-skill relationship network |
| **Graph View** | ⭐⭐⭐⭐⭐ | Force-directed Graph Visualization | Skill graph API |
| **Metadata Cache** | ⭐⭐⭐⭐ | MetadataCache / resolvedLinks | Skill link cache mechanism |
| **MOC Pattern** | ⭐⭐⭐⭐ | Map of Content | Auto-generated skill category index |

### 1.3 Motivation Analysis

**Core Problem**: Skill-0 currently has 53 parsed skills with mature internal decomposition (Action/Rule/Directive ternary classification), but skills are **completely isolated** — lacking any cross-skill relationship modeling mechanism.

**Obsidian Insight**: Obsidian's "links over classification" design philosophy demonstrates that relationships between knowledge units are equally important as the units themselves.

**Expected Benefits**:
- Structured recording of inter-skill dependencies
- Link-based intelligent recommendation capabilities
- Full-landscape visualization of the skill ecosystem
- Improved efficiency in skill discovery and composition

---

## 2. Technology/Architecture/Capability Assessment

### 2.1 Technical Solution Evaluation

#### Bidirectional Links

| Dimension | Assessment |
|-----------|-----------|
| **Tech Source** | Obsidian MetadataCache.resolvedLinks concept |
| **Implementation** | SQLite relational table + reverse link VIEW |
| **Relevance** | Directly fills the inter-skill relationship gap |
| **Compliance** | Pure SQLite, no additional licensing issues |
| **Appropriateness** | Perfect fit — Skill-0 already uses SQLite, extension cost is minimal |

#### Graph Visualization (Graph View)

| Dimension | Assessment |
|-----------|-----------|
| **Tech Source** | Obsidian Graph View (force-directed graph) |
| **Implementation** | API endpoint providing JSON format nodes/edges data |
| **Relevance** | Enables skill relationship visualization for frontends |
| **Compliance** | Pure backend API, no frontend dependencies introduced |
| **Appropriateness** | High — API-first design, frontend can freely choose implementation |

#### Metadata Cache

| Dimension | Assessment |
|-----------|-----------|
| **Tech Source** | Obsidian MetadataCache in-memory cache pattern |
| **Implementation** | Python dict cache + TTL expiration mechanism |
| **Relevance** | Accelerates link queries, avoids repeated SQL queries |
| **Compliance** | Pure Python implementation, no external dependencies |
| **Appropriateness** | Medium — limited performance gain at current scale (53 skills), but prepares for future growth |

#### MOC Pattern

| Dimension | Assessment |
|-----------|-----------|
| **Tech Source** | Obsidian Map of Content community pattern |
| **Implementation** | Automated skill category index API + summary statistics |
| **Relevance** | Provides structured navigation for the skill ecosystem |
| **Compliance** | Uses existing semantic search + link analysis, no new dependencies |
| **Appropriateness** | High — highly complementary with existing category field and semantic search |

### 2.2 Technical Risk Assessment

| Risk Item | Level | Mitigation |
|-----------|-------|-----------|
| Schema changes break backward compatibility | Low | `skill_links` is an optional field |
| SQLite performance bottleneck | Low | 53 skills well below bottleneck; indexes established |
| Cache consistency issues | Medium | Implement cache invalidation mechanism |
| API interface changes affect frontend | Low | New endpoints only, no existing API modifications |

---

## 3. Current Project Evaluation Report

### 3.1 Project Status

| Dimension | Status | Details |
|-----------|--------|---------|
| **Parsed skills** | 53 | `data/parsed/` directory |
| **Schema version** | 2.2.0 | Ternary classification + Resource deps + Provenance |
| **Vector search** | ✅ Complete | SQLite-vec + all-MiniLM-L6-v2 (384-dim) |
| **REST API** | ✅ Complete | FastAPI with search/similar/cluster/stats |
| **Dashboard** | 🔧 In progress | React + Vite + TailwindCSS |
| **Testing** | ✅ Partial | pytest with helper and enhancement tests |
| **Inter-skill relationships** | ❌ Missing | This is exactly what this implementation addresses |

### 3.2 Affected Files

| File | Change Type | Description |
|------|------------|-------------|
| `schema/skill-decomposition.schema.json` | Extension | Add `skill_links` definition |
| `src/vector_db/vector_store.py` | Extension | Add skill_links table + management methods |
| `src/vector_db/search.py` | Extension | Add link query methods |
| `src/api/main.py` | Extension | Add API endpoints |
| `tests/test_skill_links.py` | New | Link functionality tests |

### 3.3 Unaffected Files

- `data/parsed/*.json` — Existing skill files need no modification (`skill_links` is optional)
- `src/vector_db/embedder.py` — Vector embedding logic unaffected
- `src/parsers/` — Parsers unaffected
- Existing API endpoints — Backward compatible

---

## 4. Requirements & Pros/Cons Report

### 4.1 Feature Requirements

#### Must Have
1. **skill_links Schema definition**: 7 link types (depends_on, extends, composes_with, alternative_to, related_to, derived_from, parent_of)
2. **SQLite skill_links table**: With indexes and uniqueness constraints
3. **Backlink query VIEW**: SQL VIEW for auto-generated reverse links
4. **CRUD API**: Create/Read/Delete skill links
5. **Graph data API**: Return JSON format nodes + edges

#### Should Have
6. **In-memory cache**: Link relationship caching with TTL expiration
7. **MOC index API**: Auto-generate skill category statistics and navigation
8. **Backlink endpoint**: Query all backlinks for a given skill

#### Nice to Have
9. **Link strength inference**: Auto-suggest links based on semantic similarity
10. **Orphan skill detection**: Identify skills with no links

### 4.2 Advantages

| Advantage | Description |
|-----------|-------------|
| **Fills critical gap** | Upgrades from isolated skill collection to interconnected skill network |
| **Low invasiveness** | All additions — no existing functionality modified |
| **Backward compatible** | `skill_links` is optional; existing data needs no changes |
| **Incremental adoption** | Schema → Database → API → Visualization, phased rollout |
| **Technical consistency** | Uses existing tech stack (SQLite + FastAPI + Python) |
| **Extensibility** | Lays data foundation for future Dashboard graph visualization |

### 4.3 Disadvantages

| Disadvantage | Mitigation Strategy |
|-------------|-------------------|
| **Increased Schema complexity** | `skill_links` is optional, doesn't affect minimal use cases |
| **Manual link maintenance cost** | Provide auto-suggestion features to reduce manual input |
| **Cache consistency risk** | Implement TTL + invalidation mechanism |
| **Increased test coverage needed** | Add dedicated test suite |

---

## 5. Deliverables & Acceptance Criteria

### 5.1 Deliverables

1. ✅ Schema extension (`skill_links` + `skill_link` definition)
2. ✅ SQLite table (`skill_links` table + indexes + view)
3. ✅ VectorStore extension (link CRUD methods)
4. ✅ SemanticSearch extension (link queries + graph + MOC)
5. ✅ FastAPI endpoints (link management + graph + MOC + backlinks)
6. ✅ In-memory cache (SkillLinkCache class)
7. ✅ Test suite (test_skill_links.py)
8. ✅ This document (implementation plan)

### 5.2 Acceptance Criteria

- [ ] All new API endpoints return correct results
- [ ] Backlink queries correctly reverse relationship types
- [ ] Cache hit/miss mechanism works correctly
- [ ] All tests pass
- [ ] Existing tests unaffected

---

**Document Version**: 1.0.0  
**Last Updated**: 2026-02-08  
**Author**: pingqLIN
