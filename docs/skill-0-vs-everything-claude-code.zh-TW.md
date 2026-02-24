# Skill-0 vs Everything Claude Code

比較兩個 AI 技能/指令生態系：**Skill-0**（結構化技能拆解與語意搜尋）與 **Everything Claude Code**（生產就緒的 Claude Code 外掛，含代理人、技能與指令）。本文件評估相似性、差異、Skill-0 能為 Everything Claude Code 帶來的具體幫助，以及潛在的合作路徑。

## 定位

- **Skill-0**: 三元分類系統，將 AI 技能/工具指令解析為結構化 JSON（Actions / Rules / Directives），存入 SQLite 搭配向量嵌入，提供語意搜尋、群集分析、治理流程與儀表板 API。
- **Everything Claude Code（ECC）**: Anthropic Hackathon 獲獎的 Claude Code 外掛，提供 13 個專用代理人、44+ 個技能、32 個指令，歷經 10+ 個月的日常生產環境使用精練而成。技能以 Markdown 檔案形式儲存於各自目錄，由 Claude Code 在提示時直接讀取。

## 流程比較

| 面向 | Skill-0 | Everything Claude Code |
|------|---------|------------------------|
| **輸入** | 技能/工具定義（Markdown/JSON） | Claude Code 提示中引用 `skills/<name>/` |
| **核心流程** | 解析 → 分類 → 索引 → 搜尋 | AI 讀取技能 Markdown → 執行受約束的工作流程 |
| **輸出** | 結構化 JSON、語意搜尋結果、技能圖 | 程式碼變更、測試執行、規劃文件 |
| **主要目標** | 知識抽取、發現與技能定義治理 | 以經過驗證的 AI 工作流程加速真實世界軟體開發 |
| **使用方式** | CLI、REST API、儀表板 | 斜線指令（`/tdd`、`/plan`、`/code-review`）與技能引用 |
| **技能數量** | 32 已解析 + 171 已匯入 | 44+ 個技能分散於 30+ 個目錄 |
| **發布方式** | SQLite + 向量儲存、REST API | Claude Code 外掛市集（`/plugin install`） |

## 相似之處

1. **皆為技能生態系**: 兩者都定義結構化指令來引導 AI 行為 — Skill-0 用於分析/索引，ECC 用於執行生產軟體工作流程。
2. **規則導向架構**: 兩者依賴明確規則。Skill-0 使用正式的 `Rules` 分類（condition_type、output）。ECC 技能內嵌驗證規則、TDD 紅-綠-重構關卡，以及安全性檢查清單。
3. **反模式意識**: 兩者都記錄 AI 不應執行的操作。Skill-0 在規則中記錄 `failure_consequence`，ECC 技能包含明確的「禁止」章節（如：禁止過早最佳化、禁止跳過測試）。
4. **持續學習**: 兩者都支援知識演進。Skill-0 支援版本化 Schema 與技能更新。ECC 有專屬的 `continuous-learning` 技能，可從程式碼 session 自動抽取模式。
5. **多語言支援**: 兩者都能適應多種程式語言。Skill-0 的 Schema 與語言無關。ECC 有各語言專屬技能目錄（TypeScript、Python、Go、Java、C++、Swift、Django、Spring Boot）。
6. **Markdown 優先撰寫**: 兩者都以 Markdown 作為技能定義的主要格式。

## 差異

| 面向 | Skill-0 | Everything Claude Code |
|------|---------|------------------------|
| **範疇** | 通用型技能拆解（任何領域） | 軟體開發工作流程（程式碼、測試、審查、部署） |
| **結構** | 正式 JSON Schema v2.2.0，三元分類 | 扁平 Markdown 目錄；無共用 Schema |
| **可搜尋性** | 向量嵌入語意搜尋（384 維） | 不可搜尋；AI 在提示時直接讀取檔案 |
| **技能關係** | 透過 `skill_links` 建立技能間連結（Schema v2.3.0） | 目錄命名慣例隱含的關係 |
| **治理機制** | 審核流程、稽核日誌、安全掃描 | GitHub 社群 PR；基於 Changelog 的發版 |
| **重複偵測** | 跨索引技能的內建相似度搜尋 | 人工審查；語言變體間可能存在重疊 |
| **自省能力** | 完整圖/MOC 檢視、群集分析 | 無程式化自省；人工維護的 README |
| **技術架構** | Python、FastAPI、SQLite-vec、sentence-transformers | Node.js hooks、TypeScript 配置、Bash 腳本 |
| **部署方式** | 自架 API + 儀表板 | Claude Code / OpenCode 外掛（零基礎設施） |
| **目標受眾** | 平台建構者、AI 研究者、技能策展人 | 日常使用 Claude Code 的個人開發者與團隊 |
| **技能深度** | 原子化 Actions / Rules / Directives 拆解 | 完整工作流程描述，含範例與代理人委派 |
| **版本管理** | Schema 版本化（2.1 → 2.2 → 2.3） | 語意版本化發版（v1.2 → v1.3 → v1.4） |

## Skill-0 能如何幫助 Everything Claude Code

### 1. 語意技能發現
ECC 的 44+ 個技能分散於 30+ 個目錄，僅憑名稱難以導覽。Skill-0 的向量搜尋讓貢獻者與使用者可透過語意尋找相關技能：
- 查詢 `"資料庫最佳化"` → 找到 `postgres-patterns`、`clickhouse-io`、`jpa-patterns`、`database-migrations`
- 查詢 `"測試驅動開發"` → 找到 `tdd-workflow`、`golang-testing`、`django-tdd`、`springboot-tdd`、`python-testing`
- 在決定為新語言變體使用或擴展哪個技能時，此功能尤其有價值。

### 2. 跨語言重複與模式偵測
ECC 為多個語言（TypeScript、Python、Go、Java、Django、Spring Boot）提供幾乎相同的 TDD、安全審查與驗證循環技能。Skill-0 的相似度搜尋可：
- 浮現餘弦相似度 >0.9 的技能，標記為可整合或建立共用基礎模板的候選。
- 識別每個語言變體在通用模式之上新增的獨特規則，讓維護工作更輕鬆。

### 3. `continuous-learning` 技能的結構化拆解
ECC 的 `continuous-learning` 與 `continuous-learning-v2` 技能描述了複雜的多步驟 AI 學習循環。將這些技能解析為 Skill-0 的三元格式可：
- 將確切的 Actions（抽取模式、儲存本能、評分信心）、Rules（門檻檢查：信心 ≥ 0.7）與 Directives（目標：自動演進程式碼模式）揭露為明確、可檢視的元件。
- 驗證學習循環的連接是否正確，且無遺漏步驟或衝突規則。

### 4. 技能品質評分與治理
ECC 透過社群 PR 成長。Skill-0 的分析工具可對每個提交的技能進行評分：
- **結構完整性**: 技能是否定義了清晰的動作、失敗條件與預期結果？
- **規則覆蓋率**: 是否記錄了邊界案例與錯誤狀態？
- **反模式文件**: 技能是否明確說明應避免的事項？
- 在合併前為技能貢獻提供客觀的品質關卡。

### 5. 技能間依賴關係圖
ECC 技能之間存在隱含依賴（如：`tdd-workflow` 預設 `coding-standards` 存在；`eval-harness` 依賴 `verification-loop`）。Skill-0 的 `skill_links` 功能可：
- 明確映射這些關係（`depends_on`、`extends`、`composes_with`）
- 生成自動渲染的依賴關係圖（MOC 檢視），顯示技能如何組合成完整工作流程
- 當基礎技能的修改會破壞依賴技能時，向維護者發出警報

### 6. 技能匯出為結構化文件
Skill-0 可生成所有 ECC 技能的機器可讀 JSON 目錄，實現：
- 自動生成 API 文件與整合指南
- LLM 輔助上手引導：新使用者查詢 `"哪個技能處理 CI/CD 回滾？"` 並得到精確答案
- 整合外部工具（Notion、Confluence、內部 Wiki），這些工具可消費結構化 JSON

### 7. 本能知識庫索引
ECC 的 `continuous-learning-v2` 引入了「本能（instinct）」系統，AI 從 session 中抽取模式為可重複使用的知識。Skill-0 的向量儲存可：
- 將抽取的本能與正式技能一同索引，實現語意檢索
- 偵測新抽取的本能何時與既有技能重複，防止知識碎片化
- 提供來源追蹤：哪個 session 生成了哪個本能，以及其信心的演進過程

## 市場角色分析

### Skill-0：基礎設施層
- **角色**: AI 技能管理的後端知識基礎設施
- **價值**: 技能定義的結構化、可搜尋性、治理與生命週期管理
- **市場**: 企業 AI 平台、工具註冊中心、技能市集、AI 治理團隊

### Everything Claude Code：執行層
- **角色**: 軟體開發的生產就緒執行工作流程
- **價值**: 以經過驗證的 AI 輔助工作流程即時提升開發者生產力
- **市場**: 使用 Claude Code 的個人開發者、工程團隊、開源貢獻者

### 競爭分析

直接競爭**極小**，因為兩者運作在不同層級：
- Skill-0 是**元系統**（解析、索引與治理技能）；ECC 是**技能集合**（定義與執行工作流程）。
- ECC 的 44+ 個技能全部可被 Skill-0 解析並索引，使 ECC 成為 Skill-0 解析能力最大規模的真實世界測試案例之一。

### 合作機會

1. **ECC 作為 Skill-0 最大的匯入來源**: 對 ECC 的 `skills/` 目錄執行 `tools/batch_import.py`，將 44+ 個技能解析為 Skill-0 的三元格式，建立 Claude Code 工作流程最完整的結構化技能登錄。

2. **Skill-0 作為 ECC 的品質關卡**: 將 Skill-0 的分析管線整合進 ECC 的 CI（GitHub Actions），對傳入的技能 PR 進行評分。品質低於門檻的技能在合併前需要補充文件。

3. **共享技能發現 API**: 透過 Skill-0 的 REST API（`/api/search`）公開 ECC 技能，讓使用者在不閱讀數十個 Markdown 檔案的情況下，以語意查詢所有 ECC 能力。

4. **本能 → 技能升級管線**: 將 ECC 的 `continuous-learning-v2` 輸出連接到 Skill-0 的治理工作流程。當抽取的本能達到足夠信心（如 ≥0.8）時，自動在 Skill-0 建立治理審查，以升級為正式的 ECC 技能。

5. **依賴感知技能套組**: 使用 Skill-0 的技能圖生成安裝套組。當使用者安裝 `django-tdd` 時，Skill-0 的依賴圖自動包含 `coding-standards` 與 `verification-loop`，防止設定不完整。

## 總結矩陣

| 面向 | Skill-0 | Everything Claude Code | 協同潛力 |
|------|---------|------------------------|----------|
| 架構 | 全端平台 | 外掛 + Markdown 技能 | Skill-0 索引所有 ECC 技能 |
| 可搜尋性 | 語意向量搜尋 | README 瀏覽 | 透過 Skill-0 搜尋 API 公開 ECC |
| 治理 | 內建審核工作流程 | 社群 PR | Skill-0 作為 ECC 的 CI 品質關卡 |
| 關係 | 明確的 skill_links 圖 | 慣例隱含 | 自動映射 ECC 依賴關係圖 |
| 學習 | Schema 版本化 | 本能型持續學習 | 在 Skill-0 向量儲存中索引本能 |
| 重複偵測 | 相似度偵測 | 人工審查 | 浮現冗餘的語言變體 |
| 發布 | REST API + JSON 目錄 | 外掛市集 | 為 ECC 提供結構化 JSON 目錄 |
| 目標受眾 | 平台/基礎設施建構者 | 日常 Claude Code 使用者 | 橋接：結構化治理 × 日常執行 |

> [!WARNING]
> 此比較基於 Skill-0 儲存庫（pingqLIN/skill-0）與 Everything Claude Code 儲存庫（affaan-m/everything-claude-code）截至 2026-02 的內容。專案功能與定位可能隨時間變更。

## 來源

- Skill-0 儲存庫: https://github.com/pingqLIN/skill-0
- Everything Claude Code 儲存庫: https://github.com/affaan-m/everything-claude-code
- ECC README: https://github.com/affaan-m/everything-claude-code/blob/main/README.md
- ECC 技能目錄: https://github.com/affaan-m/everything-claude-code/tree/main/skills
