# Skill-0: Skill Decomposition Parser

> 一個解析 Claude Skills 與 MCP Tools 內部結構的三元分類系統

## Overview 概述

Skill-0 是一個分類系統，用於將 AI/Chatbot Skills（特別是 Claude Skills 和 MCP Tools）解析為結構化的組件。

## Ternary Classification System 三元分類法

將 Skill 中不可變的部分（或修改後會改變行為的部分）組織並定義為三個類別：

```
┌─────────────────────────────────────────────────────────────┐
│                    Skill 三元分類法                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────────┐   │
│  │   Action    │   │    Rule     │   │   Directive     │   │
│  │   (動作)    │   │   (規則)    │   │    (指示)       │   │
│  ├─────────────┤   ├─────────────┤   ├─────────────────┤   │
│  │ 原子操作    │   │ 原子判斷    │   │ 描述性語句      │   │
│  │ 不可分解    │   │ 不可分解    │   │ 可分解但暫停    │   │
│  │             │   │             │   │                 │   │
│  │ 回答：      │   │ 回答：      │   │ 回答：          │   │
│  │ 「做什麼」  │   │「怎麼判斷」 │   │「描述什麼狀態」 │   │
│  └─────────────┘   └─────────────┘   └─────────────────┘   │
│        │                 │                    │             │
│        ▼                 ▼                    ▼             │
│   🔒 終點            🔒 終點           ⏸️ 暫停點           │
│                                        (可深入解析)         │
└─────────────────────────────────────────────────────────────┘
```

| Category | Definition | Characteristics |
|----------|------------|-----------------|
| **Action** (動作) | 原子操作：不可再分解的基礎操作 | 確定性結果、無條件分支、原子操作 |
| **Rule** (規則) | 原子判斷：純粹的條件判斷/分類 | 回傳布林值/分類結果、條件評估 |
| **Directive** (指示) | 描述性語句：可分解但在此層次選擇不分解 | 包含完成狀態、知識、原則、限制等 |

### Directive Types 指示類型

| Type | Description | Example |
|------|-------------|---------|
| `completion` | 完成狀態描述 | 「表格已全部提取」 |
| `knowledge` | 領域知識 | 「PDF 格式規範」 |
| `principle` | 指導原則 | 「優化 Context Window」 |
| `constraint` | 限制條件 | 「最大 25,000 tokens」 |
| `preference` | 偏好設定 | 「使用者偏好 JSON 格式」 |
| `strategy` | 策略方針 | 「錯誤時重試三次」 |

### ID Format ID 格式

| Element | Pattern | Example |
|---------|---------|---------|
| Action | `a_XXX` | `a_001`, `a_002` |
| Rule | `r_XXX` | `r_001`, `r_002` |
| Directive | `d_XXX` | `d_001`, `d_002` |

## Project Structure 專案結構

```
skill-0/
├── README.md
├── schema/
│   └── skill-decomposition.schema.json    # JSON Schema v2.0
├── parsed/
│   └── anthropic-pdf-skill.json           # PDF Skill 解析範例
└── docs/
    └── conversation-2026-01-23.md         # 原始對話紀錄
```

## Quick Example 快速範例

```json
{
  "decomposition": {
    "actions": [
      {
        "id": "a_001",
        "name": "Read PDF",
        "action_type": "io_read",
        "deterministic": true
      }
    ],
    "rules": [
      {
        "id": "r_001",
        "name": "Check File Exists",
        "condition_type": "existence_check",
        "returns": "boolean"
      }
    ],
    "directives": [
      {
        "id": "d_001",
        "name": "PDF Processing Complete",
        "directive_type": "completion",
        "description": "All tables extracted and saved to Excel",
        "decomposable": true
      }
    ]
  }
}
```

## Version 版本

- Schema Version: 2.0.0
- Created: 2026-01-23
- Updated: 2026-01-26
- Author: Project Maintainer

## Changelog 更新紀錄

### v2.0.0 (2026-01-26)
- **Breaking Change**: 重新定義三元分類
  - `core_action` → `action` (ID: `ca_XXX` → `a_XXX`)
  - `mission` → `directive` (ID: `m_XXX` → `d_XXX`)
- 新增 `directive_type` 支援：completion, knowledge, principle, constraint, preference, strategy
- 新增 `decomposable` 和 `decomposition_hint` 欄位
- 新增 `action_type`: `await_input`
- Schema 結構優化

### v1.1.0 (2026-01-23)
- 初始版本

## License 授權

MIT
