# Claude Best Practices for Skill-0

> Guidelines for working with skill-0 decomposition system and Claude AI integration

## Overview

This document outlines best practices when working with the skill-0 ternary classification system, whether you're parsing existing Claude Skills, creating new decompositions, or integrating with Claude AI for skill analysis.

## Core Principles

### 1. Atomic Decomposition
- **Actions** must be indivisible operations with deterministic outcomes
- **Rules** should evaluate to clear boolean/classification results
- **Directives** describe states, goals, or principles without further decomposition at current level

### 2. Immutability
- Identify which elements are immutable (fixed behavior)
- Track mutable elements (parameters that can vary)
- Document side effects explicitly

### 3. Schema Compliance
- Always validate against `schema/skill-decomposition.schema.json` (v2.0.0)
- Use correct ID patterns: `a_XXX`, `r_XXX`, `d_XXX`
- Include all required fields in meta section

## Working with Actions

### Action Types (Choose appropriately)
```
transform       - Data transformation without I/O
io_read         - Reading from external sources
io_write        - Writing to external destinations
compute         - Mathematical/logical computation
external_call   - API/service calls
state_change    - State modifications
llm_inference   - LLM-based operations
await_input     - Waiting for user input
```

### Best Practices
- Keep actions atomic - if you can split it, it's not atomic enough
- Mark `deterministic: false` only for truly non-deterministic operations (LLM, external APIs)
- Document side effects even if they seem obvious
- Use clear, verb-based naming: "Read PDF", not "PDF Reader"

### Example
```json
{
  "id": "a_001",
  "name": "Read PDF Document",
  "action_type": "io_read",
  "description": "Reads PDF file from specified path into memory",
  "deterministic": true,
  "immutable_elements": ["file_format: PDF"],
  "mutable_elements": ["file_path"],
  "side_effects": ["memory_allocation"]
}
```

## Working with Rules

### Condition Types
```
validation         - Input validation
existence_check    - File/resource existence
type_check         - Type verification
range_check        - Value range validation
permission_check   - Access control
state_check        - State verification
consistency_check  - Data consistency
threshold_check    - Threshold comparison
```

### Best Practices
- Rules must return clear results: boolean, classification, enum, or score
- Define failure consequences explicitly
- Keep conditions simple and testable
- Use descriptive names that indicate what's being checked

### Example
```json
{
  "id": "r_001",
  "name": "Verify PDF Has Tables",
  "condition_type": "existence_check",
  "condition": "PDF document contains at least one table structure",
  "output": "boolean",
  "description": "Checks if the PDF contains extractable table data"
}
```

## Working with Directives

### Directive Types
```
completion  - Success/completion states
knowledge   - Domain-specific knowledge
principle   - Design principles
constraint  - System constraints
preference  - User/system preferences
strategy    - Algorithmic strategies
```

### Best Practices
- Mark `decomposable: true` if directive can be further broken down
- Provide decomposition hints when applicable
- Use directives for context that doesn't fit actions/rules
- Keep descriptions clear and actionable

### Example
```json
{
  "id": "d_001",
  "directive_type": "completion",
  "description": "All tables extracted and formatted as Excel sheets",
  "decomposable": true,
  "decomposition_hint": "Can decompose into: extract tables, format cells, write Excel"
}
```

## Context Window Optimization

### For Large Skills
1. **Prioritize Core Elements**: Focus on actions and critical rules first
2. **Batch Processing**: Use `tools/batch_parse.py` for multiple skills
3. **Incremental Decomposition**: Start with high-level directives, decompose later
4. **Reference Reuse**: Link to existing patterns in `analysis/patterns.json`

### Token Budget Management
- Average skill: 200-400 tokens (JSON)
- Complex skill: 600-1000 tokens
- Use `description` field wisely - be concise
- Reference external docs instead of repeating

## Claude-Specific Patterns

### When to Use LLM Inference Action Type
Mark as `llm_inference` when:
- Operation involves natural language understanding
- Requires reasoning or interpretation
- Output varies based on semantic context
- Non-deterministic by nature

### Handling Multi-Step Skills
```json
{
  "execution_paths": [
    {
      "path_name": "Happy Path",
      "sequence": ["a_001", "r_001", "a_002", "d_001"],
      "description": "Standard PDF table extraction flow"
    }
  ]
}
```

## Integration with Vector Search

### Naming Conventions for Searchability
- Use clear, domain-specific terms in names
- Include synonyms in descriptions
- Tag related concepts explicitly

### Example
```json
{
  "name": "Extract Data from Spreadsheet",
  "description": "Reads and parses Excel/CSV files (alias: parse worksheet, load tabular data)"
}
```

## Validation Workflow

### Before Committing
1. **Schema Validation**
   ```bash
   python -c "import json, jsonschema; ..."
   ```

2. **Pattern Consistency**
   ```bash
   python tools/analyzer.py -p parsed -o analysis/report.json
   ```

3. **Vector Indexing**
   ```bash
   python -m vector_db.search --db skills.db --parsed-dir parsed index
   ```

4. **Semantic Verification**
   ```bash
   python -m vector_db.search search "your skill description"
   ```

## Common Pitfalls

### ❌ Avoid
- Mixing actions with rules (e.g., "Read and validate file")
- Vague directive types (use specific type from enum)
- Missing required fields in meta section
- Inconsistent ID numbering
- Over-decomposition (creating non-atomic actions)

### ✅ Do
- One action = one operation
- Clear, testable rules
- Descriptive directives with context
- Complete meta information
- Consistent naming patterns

## Testing Your Decomposition

### Manual Review Checklist
- [ ] All actions are atomic and deterministic (or marked otherwise)
- [ ] All rules have clear conditions and outputs
- [ ] All directives have appropriate types
- [ ] IDs follow pattern: `a_001`, `r_001`, `d_001`
- [ ] Meta section is complete
- [ ] Schema validation passes

### Automated Validation
```bash
# Run full analysis
python tools/evaluate.py -p parsed

# Check coverage
python tools/pattern_extractor.py -o analysis/patterns.json

# Test semantic search
python -m vector_db.search similar "Your Skill Name"
```

## Contributing New Skills

### Workflow
1. **Research**: Study existing similar skills in `parsed/`
2. **Draft**: Create initial decomposition
3. **Validate**: Check against schema
4. **Test**: Run semantic search to find duplicates
5. **Document**: Add to appropriate category
6. **Submit**: Include analysis report

### Template
Use `parsed/template.json` (if exists) or copy structure from `parsed/docx-skill.json`

## Performance Considerations

### Indexing
- Batch operations: ~30ms per skill
- Vector generation: ~10ms per skill
- Search latency: ~75ms average

### Optimization Tips
- Pre-index before batch operations
- Cache embeddings for repeated searches
- Use `--filter` flags for targeted analysis

## Resources

### Internal Documentation
- [README.md](README.md) - Project overview
- [schema/skill-decomposition.schema.json](schema/skill-decomposition.schema.json) - Schema specification
- [tools/README.md](tools/README.md) - Tool documentation
- [docs/skill-0-framework-evaluation.md](docs/skill-0-framework-evaluation.md) - Framework evaluation

### External References
- Claude Skills: https://github.com/ComposioHQ/awesome-claude-skills
- MCP Documentation: https://github.com/modelcontextprotocol
- JSON Schema: https://json-schema.org/

## Version History

- **2.0.0** (2026-01-26): Directive-based classification
- **1.1.0** (2026-01-23): Initial release

---

*For questions or improvements, please open an issue or PR in the repository.*
