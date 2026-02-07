# Skill-0 vs Vercel Labs Skills：專案比較分析

**作者**: pingqLIN  
**日期**: 2026-02-07  
**版本**: 1.0.0

## 執行摘要

本文檔對比分析兩個致力於 AI agent 技能生態系統的專案：
- **skill-0**: 技能分解與語義搜尋系統
- **Vercel Labs Skills**: 開放 agent 技能生態的 CLI 工具

兩個專案雖然都關注 AI agent 技能，但定位、架構和目標使用者群大不相同。Skill-0 專注於「技能內部結構的解析與分類」，而 Vercel Skills 則致力於「技能的分發與安裝管理」。

---

## 1. 專案定位對比

### Skill-0
**定位**: 技能分解分析器與語義搜尋引擎  
**核心價值**: 將 Claude Skills 和 MCP Tools 解析成結構化的原子組件，並提供語義搜尋能力

**關鍵特性**:
- 三元分類系統 (Action/Rule/Directive)
- 語義向量搜尋 (384-dim embeddings)
- JSON Schema 2.2.0 標準化格式
- 治理與安全掃描
- 分散式處理架構

**目標使用者**:
- AI 技能開發者（需深度了解技能內部結構）
- 研究人員（技能模式分析）
- 企業 IT（治理、合規）
- 框架開發者（需可組合的技能組件）

### Vercel Labs Skills
**定位**: Agent 技能生態系統的 CLI 安裝工具  
**核心價值**: 讓開發者輕鬆在 39+ 個 coding agent 間安裝、管理、更新技能

**關鍵特性**:
- NPM-like CLI 體驗 (`npx skills add`, `npx skills update`)
- 支援 39 個 coding agents（Claude Code、Cursor、Windsurf、OpenCode 等）
- GitHub/GitLab 快捷安裝
- 專案與全域作用域
- Symlink vs Copy 安裝模式
- 技能市場整合 (skills.sh)

**目標使用者**:
- Coding agent 使用者（快速擴充 agent 能力）
- 技能創作者（分享技能給社群）
- 團隊協作（統一技能集）
- IDE/Editor 開發者（整合技能生態）

---

## 2. 技術架構對比

| 維度 | Skill-0 | Vercel Labs Skills |
|------|---------|-------------------|
| **語言/框架** | Python 3.8+, FastAPI, React | Node.js, TypeScript, CLI |
| **主要用途** | 技能結構解析與分析 | 技能安裝與分發 |
| **資料格式** | JSON (自定義 Schema 2.2.0) | YAML Frontmatter + Markdown (SKILL.md) |
| **儲存方式** | SQLite-vec (向量資料庫) | 檔案系統 (symlink/copy) |
| **搜尋能力** | 語義向量搜尋 (sentence-transformers) | 關鍵字過濾 (fzf-style) |
| **分發方式** | 無（專注於解析） | GitHub, GitLab, local paths |
| **安裝方式** | pip install | npx skills add |
| **版本管理** | Schema 版本控制 | Git-based update checks |
| **擴展性** | Parser abstraction, Worker pool | Plugin manifest, 39+ agents |

### 架構圖示

#### Skill-0 架構
```
Input (Claude Skills, MCP Tools)
    ↓
[Parser Layer] → 三元分類 (Action/Rule/Directive)
    ↓
[Vector DB] → SQLite-vec (384-d embeddings)
    ↓
[API/Dashboard] → 搜尋、分析、治理
    ↓
Output (Structured JSON, Semantic Search, Patterns)
```

#### Vercel Skills 架構
```
Skill Repository (GitHub/GitLab/Local)
    ↓
[CLI Parser] → 掃描 SKILL.md 檔案
    ↓
[Installer] → Symlink or Copy to agent directories
    ↓
[Agent Loader] → 39+ agents (Claude Code, Cursor, etc.)
    ↓
Output (Skills active in coding agents)
```

---

## 3. 資料模型與格式對比

### Skill-0: 結構化 JSON

**Schema**: 完整 JSON Schema 2.2.0，嚴格型別定義

```json
{
  "meta": {
    "skill_id": "claude__pdf",
    "name": "pdf",
    "skill_layer": "claude_skill",
    "title": "Pdf Skill",
    "schema_version": "2.2.0"
  },
  "decomposition": {
    "actions": [
      {
        "id": "a_001",
        "name": "Read PDF",
        "action_type": "io_read",
        "deterministic": true,
        "immutable_elements": ["file_format: PDF"],
        "mutable_elements": ["file_path"],
        "side_effects": ["memory_allocation"]
      }
    ],
    "rules": [
      {
        "id": "r_001",
        "name": "Check File Exists",
        "condition_type": "existence_check",
        "condition": "PDF file exists at path",
        "output": "boolean"
      }
    ],
    "directives": [
      {
        "id": "d_001",
        "directive_type": "completion",
        "description": "All tables extracted and saved",
        "decomposable": true
      }
    ]
  }
}
```

**特點**:
- 原子級分解（8 種 action 類型，6 種 directive 類型）
- 明確的不可變/可變元素標記
- 副作用追蹤
- 可選的來源溯源 (provenance)

### Vercel Skills: YAML Frontmatter + Markdown

**格式**: 輕量 YAML + 自由格式 Markdown

```markdown
---
name: my-skill
description: What this skill does and when to use it
metadata:
  internal: false
---

# My Skill

Instructions for the agent to follow when this skill is activated.

## When to Use

Describe the scenarios where this skill should be used.

## Steps

1. First, do this
2. Then, do that
```

**特點**:
- 簡單易寫（僅需 name + description）
- 人類可讀的 Markdown 格式
- 無結構化約束（靈活但缺少標準）
- 可選的 internal 標記

---

## 4. 核心功能對比

| 功能 | Skill-0 | Vercel Skills |
|------|---------|---------------|
| **技能解析** | ✅ 深度結構化解析 (Actions/Rules/Directives) | ✅ 輕量 YAML 解析 (name/description) |
| **語義搜尋** | ✅ 向量語義搜尋 (75ms latency) | ⚠️ 關鍵字過濾 (`npx skills find`) |
| **技能安裝** | ❌ 無（僅解析分析） | ✅ 核心功能（39 agents） |
| **版本管理** | ⚠️ Schema 版本控制 | ✅ Git-based (`skills check/update`) |
| **技能發現** | ✅ Clustering、相似度搜尋 | ✅ 技能市場 (skills.sh) |
| **治理與安全** | ✅ 安全掃描、審批流程 | ❌ 無 |
| **分散式處理** | ✅ Worker pool (4x speedup) | ❌ 無 |
| **統計分析** | ✅ Analyzer、Pattern Extractor | ❌ 無 |
| **API** | ✅ REST API + Python SDK | ❌ 僅 CLI |
| **Dashboard** | ✅ React Dashboard | ❌ 無 |
| **Agent 整合** | ⚠️ Claude Skills、MCP Tools | ✅ 39+ coding agents |

---

## 5. 使用情境對比

### Scenario 1: 快速擴充 Coding Agent 能力
- **Vercel Skills 勝出**: 一行指令即可安裝
  ```bash
  npx skills add vercel-labs/agent-skills --skill frontend-design
  ```
- **Skill-0**: 需手動解析、轉換、整合

### Scenario 2: 分析技能組成與模式
- **Skill-0 勝出**: 深度結構化分析
  ```bash
  python -m src.vector_db.search search "PDF processing"
  python src/tools/pattern_extractor.py
  ```
- **Vercel Skills**: 僅能瀏覽原始 Markdown

### Scenario 3: 企業級治理與合規
- **Skill-0 勝出**: 內建安全掃描與審批流程
- **Vercel Skills**: 無治理功能

### Scenario 4: 跨 Agent 統一技能管理
- **Vercel Skills 勝出**: 支援 39+ agents
- **Skill-0**: 專注於 Claude/MCP 生態

### Scenario 5: 技能重組與自動化生成
- **Skill-0 勝出**: Pattern extraction → Template generation
- **Vercel Skills**: 需手動撰寫 SKILL.md

---

## 6. 生態系統整合對比

### Skill-0 生態
```
┌──────────────────┐
│ Claude Skills    │
│ MCP Tools        │
└────────┬─────────┘
         │ Parse
         ↓
┌──────────────────┐
│    Skill-0       │
│ (Decomposition)  │
└────────┬─────────┘
         │
         ├→ Vector Search
         ├→ Pattern Analysis
         ├→ Security Scan
         └→ Governance
```

### Vercel Skills 生態
```
┌──────────────────┐
│  GitHub/GitLab   │
│  Local Repos     │
└────────┬─────────┘
         │ Install
         ↓
┌──────────────────┐
│  Vercel Skills   │
│     (CLI)        │
└────────┬─────────┘
         │
         ├→ Claude Code
         ├→ Cursor
         ├→ Windsurf
         ├→ OpenCode
         ├→ Cline
         ├→ ... (39+ agents)
         └→ skills.sh marketplace
```

---

## 7. 資料統計對比

### Skill-0
- **32 個已解析技能**
- 266 個 Actions
- 84 個 Rules
- 120 個 Directives
- 資料庫大小：1.8MB (SQLite-vec)
- 索引時間：0.88s
- 搜尋延遲：~75ms

### Vercel Skills
- **39 個支援的 agents**
- 技能數量：未公開（依賴社群貢獻）
- 技能市場：skills.sh
- 安裝時間：秒級（Git clone + symlink）
- MCP 生態：4,509 個 repositories (根據 Skill-0 的 GitHub 搜尋報告)

---

## 8. 優劣勢分析

### Skill-0

**優勢** ✅:
1. **深度結構化**: 三元分類提供原子級分解
2. **語義搜尋**: 向量搜尋超越關鍵字匹配
3. **分析能力**: Pattern extraction、clustering、統計分析
4. **治理完整**: 安全掃描、審批流程、審計追蹤
5. **可擴展**: Parser abstraction、Worker pool、REST API
6. **Provenance**: 追蹤技能來源與版本

**劣勢** ❌:
1. **學習曲線高**: 需理解三元分類系統
2. **生態整合有限**: 主要針對 Claude/MCP
3. **無分發機制**: 不提供安裝/部署功能
4. **手動解析**: 需人工或 LLM 輔助分解
5. **社群規模小**: 32 個技能 vs 社群龐大的 Vercel 生態

### Vercel Skills

**優勢** ✅:
1. **使用簡單**: NPM-like CLI，學習成本低
2. **廣泛支援**: 39+ coding agents
3. **快速部署**: 一行指令安裝技能
4. **生態成熟**: 連接 skills.sh marketplace
5. **格式靈活**: Markdown 易於撰寫
6. **社群驅動**: 開放生態，易於貢獻

**劣勢** ❌:
1. **無結構化**: 技能內容無標準格式
2. **無語義搜尋**: 僅關鍵字過濾
3. **無治理**: 缺少安全掃描與合規機制
4. **無分析工具**: 無法分析技能模式
5. **版本管理簡陋**: 僅依賴 Git
6. **無 API**: 僅 CLI，無程式化存取

---

## 9. 互補性與整合可能性

兩個專案實際上具有**高度互補性**，而非競爭關係：

### 可能的整合架構

```
┌─────────────────────────────────────────┐
│         Vercel Skills CLI               │
│  (技能分發與安裝 - 39+ agents)           │
└──────────────┬──────────────────────────┘
               │ Install
               ↓
┌─────────────────────────────────────────┐
│       Agent Runtime Environment         │
│  (Claude Code, Cursor, Windsurf, ...)   │
└──────────────┬──────────────────────────┘
               │ Execute Skill
               ↓
┌─────────────────────────────────────────┐
│           Skill-0 Layer                 │
│  (深度解析、語義搜尋、治理)              │
└──────────────┬──────────────────────────┘
               │
               ├→ 語義搜尋推薦
               ├→ 技能組合建議
               ├→ 安全性檢查
               └→ 效能分析
```

### 具體整合方案

#### 方案 1: Skill-0 作為後端分析引擎
```bash
# Vercel Skills 安裝時自動送交 Skill-0 分析
npx skills add repo/skill --analyze-with-skill0

# Skill-0 回傳：
# - 技能複雜度評分
# - 安全性掃描結果
# - 相似技能推薦
# - 組合建議
```

#### 方案 2: SKILL.md ↔ Skill-0 JSON 雙向轉換
```bash
# Markdown → Skill-0 JSON
python src/tools/helper.py convert SKILL.md output.json

# Skill-0 JSON → Markdown (for Vercel Skills)
python src/tools/helper.py export output.json SKILL.md
```

#### 方案 3: Skill-0 提供推薦 API 給 Vercel CLI
```typescript
// In Vercel Skills CLI
import { Skill0Client } from '@skill-0/client'

const client = new Skill0Client('http://skill0-api:8000')

// 安裝前檢查
const recommendations = await client.search({
  query: "PDF processing",
  agent: "claude-code"
})

// 推薦相似或互補技能
console.log("You might also like:", recommendations)
```

---

## 10. 建議與結論

### 給 Skill-0 的建議
1. **增加 SKILL.md 支援**: 實作 `SKILL.md → Skill-0 JSON` 轉換器
2. **提供分發機制**: 參考 Vercel Skills 的 CLI 體驗
3. **擴展 Agent 支援**: 不只 Claude/MCP，支援更多 coding agents
4. **簡化使用**: 提供簡化版 API 給一般使用者
5. **社群建設**: 建立技能市場與貢獻指南

### 給 Vercel Skills 的建議
1. **增加結構化選項**: 支援可選的結構化 metadata (如 Skill-0 schema)
2. **語義搜尋**: 整合向量搜尋提升技能發現能力
3. **治理功能**: 增加安全掃描與審批流程（企業用戶需求）
4. **分析工具**: 提供技能使用統計與效能分析
5. **API 層**: 提供 REST API 供 CI/CD 與自動化工具整合

### 結論

| 面向 | Skill-0 | Vercel Skills | 推薦 |
|------|---------|---------------|------|
| **技能創作者** | 深度分析工具 | 快速分發 | 兩者結合：Skill-0 分析 + Vercel 分發 |
| **開發者** | 複雜組合場景 | 日常技能擴充 | 優先 Vercel Skills |
| **企業** | 治理與合規 | 團隊協作 | Skill-0 治理 + Vercel 分發 |
| **研究者** | 技能模式研究 | 生態觀察 | Skill-0 |
| **Agent 開發者** | 技能引擎設計 | 技能整合 | 兩者結合 |

**終極願景**: Skill-0 與 Vercel Skills 可形成完整的技能生態閉環：
- Vercel Skills 負責「分發與安裝」（寬度）
- Skill-0 負責「分解與分析」（深度）
- 兩者整合可實現「智慧技能推薦」、「自動化組合」、「企業級治理」

---

## 11. 參考資料

### Skill-0
- **GitHub**: https://github.com/pingqLIN/skill-0
- **Schema**: `schema/skill-decomposition.schema.json` v2.2.0
- **Documentation**: `README.md`, `CLAUDE.md`, `SKILL.md`
- **Statistics**: 32 skills, 266 actions, 84 rules, 120 directives

### Vercel Labs Skills
- **GitHub**: https://github.com/vercel-labs/skills
- **Website**: https://skills.sh
- **Specification**: https://agentskills.io
- **Statistics**: 39 supported agents, community-driven skill library

### 相關專案
- **Agent-Lightning** (Microsoft): https://github.com/microsoft/agent-lightning
- **Awesome MCP Servers**: https://github.com/punkpeye/awesome-mcp-servers (79,994 ⭐)
- **Claude Code**: https://code.claude.com/docs/en/skills
- **Cursor**: https://cursor.com/docs/context/skills

---

**文件版本**: 1.0.0  
**最後更新**: 2026-02-07  
**作者**: pingqLIN  
**License**: MIT
