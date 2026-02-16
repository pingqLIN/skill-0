# Skill-0 Schema Reference

> Complete reference for skill decomposition schema v2.0.0

## Schema Overview

### Meta Information
Every skill decomposition must include complete metadata:

```json
{
  "meta": {
    "skill_id": "string",           // Format: "claude__<name>" or "mcp__<name>"
    "name": "string",                // Skill identifier
    "skill_layer": "enum",           // claude_skill | mcp_tool | mcp_server_internal
    "title": "string",               // Human-readable title
    "description": "string",         // Brief description
    "schema_version": "2.0.0",       // Current schema version
    "parse_timestamp": "ISO-8601",   // When parsed
    "parser_version": "string",      // Parser tool version
    "parsed_by": "string"            // Parser identifier
  }
}
```

### Field Specifications

| Field | Type | Required | Pattern/Constraints |
|-------|------|----------|---------------------|
| `skill_id` | string | ✅ | Must be unique within repository |
| `name` | string | ✅ | Lowercase, alphanumeric with hyphens |
| `skill_layer` | enum | ✅ | One of: claude_skill, mcp_tool, mcp_server_internal |
| `title` | string | ✅ | Clear, concise title |
| `description` | string | ✅ | 1-3 sentences |
| `schema_version` | string | ✅ | "2.0.0" (current) |
| `parse_timestamp` | string | ✅ | ISO 8601 format |
| `parser_version` | string | ✅ | Version of parser used |
| `parsed_by` | string | ✅ | Tool or person identifier |

## Original Definition

Preserve the original skill definition for reference:

```json
{
  "original_definition": {
    "source": "string",              // URL or file path
    "skill_name": "string",          // Original name
    "skill_description": "string"    // Original description
  }
}
```

## Decomposition Structure

### Actions

Atomic operations that perform specific tasks.

```json
{
  "id": "a_XXX",                     // Pattern: a_001, a_002, ...
  "name": "string",                  // Clear, verb-based name
  "action_type": "enum",             // See Action Types below
  "description": "string",           // What it does
  "deterministic": "boolean",        // True if output is predictable
  "immutable_elements": ["string"],  // Fixed elements
  "mutable_elements": ["string"],    // Variable parameters
  "side_effects": ["string"]         // External effects
}
```

#### Action Types

| Type | Description | Deterministic? | Examples |
|------|-------------|----------------|----------|
| `transform` | Data transformation | Usually ✅ | Parse JSON, Convert format |
| `io_read` | Read from external source | ✅ | Read file, Fetch URL |
| `io_write` | Write to external destination | ✅ | Write file, Send data |
| `compute` | Mathematical/logical computation | ✅ | Calculate sum, Sort array |
| `external_call` | Call external API/service | ❌ | REST API call, Database query |
| `state_change` | Modify system state | ✅ | Update variable, Set flag |
| `llm_inference` | LLM-based operation | ❌ | Generate text, Classify intent |
| `await_input` | Wait for user input | ❌ | Prompt user, Get confirmation |

#### Deterministic Guidelines
- **True**: Same input always produces same output
- **False**: Output may vary (network, LLM, user input, random)

#### Immutable Elements
Elements that cannot change without changing the action's identity:
- File formats (e.g., "format: PDF")
- Protocols (e.g., "protocol: HTTPS")
- Algorithms (e.g., "algorithm: SHA-256")

#### Mutable Elements
Parameters that can vary between invocations:
- File paths
- API endpoints
- Configuration values
- User preferences

#### Side Effects
External effects that persist after action completes:
- `memory_allocation`
- `file_creation`
- `network_traffic`
- `state_modification`
- `cache_update`

### Rules

Atomic judgments that evaluate conditions without performing actions.

```json
{
  "id": "r_XXX",                     // Pattern: r_001, r_002, ...
  "name": "string",                  // Clear, condition-based name
  "condition_type": "enum",          // See Condition Types below
  "condition": "string",             // What is being evaluated
  "output": "enum",                  // Result type
  "description": "string"            // Purpose and context
}
```

#### Condition Types

| Type | Purpose | Output | Example |
|------|---------|--------|---------|
| `validation` | Input validation | boolean/enum | Validate email format |
| `existence_check` | Resource existence | boolean | Check file exists |
| `type_check` | Type verification | boolean/enum | Verify data type |
| `range_check` | Value range validation | boolean | Check value in range |
| `permission_check` | Access control | boolean | User has permission |
| `state_check` | State verification | boolean/enum | System is ready |
| `consistency_check` | Data consistency | boolean | Data is consistent |
| `threshold_check` | Threshold comparison | boolean/score | Value exceeds threshold |

#### Output Types

| Type | Description | Example Values |
|------|-------------|----------------|
| `boolean` | True/False result | true, false |
| `classification` | Category result | "valid", "invalid", "warning" |
| `enum_value` | Enumerated value | "low", "medium", "high" |
| `score` | Numeric score | 0.85, 42, 95.5 |

### Directives

Descriptive statements providing context, goals, or constraints.

```json
{
  "id": "d_XXX",                     // Pattern: d_001, d_002, ...
  "directive_type": "enum",          // See Directive Types below
  "description": "string",           // What it describes
  "decomposable": "boolean",         // Can be further decomposed?
  "decomposition_hint": "string"     // Optional: How to decompose
}
```

#### Directive Types

| Type | Purpose | When to Use | Example |
|------|---------|-------------|---------|
| `completion` | Success state | Define done criteria | "All data exported to CSV" |
| `knowledge` | Domain knowledge | Provide context | "PDF 1.7 specification" |
| `principle` | Guiding principle | State design rule | "Minimize token usage" |
| `constraint` | System constraint | Define limitation | "Maximum 100 MB file size" |
| `preference` | User preference | User settings | "User prefers JSON output" |
| `strategy` | Algorithmic strategy | Define approach | "Retry up to 3 times" |

#### Decomposable Field
- **true**: Directive can be broken into smaller elements
- **false**: Already at appropriate level of detail

#### Decomposition Hint (Optional)
Guidance for future decomposition:
```json
{
  "decomposable": true,
  "decomposition_hint": "Can split into: validate format, extract data, transform structure"
}
```

## Execution Paths (Optional)

Document common execution sequences:

```json
{
  "execution_paths": [
    {
      "path_name": "string",         // Name of this path
      "sequence": ["id"],            // Ordered list of element IDs
      "description": "string"        // When/why this path executes
    }
  ]
}
```

### Example
```json
{
  "execution_paths": [
    {
      "path_name": "Happy Path",
      "sequence": ["a_001", "r_001", "a_002", "d_001"],
      "description": "Standard successful execution"
    },
    {
      "path_name": "Validation Failure",
      "sequence": ["a_001", "r_001", "d_002"],
      "description": "Execution when validation fails"
    }
  ]
}
```

## ID Formatting Rules

### Patterns
- Actions: `a_` + 3 digits (e.g., `a_001`, `a_099`)
- Rules: `r_` + 3 digits (e.g., `r_001`, `r_050`)
- Directives: `d_` + 3 digits (e.g., `d_001`, `d_025`)

### Numbering
- Start from 001 for each type
- Increment sequentially
- Pad with leading zeros
- No gaps in sequence

### Examples
```
✅ Valid:   a_001, a_002, a_003
❌ Invalid: a_1, a_01, a_0001
❌ Invalid: a001, A_001, action_001
```

## Complete Example

```json
{
  "meta": {
    "skill_id": "claude__pdf-extraction",
    "name": "pdf-extraction",
    "skill_layer": "claude_skill",
    "title": "PDF Data Extraction Skill",
    "description": "Extract structured data from PDF documents including text, tables, and images",
    "schema_version": "2.0.0",
    "parse_timestamp": "2026-01-28T10:30:00Z",
    "parser_version": "skill-0 v2.0",
    "parsed_by": "skill-0-batch"
  },
  "original_definition": {
    "source": "https://example.com/pdf-skill",
    "skill_name": "PDF Extraction",
    "skill_description": "Extract data from PDFs"
  },
  "decomposition": {
    "actions": [
      {
        "id": "a_001",
        "name": "Read PDF File",
        "action_type": "io_read",
        "description": "Reads PDF file from specified path into memory",
        "deterministic": true,
        "immutable_elements": ["file_format: PDF"],
        "mutable_elements": ["file_path"],
        "side_effects": ["memory_allocation"]
      },
      {
        "id": "a_002",
        "name": "Extract Text Content",
        "action_type": "transform",
        "description": "Extracts all text content from PDF pages",
        "deterministic": true,
        "immutable_elements": ["extraction_method: pypdf"],
        "mutable_elements": [],
        "side_effects": []
      },
      {
        "id": "a_003",
        "name": "Extract Tables",
        "action_type": "transform",
        "description": "Identifies and extracts table structures",
        "deterministic": false,
        "immutable_elements": [],
        "mutable_elements": ["detection_threshold"],
        "side_effects": []
      }
    ],
    "rules": [
      {
        "id": "r_001",
        "name": "Verify File Exists",
        "condition_type": "existence_check",
        "condition": "PDF file exists at specified path",
        "output": "boolean",
        "description": "Checks if the file exists before attempting to read"
      },
      {
        "id": "r_002",
        "name": "Validate PDF Format",
        "condition_type": "validation",
        "condition": "File has valid PDF header and structure",
        "output": "boolean",
        "description": "Ensures file is a valid PDF document"
      }
    ],
    "directives": [
      {
        "id": "d_001",
        "directive_type": "completion",
        "description": "All extractable data has been successfully retrieved and structured",
        "decomposable": false
      },
      {
        "id": "d_002",
        "directive_type": "constraint",
        "description": "Maximum file size: 50 MB",
        "decomposable": false
      },
      {
        "id": "d_003",
        "directive_type": "knowledge",
        "description": "PDF specification version 1.7 (ISO 32000-1)",
        "decomposable": true,
        "decomposition_hint": "Can detail specific PDF features: annotations, forms, encryption"
      }
    ]
  },
  "execution_paths": [
    {
      "path_name": "Standard Extraction",
      "sequence": ["r_001", "r_002", "a_001", "a_002", "a_003", "d_001"],
      "description": "Normal flow for valid PDF files"
    },
    {
      "path_name": "Invalid File",
      "sequence": ["r_001", "d_002"],
      "description": "Abort when file doesn't exist"
    }
  ]
}
```

## Schema Validation

### JSON Schema Location
`schema/skill-decomposition.schema.json`

### Validation Command
```bash
python -c "
import json
import jsonschema

# Load schema
with open('schema/skill-decomposition.schema.json') as f:
    schema = json.load(f)

# Load skill
with open('parsed/your-skill.json') as f:
    skill = json.load(f)

# Validate
try:
    jsonschema.validate(skill, schema)
    print('✅ Valid')
except jsonschema.ValidationError as e:
    print(f'❌ Validation Error: {e.message}')
"
```

### Common Validation Errors

#### Missing Required Field
```
Error: 'skill_id' is a required property
Fix: Add all required meta fields
```

#### Invalid ID Pattern
```
Error: 'a_1' does not match pattern '^a_[0-9]{3}$'
Fix: Use correct format: a_001
```

#### Invalid Enum Value
```
Error: 'unknown' is not one of ['claude_skill', 'mcp_tool', 'mcp_server_internal']
Fix: Use valid skill_layer value
```

#### Type Mismatch
```
Error: True is not of type 'string'
Fix: Ensure field types match schema
```

## Migration Guides

### From v1.1.0 to v2.0.0

#### Changed Elements
| v1.1.0 | v2.0.0 | Notes |
|--------|--------|-------|
| `core_action` | `action` | Renamed for clarity |
| `ca_XXX` | `a_XXX` | Simplified ID prefix |
| `mission` | `directive` | More descriptive term |
| `m_XXX` | `d_XXX` | New ID prefix |

#### New Fields
- `directive_type`: Required enum field
- `decomposable`: Boolean flag
- `decomposition_hint`: Optional guidance
- `await_input`: New action type

#### Migration Script
```python
import json

def migrate_v1_to_v2(old_skill):
    new_skill = old_skill.copy()
    
    # Update schema version
    new_skill['meta']['schema_version'] = '2.0.0'
    
    # Rename core_action to action
    if 'core_action' in old_skill['decomposition']:
        new_skill['decomposition']['actions'] = old_skill['decomposition']['core_action']
        del new_skill['decomposition']['core_action']
    
    # Update action IDs: ca_XXX -> a_XXX
    for action in new_skill['decomposition']['actions']:
        if action['id'].startswith('ca_'):
            action['id'] = 'a_' + action['id'][3:]
    
    # Rename mission to directive
    if 'mission' in old_skill['decomposition']:
        new_skill['decomposition']['directives'] = old_skill['decomposition']['mission']
        del new_skill['decomposition']['mission']
    
    # Update directive IDs: m_XXX -> d_XXX
    for directive in new_skill['decomposition']['directives']:
        if directive['id'].startswith('m_'):
            directive['id'] = 'd_' + directive['id'][2:]
        
        # Add directive_type if missing
        if 'directive_type' not in directive:
            directive['directive_type'] = 'completion'  # Default
        
        # Add decomposable if missing
        if 'decomposable' not in directive:
            directive['decomposable'] = False
    
    return new_skill

# Usage
with open('old_skill.json') as f:
    old = json.load(f)

new = migrate_v1_to_v2(old)

with open('new_skill.json', 'w') as f:
    json.dump(new, f, indent=2)
```

## Best Practices

### Naming Conventions
- **Actions**: Start with verb (Read, Extract, Transform)
- **Rules**: Start with condition (Check, Verify, Validate)
- **Directives**: Describe state or goal

### Description Quality
- Be specific and concrete
- Include relevant details
- Avoid ambiguity
- Use consistent terminology

### Element Count Guidelines
| Skill Complexity | Actions | Rules | Directives |
|------------------|---------|-------|------------|
| Simple | 2-5 | 1-2 | 1-3 |
| Medium | 5-10 | 2-5 | 3-5 |
| Complex | 10-20 | 5-10 | 5-10 |

### When to Create New Action vs Rule
- **Action**: Performs transformation or I/O
- **Rule**: Only evaluates condition

### When to Use Directive vs Action
- **Directive**: Describes context, goal, or principle
- **Action**: Executes specific operation

## Advanced Features

### Nested References
Reference other skills in decomposition:
```json
{
  "id": "a_001",
  "name": "Process Document",
  "action_type": "external_call",
  "description": "Delegates to pdf-skill for processing",
  "immutable_elements": ["delegate_to: pdf-skill"]
}
```

### Conditional Execution
Document branching logic:
```json
{
  "execution_paths": [
    {
      "path_name": "With Tables",
      "sequence": ["a_001", "r_001", "a_002"],
      "description": "When r_001 returns true"
    },
    {
      "path_name": "No Tables",
      "sequence": ["a_001", "r_001", "d_001"],
      "description": "When r_001 returns false"
    }
  ]
}
```

### Parallel Execution
Indicate concurrent operations:
```json
{
  "execution_paths": [
    {
      "path_name": "Parallel Processing",
      "sequence": [
        "a_001",
        ["a_002", "a_003", "a_004"],  // These run in parallel
        "a_005"
      ],
      "description": "Process multiple operations concurrently"
    }
  ]
}
```

## Troubleshooting

### Issue: ID Conflicts
**Symptom**: Duplicate IDs across skills
**Solution**: Ensure IDs are unique within each skill file

### Issue: Schema Version Mismatch
**Symptom**: Old schema version in new files
**Solution**: Update to "2.0.0" in meta section

### Issue: Missing Directive Types
**Symptom**: Validation fails on directive_type
**Solution**: Add appropriate directive_type from enum

### Issue: Incorrect Deterministic Flag
**Symptom**: LLM operations marked deterministic
**Solution**: Set deterministic: false for non-deterministic operations

## Resources

- [JSON Schema Specification](schema/skill-decomposition.schema.json)
- [Example Skills](parsed/)
- [CLAUDE.md](CLAUDE.md) - Best practices
- [SKILL.md](SKILL.md) - Tool portal

---

*Schema Version: 2.0.0*  
*Last Updated: 2026-01-28*
