# AGENTS.md - Guidelines for AI Agents Working on skill-0

This document provides context and instructions for AI coding agents working on the skill-0 project.

## Project Overview

skill-0 is a **Ternary Classification System** that parses Claude Skills and MCP Tools into three atomic categories:
- **Actions** (`a_XXX`): Atomic, deterministic operations
- **Rules** (`r_XXX`): Conditional evaluations/judgments  
- **Directives** (`d_XXX`): Descriptive statements about goals/constraints

The project includes:
- 32 parsed skills in JSON format
- Schema v2.0.0 with JSON Schema validation
- Vector database for semantic search (SQLite-vec + sentence-transformers)
- Analysis tools for pattern extraction and evaluation

## Development Environment Tips

### Project Structure
```
skill-0/
├── schema/                    # JSON Schema v2.0.0 definition
├── parsed/                    # 32 parsed skill JSON files
├── tools/                     # Analysis utilities (analyzer, pattern_extractor, evaluate, batch_parse)
├── vector_db/                 # Semantic search (embedder, vector_store, search)
├── scripts/                   # Helper utilities (helper.py)
├── docs/                      # Documentation and planning
└── skills.db                  # SQLite-vec database
```

### Key Files to Know
- `schema/skill-decomposition.schema.json` - Canonical schema definition
- `README.md` - Project overview and usage guide
- `CLAUDE.md` - Best practices for skill decomposition
- `SKILL.md` - Tool portal and workflow guide
- `reference.md` - Complete schema reference
- `examples.md` - Example decompositions

### Installing Dependencies
```bash
pip install -r requirements.txt
```

Dependencies include:
- `sqlite-vec` - Vector database
- `sentence-transformers` - Embedding model
- `scikit-learn` - Clustering
- Standard library (json, pathlib, typing, etc.)

### Virtual Environment Setup
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Working with Skills

### Skill File Format
Each skill is a JSON file following this structure:
```json
{
  "meta": {
    "skill_id": "claude__skill-name",
    "name": "skill-name", 
    "skill_layer": "claude_skill|mcp_tool|mcp_server_internal",
    "title": "Human Readable Title",
    "description": "Brief description",
    "schema_version": "2.0.0",
    "parse_timestamp": "ISO-8601",
    "parser_version": "skill-0 v2.0",
    "parsed_by": "parser-name"
  },
  "decomposition": {
    "actions": [ ... ],
    "rules": [ ... ],
    "directives": [ ... ]
  }
}
```

### ID Conventions
- **Actions**: `a_001`, `a_002`, ..., `a_999`
- **Rules**: `r_001`, `r_002`, ..., `r_999`
- **Directives**: `d_001`, `d_002`, ..., `d_999`

Always use 3-digit zero-padded numbers.

### Action Types (enum)
- `transform` - Data transformation
- `io_read` - Read from external source
- `io_write` - Write to external destination
- `compute` - Mathematical/logical computation
- `external_call` - External API/service call
- `state_change` - State modification
- `llm_inference` - LLM-based operation
- `await_input` - Wait for user input

### Directive Types (enum)
- `completion` - Completion state description
- `knowledge` - Domain knowledge
- `principle` - Guiding principle
- `constraint` - Constraint condition
- `preference` - Preference setting
- `strategy` - Strategy guideline

## Testing and Validation

### Validate a Skill
```bash
# Using helper script
python scripts/helper.py validate parsed/my-skill.json

# Using JSON Schema (manual)
python -c "
import json, jsonschema
schema = json.load(open('schema/skill-decomposition.schema.json'))
skill = json.load(open('parsed/my-skill.json'))
jsonschema.validate(skill, schema)
print('✅ Valid')
"
```

### Test Execution Paths
```bash
python scripts/helper.py test parsed/my-skill.json --analyze
```

### Run Analysis Tools
```bash
# Statistical analysis
python tools/analyzer.py -p parsed -o analysis/report.json

# Pattern extraction
python tools/pattern_extractor.py -o analysis/patterns.json

# Coverage evaluation
python tools/evaluate.py -p parsed
```

### Semantic Search
```bash
# Re-index after adding skills
python -m vector_db.search --db skills.db --parsed-dir parsed index

# Search for skills
python -m vector_db.search search "document processing"

# Find similar skills
python -m vector_db.search similar "Docx Skill"
```

## Coding Conventions

### Python Code Style
- Use **type hints** for function signatures
- Use **dataclasses** for structured data
- Use **pathlib.Path** instead of os.path
- Follow **PEP 8** style guide
- Docstrings in **Traditional Chinese or English**
- Use descriptive variable names

### JSON Formatting
- **2-space indentation**
- **UTF-8 encoding**
- **Sorted keys** (optional but preferred)
- **No trailing commas**
- **ISO 8601 timestamps** (UTC with Z suffix)

### Documentation Style
- Headers use emoji prefixes: `# 🎯`, `## 📊`
- Tables for comparisons and statistics
- Code blocks with language tags
- Bilingual support (Traditional Chinese + English)

## Common Tasks

### Adding a New Skill

1. **Create JSON file** in `parsed/` directory:
   ```bash
   python scripts/helper.py template -o parsed/new-skill.json
   ```

2. **Edit the file** with your decomposition

3. **Validate** the schema:
   ```bash
   python scripts/helper.py validate parsed/new-skill.json
   ```

4. **Re-index** the vector database:
   ```bash
   python -m vector_db.search index
   ```

5. **Verify** the skill is searchable:
   ```bash
   python -m vector_db.search search "new skill description"
   ```

### Updating Schema

⚠️ **Schema changes are breaking changes**

1. Update `schema/skill-decomposition.schema.json`
2. Update schema version if needed
3. Update ALL parsed skills to match
4. Update documentation (README, reference.md)
5. Create migration script if necessary

### Running Batch Operations

```bash
# Parse multiple skills at once
python tools/batch_parse.py -i input_skills/ -o parsed/ --validate

# Analyze all skills
python tools/analyzer.py -p parsed -t > analysis/report.txt

# Re-index all skills
python -m vector_db.search index --force
```

## Error Handling

### Common Issues

**Issue: JSON Schema Validation Fails**
```bash
# Check specific error
python scripts/helper.py validate parsed/skill.json
```

**Issue: Vector Search Returns No Results**
```bash
# Re-index database
python -m vector_db.search index --force

# Check database stats
python -m vector_db.search stats
```

**Issue: ID Pattern Mismatch**
- IDs must be `a_NNN`, `r_NNN`, or `d_NNN` with exactly 3 digits
- Fix: Use regex `^[ard]_\d{3}$` to validate

**Issue: Missing Required Fields**
- Check meta section has all required fields
- Validate decomposition elements have required fields
- Use helper.py validate for detailed errors

## Performance Considerations

### Vector Database
- Indexing: ~30ms per skill (for 32 skills: ~0.88s)
- Search latency: ~75ms average
- Embedding dimension: 384 (all-MiniLM-L6-v2)

### Optimization Tips
- Batch operations for multiple skills
- Cache embeddings during development
- Use `--limit` flag for large result sets
- Pre-filter with `--filter` patterns

## Git Workflow

### Before Committing
1. Validate all modified skill files
2. Run analysis tools to check coverage
3. Update README statistics if needed
4. Re-index vector database if skills changed
5. Test semantic search works correctly

### Commit Message Format
```
<type>: <short description>

<detailed description if needed>

- Bullet points for key changes
- Reference issues with #123
```

Types: feat, fix, docs, style, refactor, test, chore

### Pull Request Checklist
- [ ] All skill files validate successfully
- [ ] Analysis reports updated if needed
- [ ] Vector database re-indexed
- [ ] Documentation updated
- [ ] No merge conflicts
- [ ] Tests pass (if applicable)

## Useful Commands Reference

### Validation
```bash
python scripts/helper.py validate parsed/skill.json
```

### Template Generation
```bash
python scripts/helper.py template -o template.json
```

### Format Conversion
```bash
python scripts/helper.py convert input.md parsed/output.json
```

### Analysis
```bash
python tools/analyzer.py -p parsed -o analysis/report.json -t
python tools/pattern_extractor.py -o analysis/patterns.json
python tools/evaluate.py -p parsed
```

### Search
```bash
python -m vector_db.search index
python -m vector_db.search search "query"
python -m vector_db.search similar "Skill Name"
python -m vector_db.search cluster -n 5
python -m vector_db.search stats
```

### Testing
```bash
python scripts/helper.py test parsed/skill.json --analyze
```

## Resources

### Documentation
- [README.md](README.md) - Project overview
- [CLAUDE.md](CLAUDE.md) - Claude best practices
- [SKILL.md](SKILL.md) - Tool portal guide
- [reference.md](reference.md) - Schema reference
- [examples.md](examples.md) - Example decompositions

### Schema
- [skill-decomposition.schema.json](schema/skill-decomposition.schema.json) - JSON Schema v2.0.0

### Tools
- [analyzer.py](tools/analyzer.py) - Statistical analysis
- [pattern_extractor.py](tools/pattern_extractor.py) - Pattern discovery
- [evaluate.py](tools/evaluate.py) - Coverage evaluation
- [batch_parse.py](tools/batch_parse.py) - Batch processing
- [helper.py](scripts/helper.py) - Helper utilities

### External References
- Claude Skills: https://github.com/ComposioHQ/awesome-claude-skills
- MCP Documentation: https://github.com/modelcontextprotocol
- JSON Schema: https://json-schema.org/
- SQLite-vec: https://github.com/asg017/sqlite-vec

## Best Practices for AI Agents

### When Modifying Skills
1. Always validate before and after changes
2. Maintain ID sequence consistency
3. Preserve schema version compatibility
4. Update timestamps and parser_version
5. Re-index vector database after changes

### When Adding Features
1. Check existing patterns in parsed skills
2. Maintain backward compatibility
3. Update documentation alongside code
4. Add examples to examples.md if applicable
5. Run full test suite

### When Encountering Errors
1. Use helper.py validate for detailed errors
2. Check schema definition for requirements
3. Compare with working examples in parsed/
4. Review reference.md for field specifications
5. Test incrementally with small changes

## Questions or Issues?

- Check documentation in [docs/](docs/) directory
- Review existing skills in [parsed/](parsed/) directory
- Run validation and analysis tools
- Open an issue on GitHub: https://github.com/pingqLIN/skill-0/issues

---

*This AGENTS.md file follows the format from https://agents.md*  
*Last updated: 2026-01-28*
