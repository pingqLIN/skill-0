# Skill-0 Development Conversation Log
**Date:** 2026-01-23  
**User:** pingqLIN  
**Topic:** MCP Skill Decomposition Parser Development

---

## Conversation Summary

This conversation established a ternary classification system for parsing Claude Skills and MCP Tools.

### Main Achievements

1. **Defined Ternary Classification System**
   - Core Action (core actions)
   - Rules (judgment rules)
   - Mission (tasks/works)

2. **Established JSON Schema Specification v1.1.0**

3. **Completed 4 Skill Parsing Examples**
   - Skill 0: skill_decomposition_parser (the parser itself)
   - Skill 1: echo (MCP Tool)
   - Skill 2: get_current_time (MCP Tool)
   - Skill 3: get-sum (MCP Tool)

---

## Complete Conversation Log

### User 1
I want to create an online program that can parse different skills, including judgments, applied technologies, software, and other relationships to analyze their component structure. First, do basic and extensive research to confirm the basic types and methods of skills.

### Assistant 1
[Conducted basic research to confirm types of Skills]

Raised confirmation questions:
1. Definition scope of Skills (professional skills, game skills, AI/Chatbot skills, etc.)
2. Goals for parsing component structure
3. Expected output format

### User 2
AI/Chatbot skills (such as Alexa Skills, Copilot Skills) are all included, but not too detailed.

### Assistant 2
[Conducted AI/Chatbot Skills framework research]

Organized comparison of major platforms:
- Alexa Skills
- Microsoft Copilot Skills  
- GPT Plugins/Custom GPTs
- Claude Tools
- Dialogflow
- Rasa

### User 3
Correction: specifically Claude skills as the main focus for related discussions.

### Assistant 3
[Conducted in-depth research on Claude Skills / MCP]

Organized:
1. MCP (Model Context Protocol) core structure
2. Tool definition structure (name, title, description, inputSchema)
3. Server Capabilities
4. Call flow (JSON-RPC 2.0)
5. MCP 2025-2026 new features

### User 4
1. Define parsing: organize and classify the parts of different skills that are immutable or whose changes will affect the results:
   1. core action: basic operations without judgment value systems (or currently unable to judge)
   2. rules: pure judgment, discussing classification without actions
   3. mission: task/work, the final goal direction
   
   After identifying the above categories, output them in order. For paths with different routes, traverse all possibilities and display them. For cases with too many (predictable/post-execution judgment) states, stop parsing and note it first.

2. First make examples of the top 10 popular MCP tools.

3. [Incomplete]

### Assistant 4
[Established ternary classification definition framework]

1. Defined complete specifications for Core Action, Rules, and Mission
2. Designed parsing output JSON format
3. Organized and analyzed the top 10 popular MCP Servers:
   - GitHub MCP Server
   - Filesystem MCP Server
   - PostgreSQL MCP Server
   - Slack MCP Server
   - Context7
   - Sequential Thinking
   - Google Drive MCP Server
   - Notion MCP Server
   - Apidog MCP Server
   - Puppeteer MCP Server

### User 5
Actually, MCP Server can continue to be parsed, but the project is huge and may not have results (internal black box). Just use MCP unit as a parsing pause point (can continue to parse if needed, for example, when the skill input judgment system considers the output inconsistent after the same data passes through a certain MCP).

The current goal is to parse all elements of skill content according to the above operations, output and convert to formal JSON specification.

B Program architecture I currently tend to use LLM model to operate and output pure text.

C Find 3 basic skills to execute.

### Assistant 5
[Retrieved actual Tool definitions from official MCP Server repository]

Established formal JSON Schema specification and completed 3 basic MCP Skill parsings:
1. echo
2. get_current_time
3. get-sum

### User 6
The ternary classification I'm referring to also needs to analyze Claude skills together.

### Assistant 6
[Completed meta-parsing - performed ternary classification on the parser itself as a Skill]

Produced complete 4 Skill parsings:

**Skill 0: skill_decomposition_parser (Claude Skill)**
- 7 Core Actions
- 6 Rules
- 3 Missions
- 5 Execution Paths

**Skill 1: echo (MCP Tool)**
- 2 Core Actions
- 2 Rules
- 1 Mission
- 3 Execution Paths

**Skill 2: get_current_time (MCP Tool)**
- 3 Core Actions
- 2 Rules
- 1 Mission
- 3 Execution Paths

**Skill 3: get-sum (MCP Tool)**
- 2 Core Actions
- 4 Rules
- 1 Mission
- 5 Execution Paths

---

## JSON Schema 規範 v1.1.0

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://skill-parser.pingqlin.dev/schema/v1.1/skill-decomposition.schema.json",
  "title": "MCP Skill Decomposition Schema",
  "version": "1.1.0",
  
  "definitions": {
    "core_action": {
      "type": "object",
      "required": ["id", "name", "action_type", "deterministic"],
      "properties": {
        "id": { "type": "string", "pattern": "^ca_[0-9]{3}$" },
        "name": { "type": "string" },
        "action_type": {
          "enum": ["transform", "io_read", "io_write", "compute", "external_call", "state_change", "llm_inference"]
        },
        "immutable_elements": { "type": "array", "items": { "type": "string" } },
        "mutable_elements": { "type": "array", "items": { "type": "string" } },
        "deterministic": { "type": "boolean" }
      }
    },
    
    "rule": {
      "type": "object",
      "required": ["id", "name", "condition_type", "returns", "fail_consequence"],
      "properties": {
        "id": { "type": "string", "pattern": "^r_[0-9]{3}$" },
        "name": { "type": "string" },
        "condition_type": {
          "enum": ["validation", "existence_check", "type_check", "range_check", "permission_check", "state_check", "consistency_check", "threshold_check"]
        },
        "returns": { "enum": ["boolean", "classification", "enum_value", "score"] },
        "fail_consequence": { "enum": ["halt", "branch", "default_value", "error_throw", "retry", "escalate"] }
      }
    },
    
    "mission": {
      "type": "object",
      "required": ["id", "name", "goal", "composed_of", "output_type"],
      "properties": {
        "id": { "type": "string", "pattern": "^m_[0-9]{3}$" },
        "name": { "type": "string" },
        "goal": { "type": "string" },
        "composed_of": { "type": "array", "items": { "type": "string" } },
        "output_type": { "type": "string" }
      }
    }
  }
}
```

---

## Next Steps

1. Formalize the Schema and save it in the `schema/` directory
2. Save each Skill parsing result in the `parsed/` directory
3. Design LLM Prompt template to make parsing repeatable
4. Create visualization (flowchart/relationship diagram)

---

*Generated by Claude on 2026-01-23*

---

*This is a machine translation. For the original content, please refer to the file named 'conversation-2026-01-23_zh-tw.md'.*