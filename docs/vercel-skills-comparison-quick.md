# Quick Comparison: Skill-0 vs Vercel Labs Skills

## TL;DR

| Feature | Skill-0 | Vercel Skills |
|---------|---------|---------------|
| **What it does** | Parses skills into atomic components | Installs skills across 39+ agents |
| **Format** | Structured JSON (Schema 2.2.0) | Markdown + YAML frontmatter |
| **Search** | Semantic vector search | Keyword filtering |
| **Target** | Skill analysis & composition | Skill distribution |
| **Command** | `python -m src.vector_db.search` | `npx skills add` |
| **Governance** | ✅ Full (security, approval) | ❌ None |
| **Agent Support** | Claude, MCP | 39+ coding agents |
| **Use Case** | Deep analysis, enterprise | Quick install, developers |

## When to Use What?

### Use Skill-0 When:
- 🔬 Analyzing skill internal structure
- 🔍 Searching skills semantically (not just keywords)
- 🏢 Requiring governance and security scanning
- 🧩 Building composable skill systems
- 📊 Extracting patterns from existing skills
- 🔐 Enterprise compliance needs

### Use Vercel Skills When:
- ⚡ Quickly installing skills to coding agents
- 🌍 Working with multiple agents (Claude Code, Cursor, etc.)
- 👥 Sharing skills with team/community
- 📦 Managing skill versions via Git
- 🚀 Rapid prototyping with agent skills
- 💡 Simple skill creation (Markdown)

## Integration Vision

```
Vercel Skills (Distribution)
         ↓
  [Agent Runtime]
         ↓
   Skill-0 (Analysis)
         ↓
   Recommendations
```

**Future**: Skill-0 could provide analysis API to Vercel Skills CLI for intelligent recommendations and security checks during installation.

## Quick Links

- **Full Comparison**: [vercel-skills-comparison.md](vercel-skills-comparison.md) (中文) | [vercel-skills-comparison.en.md](vercel-skills-comparison.en.md) (English)
- **Skill-0**: https://github.com/pingqLIN/skill-0
- **Vercel Skills**: https://github.com/vercel-labs/skills
- **Skills Marketplace**: https://skills.sh
