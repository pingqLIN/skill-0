# Skill-0 分析工具

本目錄包含用於路由、分析、驗證與治理 Skills 結構的工具。

## 工具清單

### intent_router.py - Top-down 路由入口

依照目標與任務階段，先決定要走哪一條 Skill-0 工作路徑，再回推建議命令。

目前版本是 table-driven 的 operator starter，目的在於先把既有 search / parse / analyze / govern / compare / validate 路徑收斂成單一入口，而不是宣稱它已經是完整策略引擎。

```bash
# 從自由文字推斷目標
.venv/bin/python tools/intent_router.py --goal compare --phase triage --query "overlapping skills"

# 明確指定治理目標
.venv/bin/python tools/intent_router.py --goal govern --phase review

# 以 JSON 輸出 machine-readable handoff
.venv/bin/python tools/intent_router.py --goal discover --phase intake --query "document processing" --format json
```

**適用場景：**
- 先決定現在應該 search / ingest / analyze / govern / compare / validate 哪條路徑
- 避免從工具清單自下而上反推流程
- 作為 `skill-0` 的 top-down、intent-driven meta-router

### analyzer.py - 結構統計分析

分析已解析的 skills，產生統計報告。

```bash
# 基本用法
python tools/analyzer.py

# 指定輸入目錄和輸出路徑
python tools/analyzer.py -p parsed -o analysis/report.json

# 同時產生文字報告
python tools/analyzer.py -t
```

**輸出內容：**
- 元素總數統計 (action/rule/directive)
- Action 類型分布
- Directive 類型分布
- 各 Skill 摘要
- 常見執行序列模式

### pattern_extractor.py - 模式提取

從多個 skills 中歸納共通模式，建立模式庫。

```bash
# 基本用法
python tools/pattern_extractor.py

# 指定輸出路徑
python tools/pattern_extractor.py -o analysis/patterns.json
```

**提取的模式類型：**
- `action_combination` - Action 類型的常見組合
- `directive_usage` - Directive 類型的使用模式
- `structure` - 元素比例結構模式
- `keyword` - 描述文字的關鍵字模式

## 輸出檔案

分析結果儲存在 `analysis/` 目錄：

```
analysis/
├── report.json      # 結構統計報告
├── report.txt       # 文字版報告 (可選)
└── patterns.json    # 歸納出的模式庫
```

## 未來擴展

### 階段 2: 語義相似度分析
- 加入向量索引 (sqlite-vec)
- 語義搜尋相似元素
- 自動聚類

### 階段 3: LLM 輔助分析
- 模式歸納
- 新 Skill 生成建議
- 缺口分析
