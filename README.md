# Skill-0: MCP Skill Decomposition Parser

> A general classification program for parsing Claude Skills and MCP Tools into structured components.

## 概述

Skill-0 是一個用於解析 AI/Chatbot Skills（特別是 Claude Skills 和 MCP Tools）內部成分結構的分類系統。

## 三元分類體系

將 Skill 內部不可變動/變動將造成效果改變的部分，整理定義分類為：

| 分類 | 定義 | 特徵 |
|------|------|------|
| **Core Action** | 核心動作：不具有判斷價值系統的基礎操作 | 執行結果確定、無條件分支、原子操作 |
| **Rules** | 純粹的判斷：不帶動作只討論分類 | 回傳布林/分類結果、條件評估 |
| **Mission** | 任務/作品：最終朝向的目標方向 | 組合多個 Action + Rules、有明確產出 |

## 專案結構

```
skill-0/
├── README.md
├── schema/
│   └── skill-decomposition.schema.json    # JSON Schema 規範
├── parsed/
│   ├── skill-0-parser.json                # 解析器自我解析
│   ├── mcp-echo.json                      # MCP echo tool 解析
│   ├── mcp-get-current-time.json          # MCP time tool 解析
│   └── mcp-get-sum.json                   # MCP sum tool 解析
└── docs/
    └── conversation-2026-01-23.md         # 原始對話記錄
```

## 版本

- Schema Version: 1.1.0
- Created: 2026-01-23
- Author: pingqLIN

## License

MIT
