# Skill-0 vs Taste-Skill

比較兩個 AI 技能定義專案：**Skill-0**（結構化技能拆解與語意搜尋）與 **Taste-Skill**（高品質前端設計指令）。本文件評估相似性、差異、可借鑑優點，以及市場競爭合作可能。

## 定位

- **Skill-0**: 三元分類系統，將 AI 技能/工具指令解析為結構化 JSON（Actions / Rules / Directives），存入 SQLite 搭配向量嵌入，提供語意搜尋、群集分析、治理流程與儀表板 API。
- **Taste-Skill**: 單檔（`SKILL.md`）提示工程系統，指導 AI 程式碼助手（Cursor、Claude Code、Codex 等）生成高端、現代的前端 UI 程式碼，透過設計規則、反模式清單與可調參數來約束輸出品質。

## 流程比較

| 面向 | Skill-0 | Taste-Skill |
|------|---------|-------------|
| **輸入** | 技能/工具定義（Markdown/JSON） | 單一 `SKILL.md` 檔案放入專案根目錄 |
| **核心流程** | 解析 → 分類 → 索引 → 搜尋 | AI 讀取規則 → 生成受約束的前端程式碼 |
| **輸出** | 結構化 JSON、語意搜尋結果、群集分析 | 高品質前端程式碼（React/Next.js + Tailwind） |
| **主要目標** | 知識抽取、發現與技能定義治理 | 消除 AI 生成的泛用 UI（「slop」），強制執行高端設計品味 |
| **使用方式** | CLI、REST API、儀表板 | 直接在 AI 助手提示中引用 `@SKILL.md` |

## 相似之處

1. **皆為「技能」系統**: 兩者都定義結構化指令來引導 AI 行為 — Skill-0 用於分析/索引，Taste-Skill 用於程式碼生成品質控制。
2. **規則導向架構**: 兩者依賴明確規則。Skill-0 使用正式的 `Rules` 分類（condition_type、output），Taste-Skill 使用編號設計規則（排版、配色、佈局、互動）。
3. **反模式意識**: 兩者都定義 AI 不該做的事。Skill-0 記錄副作用與失敗後果，Taste-Skill 有第 7 節（「100 AI Tells」）列出禁止模式。
4. **Markdown 優先**: 兩者都以 Markdown 作為技能定義的主要撰寫格式。
5. **目標對象為 AI 程式碼助手**: 兩者都旨在改善 AI 工具的運作方式 — Skill-0 透過結構化知識，Taste-Skill 透過約束輸出品質。

## 差異

| 面向 | Skill-0 | Taste-Skill |
|------|---------|-------------|
| **範疇** | 通用型技能拆解（任何領域） | 僅前端 UI/UX（React/Next.js 生態系） |
| **複雜度** | 全端系統：解析器、向量資料庫、API、儀表板、Schema | 單檔，零基礎建設 |
| **Schema** | 正式 JSON Schema v2.2.0 含版本控制 | 無正式 Schema；以編號章節結構化的 Markdown |
| **可搜尋性** | 向量嵌入語意搜尋（384 維） | 不可搜尋；AI 在提示時直接讀取 |
| **可配置性** | Schema 擴展、自訂技能層級 | 3 個數值旋鈕（DESIGN_VARIANCE、MOTION_INTENSITY、VISUAL_DENSITY） |
| **治理機制** | 審核流程、稽核日誌、安全掃描 | 社群回饋（GitHub Issues/PRs） |
| **技術架構** | Python、FastAPI、SQLite-vec、sentence-transformers | 無（純 Markdown 指令） |
| **拆解方式** | 三元：Actions / Rules / Directives | 扁平章節：架構、規則、反模式、效能、參考 |
| **目標受眾** | 平台建構者、AI 研究者、技能策展人 | 使用 AI 程式碼助手的前端開發者 |
| **技能數量** | 32+ 已解析、171 已匯入 | 1 個單體技能檔案 |

## 可借鑑的優點

### 1. 參數化控制旋鈕
Taste-Skill 的 3 個可配置旋鈕（`DESIGN_VARIANCE`、`MOTION_INTENSITY`、`VISUAL_DENSITY`）以 1-10 刻度提供優雅的調整體驗。Skill-0 可借鑑類似概念：
- 在 Schema 中加入可選的 `parameters` 或 `control_dials` 欄位，讓技能作者定義可調數值範圍以修改執行行為。
- 這能讓技能更靈活且更易用，同時不改變核心三元分類。

### 2. 明確的反模式目錄
Taste-Skill 的「100 AI Tells」（第 7 節）是全面的禁止模式目錄，附帶具體替代方案。Skill-0 的 Rules 支援 `failure_consequence`，但缺乏專門的負面模式目錄。在技能定義中加入 `anti_patterns` 欄位將強化品質約束。

### 3. 零設定發布模型
Taste-Skill 的「下載一個檔案並引用它」方式極具親和力。Skill-0 可提供輕量匯出模式 — 從已解析的 JSON 生成獨立的 `SKILL.md` 檔案 — 讓使用者無需運行完整基礎設施即可使用技能。

### 4. 效能護欄作為一級規則
Taste-Skill 的第 5 節專門定義效能護欄（DOM 成本、硬體加速、z-index 約束）。Skill-0 可將效能約束正式化為規則子型別，使其在技能定義中可搜尋且可強制執行。

### 5. 創意靈感庫
Taste-Skill 的第 8 節（「Creative Arsenal」）提供分類化的 UI 模式庫（導航、佈局、卡片、捲動、排版、微互動）。這種「模式庫」概念可作為 Skill-0 的新 directive 類型或連結資源，在技能定義旁提供策展過的實作參考。

## 市場角色分析

### Skill-0：基礎設施層
- **角色**: AI 技能管理的後端知識基礎設施
- **價值**: 技能定義的結構化、可搜尋性、治理與生命週期管理
- **市場**: 企業 AI 平台、工具註冊中心、技能市集、AI 治理團隊

### Taste-Skill：創意約束層
- **角色**: AI 生成程式碼的前端品質強制執行
- **價值**: 零基礎設施即時提升 AI 輸出品質
- **市場**: 個人開發者、重視設計的團隊、快速原型開發（「vibe coding」）

### 競爭分析

直接競爭**極小**，因為兩者運作在不同層級：
- Skill-0 是**元系統**（管理和索引技能）；Taste-Skill 是**具體技能**（指導特定領域的 AI 行為）。
- Taste-Skill 實際上可以被 Skill-0 解析並索引為資料庫中眾多技能之一。

### 合作機會

1. **Taste-Skill 作為 Skill-0 條目**: 將 `taste-skill/SKILL.md` 解析為 Skill-0 的三元格式。這將建立前端設計技能的結構化、可搜尋表示，同時展示 Skill-0 對真實世界熱門技能定義的解析能力。

2. **Skill-0 作為發布平台**: Skill-0 的語意搜尋與 API 可作為 Taste-Skill 等技能的發現層，讓開發者搜尋和下載特定領域的指令檔案。

3. **參數化技能匯出**: 結合 Skill-0 的結構化 Schema 與 Taste-Skill 的旋鈕概念，生成可配置的 `SKILL.md` 檔案供 AI 助手直接使用 — 橋接結構化治理與零設定使用之間的鴻溝。

4. **品質指標管線**: Skill-0 的分析工具可評估和評分 Taste-Skill 等技能檔案的結構完整性、規則覆蓋率與反模式文件 — 為潛在的技能市集提供品質指標。

## 總結矩陣

| 面向 | Skill-0 | Taste-Skill | 協同潛力 |
|------|---------|-------------|----------|
| 架構 | 全端平台 | 單檔 | Skill-0 索引 Taste-Skill |
| 靈活性 | 任何領域 | 僅前端 | 互補而非競爭 |
| 使用體驗 | CLI/API/儀表板 | 複製檔案 + 提示 | 匯出結構化技能為 SKILL.md |
| 治理 | 內建工作流程 | 社群驅動 | Skill-0 為技能生態系提供治理 |
| 導入門檻 | 需要設定 | 零設定 | Skill-0 提供輕量匯出模式 |
| 可配置性 | Schema 擴展 | 3 個旋鈕（1-10） | 將旋鈕概念加入 Skill-0 Schema |

> [!WARNING]
> 此比較基於 Skill-0 儲存庫（commit 9d9de81）與 Taste-Skill 儲存庫（https://github.com/Leonxlnx/taste-skill）截至 2026-02 的內容。專案功能與定位可能隨時間變更。

## 來源

- Skill-0 儲存庫: https://github.com/pingqLIN/skill-0
- Taste-Skill 儲存庫: https://github.com/Leonxlnx/taste-skill
- Taste-Skill SKILL.md: https://github.com/Leonxlnx/taste-skill/blob/main/SKILL.md
