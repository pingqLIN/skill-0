# Skill-0 vs Claude Code Simplifier

以下為精簡對照，聚焦於定位、流程、資料模型，以及如何互補搭配。

## 定位

- **Skill-0**: 解析技能/工具指令並建立語意索引的系統，將技能定義轉成結構化 JSON 供分析與搜尋。
- **Claude Code Simplifier**: 針對專案程式碼（含近期變更）進行分析並提出簡化修改建議的外掛。

## 流程比較

| 面向 | Skill-0 | Claude Code Simplifier |
|------|---------|------------------------|
| **輸入** | 技能描述、工具指令 | 專案程式碼與近期變更 |
| **核心流程** | 解析 -> 分類 -> 索引 -> 搜尋 | 分析 -> 簡化 -> 輸出修改 |
| **輸出** | 結構化 JSON、語意搜尋結果 | 簡化後的程式碼修改 |
| **主要目標** | 知識抽取與可搜尋性 | 程式碼可讀性與簡化 |

## 資料模型

- **Skill-0**: 以 Actions / Rules / Directives 為主的 JSON 結構（可選 provenance）。
- **Claude Code Simplifier**: 以程式碼修改建議或 diff 為主（未宣告共用 schema）。

## 優缺點

**Skill-0**
- 優點: 結構化資料模型明確、可重複索引、適合治理與檢索。
- 缺點: 需要技能定義作為輸入，並非直接改寫程式碼的工具。

**Claude Code Simplifier**
- 優點: 直接提升程式碼可讀性與複雜度，貼近實作場景。
- 缺點: 以程式碼改寫為核心，無法做技能/指令的結構化索引。

## 互補與整合建議

- 用 **Skill-0** 管理與搜尋指令集（skills、tool prompts、政策）。
- 用 **Claude Code Simplifier** 對目標專案進行簡化修正。
- 建議流程: 先用 Skill-0 彙整最佳實務，再以這些原則作為 Code Simplifier 的簡化目標。

> [!WARNING]
> 此比較基於公開外掛頁面與 Skill-0 專案內容，外掛行為可能隨時間變更。

## 來源

- Claude 外掛目錄: https://claude.com/plugins
- Claude Code Simplifier 外掛頁面: https://claude.com/plugins/code-simplifier
