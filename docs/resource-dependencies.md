# Resource Dependency System

**Schema Version:** 2.2.0  
**Project Version:** 2.4.0  
**Feature Added:** 2026-01-30  
**Status:** Production

## Overview

The Resource Dependency System in skill-0 schema v2.2.0 provides a standardized way to declare and document external resources required for skill execution. This enables better validation, deployment planning, and runtime resource management.

## Motivation

Modern AI skills and MCP servers often depend on external resources:
- **MCP Servers**: Database connections, API credentials, file systems
- **Claude Skills**: External APIs, memory caches, GPU resources
- **AI Agents**: Credentials, network access, environment variables

Without explicit resource declarations, deployment and execution failures are common. The resource dependency system addresses this by:
1. Making resource requirements explicit and discoverable
2. Enabling validation before execution
3. Supporting fallback strategies
4. Documenting resource specifications

## Resource Types

The schema defines 8 resource types:

| Type | Description | Examples |
|------|-------------|----------|
| `filesystem` | File system access | Local files, mounted volumes, shared drives |
| `database` | Database connections | PostgreSQL, MongoDB, MySQL, Redis |
| `api` | External API services | OpenAI API, GitHub API, REST services |
| `network` | Network connectivity | Internet access, VPN, proxy |
| `gpu` | GPU resources | CUDA, TPU, GPU memory |
| `memory` | Memory/cache systems | Redis, Memcached, in-memory cache |
| `credentials` | Authentication credentials | API keys, tokens, certificates |
| `environment` | Environment variables | Config values, secrets, system settings |

## Resource Definition Structure

### Basic Structure

```json
{
  "type": "database",
  "name": "primary_db",
  "required": true,
  "description": "Primary PostgreSQL database"
}
```

### Full Structure with Specification

```json
{
  "type": "database",
  "name": "primary_database",
  "required": true,
  "description": "Primary database connection for query execution",
  "specification": {
    "provider": "PostgreSQL",
    "version": ">=14.0",
    "endpoint": "postgresql://localhost:5432/mydb",
    "permissions": ["SELECT", "EXPLAIN"]
  },
  "fallback": "Use read-only replica if primary is unavailable"
}
```

## Declaration Levels

Resources can be declared at two levels:

### 1. Meta Level (Global Resources)

Declared in the `meta` section, these resources are required for the entire skill:

```json
{
  "meta": {
    "skill_id": "mcp__database__query_tool",
    "name": "Database Query Tool",
    "resources": [
      {
        "type": "database",
        "name": "primary_db",
        "required": true,
        "description": "Main database connection"
      }
    ]
  }
}
```

### 2. Action Level (Action-Specific Resources)

Declared within individual actions for fine-grained resource tracking:

```json
{
  "decomposition": {
    "actions": [
      {
        "id": "a_001",
        "name": "Query Database",
        "action_type": "external_call",
        "resources": [
          {
            "type": "database",
            "name": "primary_db",
            "required": true
          },
          {
            "type": "credentials",
            "name": "db_credentials",
            "required": true
          }
        ]
      }
    ]
  }
}
```

## Specification Details

The `specification` object provides detailed resource configuration:

```json
{
  "specification": {
    "provider": "OpenAI",          // Resource provider/vendor
    "version": ">=3.5",             // Version requirements
    "endpoint": "https://api.openai.com/v1",  // Connection endpoint
    "permissions": ["read", "write"]  // Required permissions
  }
}
```

### Common Specification Patterns

**Database:**
```json
{
  "provider": "PostgreSQL",
  "version": ">=14.0",
  "endpoint": "postgresql://localhost:5432/mydb",
  "permissions": ["SELECT", "INSERT", "UPDATE"]
}
```

**API Service:**
```json
{
  "provider": "OpenAI",
  "version": "v1",
  "endpoint": "https://api.openai.com/v1",
  "permissions": ["chat.completions.create"]
}
```

**Credentials:**
```json
{
  "provider": "environment",
  "permissions": ["read"],
  "variables": ["OPENAI_API_KEY", "DB_PASSWORD"]
}
```

## Fallback Strategies

The optional `fallback` field describes alternative behavior when a resource is unavailable:

```json
{
  "type": "memory",
  "name": "query_cache",
  "required": false,
  "fallback": "Skip caching if Redis unavailable, fetch directly from database"
}
```

### Fallback Patterns

1. **Skip Feature**: "Skip caching if unavailable"
2. **Use Alternative**: "Use read-only replica if primary is down"
3. **Degrade Gracefully**: "Reduce batch size if GPU memory insufficient"
4. **Fail Safe**: "Return cached results if API unavailable"

## Usage Examples

### Example 1: Database MCP Server

```json
{
  "meta": {
    "skill_id": "mcp__database__query_analyzer",
    "name": "Database Query Analyzer",
    "resources": [
      {
        "type": "database",
        "name": "primary_database",
        "required": true,
        "description": "Primary database for analysis",
        "specification": {
          "provider": "PostgreSQL",
          "version": ">=14.0",
          "permissions": ["SELECT", "EXPLAIN"]
        }
      },
      {
        "type": "credentials",
        "name": "db_credentials",
        "required": true,
        "description": "Database authentication"
      }
    ]
  }
}
```

### Example 2: LLM-Enhanced Action

```json
{
  "id": "a_004",
  "name": "Analyze with LLM",
  "action_type": "llm_inference",
  "resources": [
    {
      "type": "api",
      "name": "llm_api",
      "required": true,
      "description": "LLM API for analysis",
      "specification": {
        "provider": "OpenAI",
        "endpoint": "https://api.openai.com/v1"
      }
    },
    {
      "type": "credentials",
      "name": "openai_api_key",
      "required": true
    }
  ]
}
```

### Example 3: GPU Computing

```json
{
  "id": "a_005",
  "name": "Train Model",
  "action_type": "compute",
  "resources": [
    {
      "type": "gpu",
      "name": "cuda_device",
      "required": true,
      "description": "CUDA-capable GPU for training",
      "specification": {
        "provider": "NVIDIA",
        "version": ">=12.0",
        "memory": ">=8GB"
      },
      "fallback": "Use CPU training with reduced batch size"
    }
  ]
}
```

## Validation

Use the schema validator to ensure resource definitions are correct:

```bash
# Validate skill with resources
python scripts/helper.py validate examples/database-query-analyzer-with-resources.json
```

```python
import json
import jsonschema

with open('schema/skill-decomposition.schema.json') as f:
    schema = json.load(f)

with open('my-skill.json') as f:
    skill = json.load(f)

jsonschema.validate(instance=skill, schema=schema)
```

## Best Practices

### 1. Global vs Action Resources

- **Use global** (meta-level) for resources needed by multiple actions
- **Use action-level** for resources specific to one action
- Duplicate declarations are acceptable for clarity

### 2. Required vs Optional

- Mark as `required: true` if skill cannot function without it
- Mark as `required: false` for optional optimizations (caches, GPU)
- Always provide fallback for optional resources

### 3. Specification Details

- Include version requirements to prevent compatibility issues
- Document required permissions for security auditing
- Specify endpoints when multiple options exist

### 4. Fallback Strategies

- Describe concrete fallback behavior, not just "fail gracefully"
- Test fallback paths to ensure they work
- Document performance implications of fallbacks

### 5. Security Considerations

- Never include actual credentials in resource definitions
- Reference credential sources (environment, vault, etc.)
- Document minimum required permissions

## Migration from v2.1

Schema v2.2 is backward compatible with v2.1. The resource dependency feature is optional.

To add resources to existing skills:

1. Add `resources` array to `meta` section (optional)
2. Add `resources` array to individual actions (optional)
3. Update `schema_version` to "2.2.0"

**Note**: Project version (v2.4.0) and schema version (v2.2.0) are different. Update your skill's `schema_version` field to "2.2.0" when using resource dependencies.

Example migration:

**Before (v2.1):**
```json
{
  "meta": {
    "schema_version": "2.1.0"
  },
  "decomposition": {
    "actions": [
      {
        "id": "a_001",
        "name": "Query DB",
        "description": "Requires PostgreSQL connection"
      }
    ]
  }
}
```

**After (v2.2):**
```json
{
  "meta": {
    "schema_version": "2.2.0",
    "resources": [
      {
        "type": "database",
        "name": "postgres",
        "required": true
      }
    ]
  },
  "decomposition": {
    "actions": [
      {
        "id": "a_001",
        "name": "Query DB",
        "resources": [
          {
            "type": "database",
            "name": "postgres",
            "required": true
          }
        ]
      }
    ]
  }
}
```

## Future Enhancements

Potential future additions to the resource system:

1. **Resource Dependencies**: Express dependencies between resources
2. **Resource Pools**: Share resources across multiple skills
3. **Resource Monitoring**: Track resource usage and performance
4. **Auto-Discovery**: Automatically detect resources from code
5. **Resource Templates**: Reusable resource configurations

## References

- Full schema: [schema/skill-decomposition.schema.json](../schema/skill-decomposition.schema.json)
- Complete example: [examples/database-query-analyzer-with-resources.json](../examples/database-query-analyzer-with-resources.json)
- GitHub search report: [docs/github-skills-search-report.md](github-skills-search-report.md)

---

*Resource Dependency System Documentation*  
*skill-0 Project | Schema v2.2.0*
