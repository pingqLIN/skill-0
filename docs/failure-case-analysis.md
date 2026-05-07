# Skill-0 Failure Case Analysis

更新日期：2026-05-07

## 目的

本文件定義 Skill-0 失敗案例分析流程。原則是先分析失敗案例，再決定是否擴張 schema 或調整 parser，避免 scope creep。

## 失敗分類

| 類別 | 說明 | 例子 | 後續處置 |
|---|---|---|---|
| Classification ambiguity | `Action / Rule / Directive` 邊界不穩 | `must create` 被錯歸類 | 加人工標註與 regression fixture |
| Directive overload | Directive 變成兜底類別 | principle、strategy、constraint 混在同欄位 | 先分群，必要時提出 schema change |
| Workflow loss | 工作流結構被拆成清單後失去順序或條件 | review -> test -> fix loop 缺少循環關係 | 補 workflow relation 或 warning |
| Reference loss | supporting files、references、templates 未納入 | Skill 依賴外部 policy doc | 建立 dependency summary |
| Delegation loss | subagent 或 forked context 未表達 | `agent:` 或 `context: fork` | 產出 delegation node 或風險提醒 |
| Search miss | relevant Skill 未被搜尋找回 | governance 查詢找不到安全 Skill | 回填 benchmark query |
| Governance blind spot | regex scan 無法捕捉語義風險 | 間接 prompt injection | 轉入 governance hardening backlog |

## 抽樣策略

第一輪抽樣至少包含：

1. 5 個工具型 Skill。
2. 5 個指南型 Skill。
3. 5 個工作流型 Skill。
4. 3 個安全或治理型 Skill。
5. 2 個含 references/scripts/templates 或 delegation 訊號的複雜 Skill。

每個案例記錄：

- Skill ID 或來源路徑。
- 原文中重要行為。
- 目前 parsed output 的捕捉狀態。
- 缺失類別。
- 使用者可感知的風險。
- 建議修復方向。
- 是否需要 schema change。

## 分析表格式

| Skill | 類型 | 失敗類別 | 目前輸出 | 期望行為 | 修復方向 | 測試 |
|---|---|---|---|---|---|---|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD |

## Schema Change Gate

提出 schema change 前必須同時滿足：

1. 至少 3 個不同來源案例出現同類缺失。
2. 既有欄位無法以 normalization 或 warning 合理表達。
3. 有 fixture 可驗證新欄位或新規則。
4. 有 dashboard/API consumption plan，避免只新增資料但無使用路徑。

## Parser Change Gate

調整 parser 前必須說明：

- 要修的是 keyword rule、context window、frontmatter extraction，或 supporting file analysis。
- 是否會影響已驗證的 `parsed/` corpus。
- 是否需要跑 `tools/normalize_parsed_skills.py`。
- 是否需要更新 `schema/skill-decomposition.schema.json`。

## 驗收標準

- 每個高風險失敗類別至少有一個 fixture 或人工標註案例。
- 失敗案例能回填到 benchmark query 或 parser regression。
- 文件中不把「框架無法表達」偽裝成「Skill 不重要」。

## 驗證入口

```bash
git diff --check
.venv/bin/python tools/check_doc_status_markers.py
```

後續新增 fixtures 後，補上 parser regression 測試命令。
