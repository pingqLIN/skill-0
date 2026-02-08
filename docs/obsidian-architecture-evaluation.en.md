# Obsidian Database Architecture Research & Skill-0 Applicability Evaluation

**Author**: pingqLIN  
**Date**: 2026-02-08  
**Version**: 1.0.0

## Executive Summary

This document researches Obsidian's knowledge management database architecture, focusing on **Internal Links** and **Relationship Genealogy (Graph View)**, and evaluates concepts and mechanisms applicable to the Skill-0 project.

Key finding: Three core Obsidian mechanisms — **bidirectional links**, **Metadata Cache**, and **knowledge graph visualization** — have direct reference value for Skill-0's inter-skill relationship modeling and knowledge discovery, with phased adoption recommended.

---

## Table of Contents

1. [Obsidian Architecture Overview](#1-obsidian-architecture-overview)
2. [Internal Link Mechanisms](#2-internal-link-mechanisms)
3. [Relationship Genealogy & Graph View](#3-relationship-genealogy--graph-view)
4. [Properties & Metadata System](#4-properties--metadata-system)
5. [Map of Content (MOC) Pattern](#5-map-of-content-moc-pattern)
6. [Skill-0 Current State Analysis](#6-skill-0-current-state-analysis)
7. [Applicability Evaluation & Recommendations](#7-applicability-evaluation--recommendations)
8. [Concrete Adoption Plan](#8-concrete-adoption-plan)
9. [Conclusion](#9-conclusion)
10. [References](#10-references)

---

## 1. Obsidian Architecture Overview

### 1.1 Core Design Philosophy

Obsidian is a personal knowledge management system (PKM) based on **local Markdown files**, with core principles:

- **Local-First**: All notes are plain Markdown files stored in a local folder (called a Vault)
- **Linked Thought**: Links (rather than folders) serve as the primary knowledge organization method
- **Graph-Based Discovery**: Graphs reveal implicit relationships and patterns

### 1.2 Technical Architecture Layers

```
┌─────────────────────────────────────────────────────┐
│           Visualization Layer (Graph View)            │
│         Force-directed / Interactive Node-Edge Graph  │
├─────────────────────────────────────────────────────┤
│         Query & Index Layer (Dataview / Search)       │
│      Structured Queries / Dynamic Lists / SQL-like    │
├─────────────────────────────────────────────────────┤
│              Metadata Cache Layer                     │
│    MetadataCache class / resolvedLinks / CachedMetadata│
├─────────────────────────────────────────────────────┤
│           Link Resolution Layer                       │
│    Wikilink / Backlink / Block Reference / Alias      │
├─────────────────────────────────────────────────────┤
│           Storage Layer (Vault / Filesystem)          │
│        Plain Markdown files + YAML Frontmatter        │
└─────────────────────────────────────────────────────┘
```

---

## 2. Internal Link Mechanisms

### 2.1 Link Types

Obsidian supports multiple internal link syntaxes:

| Link Type | Syntax Example | Description |
|-----------|---------------|-------------|
| **Wikilink** | `[[Note Name]]` | Most common, auto-tracked |
| **Markdown Link** | `[Display Text](Note.md)` | Standard Markdown syntax |
| **Heading Link** | `[[Note#Heading]]` | Link to specific heading |
| **Block Link** | `[[Note#^block-id]]` | Link to specific paragraph block |
| **Alias Link** | `[[Note\|Display Name]]` | Custom display text |

### 2.2 Bidirectional Links

Obsidian's core innovation is **automatic bidirectional linking**:

- When Note A links to Note B, B automatically shows A's **Backlink**
- The system tracks both **Linked Mentions** and **Unlinked Mentions**
- This symmetry encourages networked knowledge structures over strict hierarchies

```
    Note A ────links to────→ Note B
       ←────backlink────
       
    (Bidirectional relationship created automatically)
```

### 2.3 Link Maintenance

- **Auto-update**: All internal links auto-update when notes are renamed or moved
- **Alias Resolution**: Aliases defined in YAML Frontmatter auto-resolve in link suggestions
- **Orphan Detection**: Notes with no links (Orphan Notes) are flagged in the graph

### 2.4 Skill-0 Implications

> **Key Insight**: Obsidian's bidirectional links demonstrate the "relationships as first-class citizens" design philosophy. Skill-0 currently only supports *intra-skill* element relationships (Action ↔ Rule ↔ Directive) but lacks *inter-skill* bidirectional link mechanisms.

---

## 3. Relationship Genealogy & Graph View

### 3.1 Graph View

Obsidian's Graph View transforms the knowledge base into an interactive force-directed graph:

- **Nodes**: Each Markdown file is a node; more links = larger node
- **Edges**: Internal links form edges between nodes, can be bidirectional
- **Clusters**: Highly interconnected notes naturally form clusters, revealing knowledge themes

### 3.2 Global vs Local Graph

| Feature | Global Graph | Local Graph |
|---------|-------------|-------------|
| **Scope** | All notes in Vault | Centered on current note |
| **Depth** | Complete network | Configurable link depth (1-hop, 2-hop...) |
| **Use** | Discover global patterns & clusters | Explore related context |
| **Filtering** | By folder/tag/search | Auto-focuses on related notes |

### 3.3 Relationship Genealogy Analogy

In the Zettelkasten methodology, note relationships resemble a family genealogy:

```
                    ┌──────────┐
                    │ Ancestor  │  (Original concept / source)
                    │   Note    │
                    └─────┬────┘
                          │
              ┌───────────┼───────────┐
              │           │           │
        ┌─────┴────┐ ┌───┴────┐ ┌────┴─────┐
        │ Child 1   │ │ Child 2 │ │ Child 3   │
        │  Note     │ │  Note   │ │   Note    │
        └─────┬────┘ └────────┘ └──────────┘
              │
        ┌─────┴────┐
        │Grandchild │  (More refined concept)
        │   Note    │
        └──────────┘
```

However, Obsidian's graph **breaks beyond strict tree structures**:
- A note can have multiple "parents" (multiple source influences)
- Relationships are **networked**, not tree-shaped
- Clusters form naturally through Backlinks and Tags

### 3.4 Metadata Cache Internal Structure

Obsidian uses the `MetadataCache` class for efficient indexing:

```typescript
// Obsidian internal data structure (conceptual)
interface MetadataCache {
  resolvedLinks: Record<string, Record<string, number>>   // Resolved links
  unresolvedLinks: Record<string, Record<string, number>> // Unresolved links
  getFileCache(file: TFile): CachedMetadata               // Get file cache

  // Event system
  on('changed', callback)    // File change notification
  on('resolved', callback)   // Link resolution complete
  on('deleted', callback)    // File deletion
}

interface CachedMetadata {
  links: LinkCache[]          // Outgoing links
  embeds: EmbedCache[]        // Embedded content
  tags: TagCache[]            // Tags
  headings: HeadingCache[]    // Headings
  frontmatter: FrontMatter    // YAML metadata
  sections: SectionCache[]    // Sections
  blocks: Record<string, BlockCache>  // Block references
}
```

**Performance characteristics**:
- In-memory cache to avoid repeated file reads
- Event-driven real-time updates
- Optimization strategies for large Vaults (10,000+ notes)

---

## 4. Properties & Metadata System

### 4.1 YAML Frontmatter as Database Fields

Obsidian treats YAML Frontmatter as structured metadata:

```yaml
---
title: Machine Learning Basics
created: 2026-02-08
tags: [AI, machine-learning, beginner]
status: published
related:
  - [[Deep Learning]]
  - [[Neural Networks]]
aliases:
  - ML Basics
---
```

### 4.2 Database Analogy

| Database Concept | Obsidian Equivalent |
|-----------------|-------------------|
| **Table** | Folder / Query result set |
| **Column / Field** | YAML Frontmatter Property |
| **Row / Record** | Individual Markdown note |
| **Data Types** | Text, Number, Date, List, Boolean, Link |
| **Query** | Search / Dataview / Bases plugin |
| **Index** | Metadata Cache |

### 4.3 Dataview Queries

The Dataview plugin treats the Vault as a queryable database:

```dataview
TABLE title, status, tags
FROM "Projects"
WHERE status = "active"
SORT created DESC
```

---

## 5. Map of Content (MOC) Pattern

### 5.1 MOC Concept

Map of Content is an organizational pattern developed by the Obsidian community, similar to a "knowledge index page":

- **Function**: Serves as a navigation hub for specific topics
- **Hybrid approach**: Manually curated important links + Dataview auto-generated lists
- **Flexible hierarchy**: Multi-level MOCs (Topic MOC → Subtopic MOC → Notes)

### 5.2 MOC & Skill-0 Analogy

```
Obsidian MOC                          Skill-0 Analogy
─────────────────────────────────────────────────────
Topic MOC                   →          Skill category
Subtopic MOC                →          Skill group / skill family
Wikilink [[Note]]           →          skill_id reference
Backlink (auto reverse link)→          Inter-skill bidirectional dependency
Dataview Query              →          Semantic Search API
Tag (#tag)                  →          Skill tags / action_type
Property (Frontmatter)      →          Schema meta fields
```

---

## 6. Skill-0 Current State Analysis

### 6.1 Current Relationship Model

Relationship types currently supported by Skill-0:

| Level | Relationship Type | Description | Corresponding Field |
|-------|------------------|-------------|-------------------|
| **Intra-skill** | Action → Rule | Dependencies in execution paths | `execution_paths.sequence` |
| **Intra-skill** | Directive → Action/Rule | Directive-related elements | `related_elements` |
| **Intra-skill** | Rule → Branch targets | Rule failure branching | `branching_targets` |
| **Inter-skill** | ❌ Does not exist | No inter-skill link mechanism | — |

### 6.2 Existing Infrastructure

```
✅ Available                        ❌ Missing
──────────────────────────────────────────────────
SQLite vector database             Inter-skill link table (skill_links)
Semantic search (similarity)       Bidirectional links (backlinks)
Skill metadata table (skills)      Graph visualization (graph view)
JSON Schema 2.2.0                  MOC index mechanism
Embeddings (384-dim)               Relationship type taxonomy (link_type)
```

### 6.3 GAP Analysis

| Obsidian Mechanism | Skill-0 Status | Gap |
|-------------------|---------------|-----|
| Bidirectional Links (Backlinks) | No inter-skill links | **High** |
| Graph View | No graph visualization | **High** |
| Metadata Cache | Has SQLite but no link cache | **Medium** |
| Properties (YAML) | Has JSON Schema metadata | **Low** |
| Dataview Queries | Has Semantic Search API | **Low** |
| MOC Navigation | No skill index pages | **Medium** |
| Alias Resolution | No alias system | **Low** |

---

## 7. Applicability Evaluation & Recommendations

### 7.1 High-Value Adoption Items

#### 🔗 Adoption 1: Inter-Skill Bidirectional Links

**Obsidian concept**: Automatic bidirectional links and backlinks between notes  
**Skill-0 application**: Establish explicit inter-skill relationships with bidirectional querying

**Value**:
- Discover dependency and composition relationships between skills
- Support "related skill recommendations"
- Build a networked skill ecosystem

**Proposed schema**:
```json
{
  "skill_links": [
    {
      "target_skill_id": "claude__pdf_extraction",
      "link_type": "depends_on",
      "description": "Requires PDF extraction as prerequisite step",
      "bidirectional": true
    },
    {
      "target_skill_id": "mcp__filesystem__read",
      "link_type": "uses",
      "description": "Uses filesystem read tool"
    }
  ]
}
```

#### 📊 Adoption 2: Skill Relationship Graph (Skill Graph View)

**Obsidian concept**: Force-directed graph visualizing all note relationships  
**Skill-0 application**: Add skill relationship graph view to the Dashboard

**Value**:
- Visualize the full skill ecosystem
- Discover skill clusters and orphan skills
- Aid skill composition decisions

#### 🗂️ Adoption 3: Skill Map of Content (Skill MOC)

**Obsidian concept**: Topic navigation hub combining manual curation with dynamic queries  
**Skill-0 application**: Auto-generate skill category index pages, integrating semantic search

### 7.2 Medium-Value Adoption Items

| Adoption Item | Description | Complexity |
|--------------|-------------|------------|
| **Link Type Taxonomy** | Borrow Obsidian's multiple link syntax concepts to define inter-skill relationship types | Low |
| **Metadata Cache** | Build an in-memory cache for skill relationships to accelerate graph queries | Medium |
| **Alias System** | Add aliases to skills for improved search hit rates | Low |

### 7.3 Low-Value / Not Applicable Items

| Item | Reason Not Applicable |
|------|----------------------|
| **Wikilink Syntax** | Skill-0 uses JSON Schema, not Markdown |
| **Vault Filesystem** | Skill-0 already has SQLite database; no need for pure file architecture |
| **Zettelkasten Atomic Notes** | Skill-0 already has ternary classification (Action/Rule/Directive) |

---

## 8. Concrete Adoption Plan

### 8.1 Phase 1: Inter-Skill Link Model (Schema Extension)

Add `skill_links` field to JSON Schema:

```json
{
  "skill_links": {
    "type": "array",
    "description": "Inter-skill link relationships (inspired by Obsidian bidirectional links)",
    "items": {
      "type": "object",
      "required": ["target_skill_id", "link_type"],
      "properties": {
        "target_skill_id": {
          "type": "string",
          "description": "Target skill identifier"
        },
        "link_type": {
          "type": "string",
          "enum": [
            "depends_on",
            "extends",
            "composes_with",
            "alternative_to",
            "related_to",
            "derived_from",
            "parent_of"
          ],
          "description": "Relationship type"
        },
        "description": {
          "type": "string",
          "description": "Relationship description"
        },
        "strength": {
          "type": "number",
          "minimum": 0,
          "maximum": 1,
          "description": "Relationship strength (0=weak association, 1=strong dependency)"
        },
        "bidirectional": {
          "type": "boolean",
          "default": false,
          "description": "Whether bidirectional (auto-creates reverse link)"
        }
      }
    }
  }
}
```

**Link type definitions**:

| link_type | Description | Analogy |
|-----------|-------------|---------|
| `depends_on` | Runtime dependency | Obsidian `[[prerequisite]]` |
| `extends` | Feature extension | Subclass relationship |
| `composes_with` | Composable | Collaborative relationship |
| `alternative_to` | Alternative solution | Same function, different implementation |
| `related_to` | Topically related | Obsidian Backlink |
| `derived_from` | Derived from | Source tracing |
| `parent_of` | Parent skill | Upper node in genealogy |

### 8.2 Phase 2: Bidirectional Link Index (Database Extension)

Add skill links table to SQLite:

```sql
-- Skill links table (inspired by Obsidian resolvedLinks)
CREATE TABLE IF NOT EXISTS skill_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_skill_id TEXT NOT NULL,
    target_skill_id TEXT NOT NULL,
    link_type TEXT NOT NULL,
    description TEXT,
    strength REAL DEFAULT 0.5,
    bidirectional BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_skill_id, target_skill_id, link_type)
);

-- Backlink index (inspired by Obsidian Backlinks)
CREATE INDEX idx_skill_links_target ON skill_links(target_skill_id);
CREATE INDEX idx_skill_links_source ON skill_links(source_skill_id);
CREATE INDEX idx_skill_links_type ON skill_links(link_type);

-- Backlink query view
CREATE VIEW IF NOT EXISTS skill_backlinks AS
SELECT 
    target_skill_id AS skill_id,
    source_skill_id AS linked_from,
    link_type,
    description,
    strength
FROM skill_links
UNION ALL
SELECT 
    source_skill_id AS skill_id,
    target_skill_id AS linked_from,
    CASE link_type
        WHEN 'depends_on' THEN 'depended_by'
        WHEN 'extends' THEN 'extended_by'
        WHEN 'parent_of' THEN 'child_of'
        ELSE link_type
    END AS link_type,
    description,
    strength
FROM skill_links
WHERE bidirectional = 1;
```

### 8.3 Phase 3: Relationship Graph Visualization (Dashboard Extension)

Add graph view to Skill-0 Dashboard:

```
┌──────────────────────────────────────────────────┐
│                Skill-0 Dashboard                  │
├──────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │Skill List │  │ Semantic  │  │  Graph   │  ← New│
│  │          │  │  Search   │  │  View    │       │
│  └──────────┘  └──────────┘  └──────────┘       │
│                                                  │
│     [PDF Extract]──depends_on──→[File Read]       │
│        │                          │              │
│        │ extends                  │ composes_with│
│        ↓                          ↓              │
│     [Table Analysis]          [Data Transform]   │
│        │                                         │
│        └────related_to────→[Excel Export]         │
│                                                  │
│  Node size = link count (from Obsidian Graph View)│
│  Cluster color = skill category                  │
└──────────────────────────────────────────────────┘
```

### 8.4 Implementation Priority & Time Estimates

| Phase | Work Item | Priority | Estimated Hours |
|-------|----------|----------|----------------|
| Phase 1 | Schema: add `skill_links` field | P0 | 2-4 hours |
| Phase 1 | Define 7 link types | P0 | 1 hour |
| Phase 2 | SQLite: add `skill_links` table | P1 | 4-6 hours |
| Phase 2 | Implement backlink query API | P1 | 4-6 hours |
| Phase 2 | Auto-create links during skill indexing | P1 | 6-8 hours |
| Phase 3 | Dashboard graph view (frontend) | P2 | 16-24 hours |
| Phase 3 | Graph data API endpoint | P2 | 4-6 hours |

---

## 9. Conclusion

### 9.1 Core Value Summary

| Obsidian Mechanism | Skill-0 Reference Value | Recommendation |
|-------------------|------------------------|----------------|
| **Bidirectional Links** | Build inter-skill relationship network | ⭐⭐⭐⭐⭐ |
| **Graph View** | Visualize skill ecosystem | ⭐⭐⭐⭐⭐ |
| **Metadata Cache** | Accelerate relationship queries | ⭐⭐⭐⭐ |
| **MOC Pattern** | Skill category indexing | ⭐⭐⭐⭐ |
| **Dataview Queries** | Structured search (already has semantic search) | ⭐⭐⭐ |
| **Properties** | Metadata extension (already has Schema) | ⭐⭐⭐ |
| **Alias System** | Alias-based search | ⭐⭐ |

### 9.2 Summary

Obsidian's design philosophy — **"links over classification"** — carries an important message for Skill-0. Currently, Skill-0's *intra-skill* structural decomposition is quite mature (Action/Rule/Directive ternary classification), but *inter-skill* relationship modeling has significant room for growth.

By borrowing Obsidian's bidirectional links and graph visualization mechanisms, Skill-0 can:

1. **Build a skill relationship network**: Upgrade from isolated skill collections to an interconnected skill ecosystem
2. **Support intelligent recommendations**: Recommend related or complementary skills based on link relationships
3. **Visualize the skill graph**: Provide an Obsidian Graph View-like experience in the Dashboard
4. **Enhance traceability**: Trace skill evolution through `derived_from` and `parent_of` relationships

**Ultimate vision**: Upgrade Skill-0 from a "skill decomposition tool" to a "skill knowledge graph platform", borrowing Obsidian's Linked Thought philosophy to achieve networked skill organization and intelligent discovery.

---

## 10. References

### Obsidian Official Documentation
- **Internal Links**: https://help.obsidian.md/links
- **Graph View**: https://help.obsidian.md/plugins/graph
- **Backlinks**: https://help.obsidian.md/Plugins/Backlinks
- **Properties**: https://help.obsidian.md/properties

### Technical Analysis
- **Internal Links and Graph View (DeepWiki)**: https://deepwiki.com/obsidianmd/obsidian-help/4.2-internal-links-and-graph-view
- **Graph View Architecture (DeepWiki)**: https://deepwiki.com/obsidianmd/obsidian-help/4.5-graph-view
- **Metadata and Linking (Plugin Docs)**: https://deepwiki.com/obsidianmd/obsidian-plugin-docs/3.5-metadata-and-linking
- **Properties and Metadata (DeepWiki)**: https://deepwiki.com/obsidianmd/obsidian-help/4.3-properties-and-metadata
- **Graph View Source (GitHub)**: https://github.com/obsidianmd/obsidian-help/blob/master/en/Plugins/Graph%20view.md

### Community Resources
- **Obsidian Zettelkasten Starter Kit**: https://github.com/groepl/Obsidian-Zettelkasten-Starter-Kit
- **Obsidian MOC Guide**: https://github.com/seqis/ObsidianMOC
- **Dataview Plugin**: https://blacksmithgu.github.io/obsidian-dataview/
- **Backlink Cache Plugin**: https://github.com/mnaoumov/obsidian-backlink-cache

### Skill-0 Related
- **Skill-0 Repository**: https://github.com/pingqLIN/skill-0
- **Schema**: `schema/skill-decomposition.schema.json` v2.2.0
- **Vector Store**: `src/vector_db/vector_store.py`
- **Semantic Search**: `src/vector_db/search.py`

---

**Document Version**: 1.0.0  
**Last Updated**: 2026-02-08  
**Author**: pingqLIN  
