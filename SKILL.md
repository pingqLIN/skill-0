# Skill-0 Tool Portal

> 🔧 Complete guide to skill decomposition workflow and toolchain

## Quick Start

### Installation
```bash
git clone https://github.com/pingqLIN/skill-0.git
cd skill-0
pip install -r requirements.txt
```

### First Run
```bash
# Index existing skills
python -m vector_db.search --db skills.db --parsed-dir parsed index

# Search for skills
python -m vector_db.search search "document processing"

# Analyze patterns
python tools/analyzer.py -p parsed -o analysis/report.json
```

## Tool Suite Overview

```
skill-0/tools/
├── analyzer.py           # 📊 Statistical analysis
├── pattern_extractor.py  # 🔍 Pattern discovery
├── evaluate.py           # ✅ Coverage evaluation
└── batch_parse.py        # 🔄 Batch processing

skill-0/vector_db/
├── embedder.py           # 🧠 Embedding generation
├── vector_store.py       # 💾 SQLite-vec storage
└── search.py             # 🔎 Semantic search CLI
```

## 1. Analyzer Tool

### Purpose
Generate comprehensive statistics about parsed skills

### Usage
```bash
# Basic analysis
python tools/analyzer.py

# Custom paths
python tools/analyzer.py -p parsed -o analysis/report.json

# With text report
python tools/analyzer.py -t
```

### Output Structure
```json
{
  "summary": {
    "total_skills": 32,
    "total_actions": 266,
    "total_rules": 84,
    "total_directives": 120
  },
  "action_types": {
    "io_read": 124,
    "io_write": 90,
    "transform": 28,
    ...
  },
  "directive_types": {
    "completion": 45,
    "knowledge": 30,
    "principle": 20,
    ...
  },
  "skills": [ /* per-skill breakdown */ ]
}
```

### Use Cases
- Project health monitoring
- Coverage verification
- Pattern identification
- Before/after comparisons

## 2. Pattern Extractor

### Purpose
Discover common patterns across skills for reuse and standardization

### Usage
```bash
# Extract patterns
python tools/pattern_extractor.py

# Custom output
python tools/pattern_extractor.py -o analysis/patterns.json
```

### Pattern Types

#### Action Combinations
Frequently occurring action sequences
```json
{
  "pattern_type": "action_combination",
  "actions": ["io_read", "transform", "io_write"],
  "frequency": 15,
  "example_skills": ["docx-skill", "pdf-skill", "xlsx-skill"]
}
```

#### Directive Usage
Common directive patterns
```json
{
  "pattern_type": "directive_usage",
  "directive_types": ["completion", "constraint"],
  "usage_context": "Document processing",
  "frequency": 8
}
```

#### Structure Patterns
Element ratio patterns
```json
{
  "pattern_type": "structure",
  "ratio": "3:1:2",
  "elements": "actions:rules:directives",
  "category": "Data processing"
}
```

### Use Cases
- Template creation
- Best practice identification
- Duplicate detection
- Framework evolution

## 3. Evaluation Tool

### Purpose
Assess framework coverage and identify gaps

### Usage
```bash
# Evaluate coverage
python tools/evaluate.py -p parsed

# Detailed report
python tools/evaluate.py -p parsed -o analysis/evaluation.json
```

### Metrics
- **Action Type Coverage**: % of action types used
- **Directive Type Coverage**: % of directive types used
- **Completeness Score**: Overall decomposition quality
- **Pattern Diversity**: Variety in skill structures

### Output
```json
{
  "coverage": {
    "action_types": {
      "total": 8,
      "used": 8,
      "percentage": 100
    },
    "directive_types": {
      "total": 6,
      "used": 6,
      "percentage": 100
    }
  },
  "gaps": [],
  "recommendations": [
    "Add more constraint-type directives",
    "Increase rule diversity in condition types"
  ]
}
```

## 4. Batch Parser

### Purpose
Parse multiple skills efficiently with consistent formatting

### Usage
```bash
# Parse directory
python tools/batch_parse.py -i input_skills/ -o parsed/

# With validation
python tools/batch_parse.py -i input_skills/ -o parsed/ --validate

# Dry run
python tools/batch_parse.py -i input_skills/ --dry-run
```

### Input Format
Accepts various formats:
- Markdown skill definitions
- JSON pre-formatted
- Plain text descriptions (requires LLM)

### Features
- Schema validation
- ID auto-increment
- Duplicate detection
- Parallel processing

## 5. Vector Search System

### Purpose
Semantic search and clustering for skill discovery

### Setup
```bash
# One-time indexing
python -m vector_db.search --db skills.db --parsed-dir parsed index
```

### Commands

#### Search by Query
```bash
python -m vector_db.search search "creative design tools"
```
Output:
```
🔍 Searching for: creative design tools
--------------------------------------------------
1. Canvas-Design Skill (53.36%)
2. Theme Factory (46.14%)
3. Pptx Skill (45.08%)
```

#### Find Similar Skills
```bash
python -m vector_db.search similar "Docx Skill"
```
Output:
```
🔍 Finding skills similar to: Docx Skill
--------------------------------------------------
1. Xlsx Skill (87.23%)
2. Pdf Skill (82.14%)
3. Txt File Skill (76.89%)
```

#### Cluster Analysis
```bash
python -m vector_db.search cluster -n 5
```
Output:
```
📊 Clustering 32 skills into 5 groups...
--------------------------------------------------
Cluster 1: Development Tools (10 skills)
  - MCP Server, Testing Framework, ...
  
Cluster 2: Document Processing (5 skills)
  - PDF Skill, DOCX Skill, ...
```

#### Statistics
```bash
python -m vector_db.search stats
```
Output:
```
📊 Skill Database Statistics
--------------------------------------------------
Total Skills: 32
Indexed Skills: 32
Embedding Dimension: 384
Database Size: 1.73 MB
Last Updated: 2026-01-28
```

### Python API
```python
from vector_db import SemanticSearch

# Initialize
search = SemanticSearch(db_path='skills.db')

# Search
results = search.search("PDF processing", limit=5)
for r in results:
    print(f"{r['name']}: {r['similarity']:.2%}")

# Find similar
similar = search.find_similar("Docx Skill", limit=5)

# Cluster
clusters = search.cluster_skills(n_clusters=5)
```

## Workflow Examples

### Adding a New Skill

#### Step 1: Create JSON
```bash
cp parsed/template.json parsed/my-skill.json
# Edit my-skill.json with your decomposition
```

#### Step 2: Validate
```bash
python tools/analyzer.py -p parsed/my-skill.json
```

#### Step 3: Index
```bash
python -m vector_db.search index
```

#### Step 4: Verify
```bash
python -m vector_db.search search "my skill description"
```

### Analyzing a Skill Category

#### Step 1: Filter Skills
```bash
python -m vector_db.search search "document processing" > doc_skills.txt
```

#### Step 2: Extract Patterns
```bash
python tools/pattern_extractor.py -p parsed/ -o patterns_doc.json
```

#### Step 3: Compare
```bash
python tools/analyzer.py -p parsed/ -t > comparison.txt
```

### Batch Migration

#### Step 1: Prepare Source
```bash
# Organize skills in input/
ls input/
# skill1.md  skill2.md  skill3.json
```

#### Step 2: Batch Parse
```bash
python tools/batch_parse.py -i input/ -o parsed/ --validate
```

#### Step 3: Re-index
```bash
python -m vector_db.search index
```

#### Step 4: Evaluate
```bash
python tools/evaluate.py -p parsed
```

## Performance Tips

### Large Datasets
- Use `--batch-size` for batch operations
- Enable parallel processing with `-j` flag
- Pre-filter with `--filter` patterns

### Memory Optimization
- Index incrementally for >100 skills
- Use `--checkpoint` for long operations
- Clear cache between major operations

### Search Optimization
- Cache frequent queries
- Use clustering for categorization
- Limit results with `--limit`

## Common Patterns

### Document Processing Skills
```
Pattern: io_read → transform → io_write
Elements: 3-5 actions, 1-2 rules, 2-3 directives
Directives: completion, constraint
```

### API Integration Skills
```
Pattern: external_call → state_check → transform
Elements: 2-4 actions, 2-3 rules, 1-2 directives
Directives: strategy, knowledge
```

### Creative Tools
```
Pattern: await_input → llm_inference → io_write
Elements: 4-6 actions, 1 rule, 3-4 directives
Directives: preference, principle
```

## Troubleshooting

### Issue: Schema Validation Fails
```bash
# Check schema version
grep schema_version parsed/your-skill.json

# Validate manually
python -c "
import json, jsonschema
schema = json.load(open('schema/skill-decomposition.schema.json'))
data = json.load(open('parsed/your-skill.json'))
jsonschema.validate(data, schema)
"
```

### Issue: Embeddings Out of Date
```bash
# Re-index everything
python -m vector_db.search index --force

# Check stats
python -m vector_db.search stats
```

### Issue: Pattern Extraction Slow
```bash
# Use sampling
python tools/pattern_extractor.py --sample-size 20

# Parallel processing
python tools/pattern_extractor.py -j 4
```

## Integration Examples

### With GitHub Actions
```yaml
name: Validate Skills
on: [push]
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Install deps
        run: pip install -r requirements.txt
      - name: Validate
        run: python tools/analyzer.py -p parsed
```

### With Pre-commit Hook
```bash
# .git/hooks/pre-commit
#!/bin/bash
python tools/analyzer.py -p parsed || exit 1
python tools/evaluate.py -p parsed || exit 1
```

### With CI/CD Pipeline
```bash
# In your CI script
python tools/batch_parse.py -i new_skills/ -o parsed/ --validate
python -m vector_db.search index
python tools/evaluate.py -p parsed > coverage_report.txt
```

## Resources

### Documentation
- [CLAUDE.md](CLAUDE.md) - Claude-specific best practices
- [reference.md](reference.md) - Complete schema reference
- [examples.md](examples.md) - Example decompositions

### Tools
- [analyzer.py](tools/analyzer.py) - Source code
- [pattern_extractor.py](tools/pattern_extractor.py) - Source code
- [search.py](vector_db/search.py) - Source code

### Support
- Issues: https://github.com/pingqLIN/skill-0/issues
- Discussions: https://github.com/pingqLIN/skill-0/discussions

---

*Last updated: 2026-01-28*
