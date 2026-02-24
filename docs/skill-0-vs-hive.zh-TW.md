# Skill-0 vs Hive

比較兩個 AI 代理專案：**Skill-0**（結構化技能拆解、語意搜尋與治理）與 **Hive**（目標驅動、自我改進的自主代理框架）。本文件評估相似之處、差異、可借鑑優點，以及市場合作潛力。

## 定位

- **Skill-0**: 三元分類系統，將 AI 技能/工具指令解析為結構化 JSON（Actions / Rules / Directives），存入 SQLite 搭配向量嵌入，提供語意搜尋、群集分析、技能關係圖、治理流程與 React 儀表板 API。
- **Hive**: 生產級自主代理框架，開發者以自然語言描述目標，由程式碼代理自動生成可執行節點圖。框架捕捉執行失敗、透過反思迴圈（Reflexion Loop）演化圖結構並重新部署，實現自我改進的多代理協作，並內建 HITL（人類在迴路中）控制、即時可觀測性與成本管理。

## 流程比較

| 面向 | Skill-0 | Hive |
|------|---------|------|
| **輸入** | 技能/工具定義（Markdown/JSON） | 自然語言目標描述 |
| **核心流程** | 解析 → 分類 → 索引 → 搜尋 → 治理 | 定義目標 → 自動生成圖 → 執行 → 監控 → 演化 |
| **輸出** | 結構化 JSON、語意搜尋結果、技能關係圖 | 執行中的自主代理，交付業務成果 |
| **主要目標** | 技能定義的知識抽取、發現與生命週期治理 | 無需硬編碼流程，打造生產級自我改進代理 |
| **使用方式** | CLI、REST API、React 儀表板 | 程式碼代理（Claude Code / Codex CLI / Cursor）、TUI 儀表板、hive CLI |
| **執行模式** | 靜態分析（離線，無執行時期） | 即時代理執行，含即時節點串流 |
| **自適應性** | 無（Schema 驅動的靜態分類） | 自我修復：捕捉失敗 → 演化圖 → 重新部署 |

## 相似之處

1. **MCP（模型上下文協定）為核心**: 兩個專案都深度整合 MCP。Skill-0 解析並索引 MCP 工具技能；Hive 內附 102 個 MCP 工具，並公開 `agent-builder` MCP 伺服器供程式碼代理使用。
2. **AI 行為的結構化分類**: 兩者都對 AI 操作施加正式結構。Skill-0 使用三元 Schema（Actions / Rules / Directives）；Hive 使用 `Goal`、`SuccessCriterion`、`Constraint` 和 `EvaluationRule` 物件。
3. **規則導向驗證**: 兩者都定義明確規則來約束 AI 行為。Skill-0 的 `Rules` 分類（condition_type、failure_consequence）；Hive 的 `EvaluationRule` 以優先順序排列，在任何 LLM 呼叫前先評估確定性檢查。
4. **Claude / Anthropic 一等整合**: 兩者都將 Anthropic Claude 視為一等整合 — Skill-0 索引 Claude 技能並使用 Claude Code 相容的 SKILL.md；Hive 有原生 Claude Code 斜線命令（`/hive`、`/hive-debugger`），並以 Anthropic 為主要 LLM 提供者。
5. **以 Python 為基礎的架構**: 兩者主要以 Python（3.11+/3.12+）搭配現代工具鏈（`uv`、FastAPI、Pydantic）建構。
6. **可觀測性儀表板**: 兩者都包含監控儀表板。Skill-0 提供以 React 為基礎的網頁儀表板；Hive 提供含即時圖形檢視、事件日誌與 WebSocket 串流的終端機 TUI。
7. **寬鬆授權的開源專案**: 兩者都是公開的開源專案（Apache 2.0）。
8. **人類在迴路中的意識**: 兩者都認識到人類監督的必要性 — Skill-0 透過治理審核流程與稽核日誌；Hive 透過暫停執行等待人類輸入的一等 HITL 干預節點。
9. **記憶體架構**: 兩者都明確建模記憶體。Skill-0 使用向量嵌入（384 維）進行語意檢索；Hive 透過 `aden_tools` SDK 提供每個節點的 STM（短期記憶）和 LTM（長期記憶）。
10. **節點／元件圖形思維**: 兩者都將系統表示為圖或網路。Skill-0 有 `skill_links`（Schema v2.3.0）含 7 種關係類型；Hive 生成含自動生成連接程式碼的動態節點執行圖。

## 差異

| 面向 | Skill-0 | Hive |
|------|---------|------|
| **核心典範** | 技能知識管理（解析、索引、治理） | 自主代理執行（執行、監控、自適應） |
| **執行** | 無執行時期 — 靜態離線分析 | 即時代理執行，含即時節點串流 |
| **自適應性** | 無 — 技能為靜態成品 | 反思迴圈：捕捉失敗 → 演化圖 → 重新部署 |
| **驗證模型** | JSON Schema 驗證 + CI 語法檢查 | 三角驗證：確定性規則 + LLM 評判 + 人類判斷 |
| **多 LLM 支援** | 索引的技能引用特定 LLM | LiteLLM 整合：100+ 提供者（OpenAI、Anthropic、Gemini、Ollama...） |
| **HITL 支援** | 治理審核流程（非同步、手動） | 一等干預節點，含可配置逾時與升級策略 |
| **成本控制** | 無 | 預算上限、節流、自動模型降級策略 |
| **技能發現** | 向量嵌入語意搜尋 | 非主要功能（代理由生成產生，非搜尋） |
| **Schema 正式化** | JSON Schema v2.2.0 含版本控制與 resource_dependency | Goal、Node、Constraint、EvaluationRule 的 Pydantic 模型 |
| **治理** | 審核流程、稽核日誌、安全掃描（batch_security_scan.py） | 社群驅動、SECURITY.md、透過 HITL 人類升級 |
| **部署** | 自架（Python + SQLite + React） | 可自架；雲端部署在路線圖中 |
| **目標受眾** | 平台建構者、AI 研究者、技能策展人、治理團隊 | 為真實業務流程建構生產級自主代理的開發者 |
| **程式碼代理整合** | SKILL.md + AGENTS.md 指令 | 為 Claude Code、Cursor、Codex CLI、Opencode、Antigravity 提供原生斜線命令 |
| **技能／知識數量** | 32+ 已解析、171 已匯入 converted-skills | 無限（使用者定義目標 → 自動生成代理） |
| **技術架構** | Python、FastAPI、SQLite-vec、sentence-transformers、React+Vite | Python、uv 工作區、LiteLLM、WebSocket、Click TUI |

## 可借鑑的優點

### 1. 三角驗證以提升技能品質

Hive 的三信號驗證模型（確定性規則 → LLM 評估 → 人類升級）是 Skill-0 可應用於技能解析與治理的穩健品質方法：
- 在已解析的技能 JSON 中加入 `quality_signals` 區塊：Schema 驗證分數、LLM 判斷的完整性分數，以及人類審核旗標。
- 以至少兩個信號的收斂作為治理批准的門檻，取代純手動審核。

### 2. 加權成功標準到技能定義

Hive 的 `Goal` 模型將 `success_criteria` 定義為加權、多維度指標。Skill-0 可在技能定義中加入可選的 `success_criteria` 陣列：
- 每個標準指定 `id`、`description`、`metric`（如 `llm_judge`、`schema_field_present`）和 `weight`。
- 這使「完成」可量化而非僅有結構性要求，實現每個技能的自動化品質評分。

### 3. 受反思迴圈啟發的失敗模式記錄

Hive 捕捉失敗數據並迭代演化代理（受 Reflexion 論文啟發）。Skill-0 可在技能定義中加入 `failure_patterns` 欄位：
- 記錄已知失敗模式、恢復策略和 `evolution_hints`（演化提示）。
- 治理流程可儲存失敗回饋並將其提供給技能作者，支援迭代改進。

### 4. 成本與資源預算約束

Hive 提供細粒度預算控制（團隊/代理/流程層級）。Skill-0 的 `resource_dependency` Schema（v2.2.0）已追蹤資源類型。在其中擴展 `budget_constraint` 物件（token 上限、API 呼叫上限、運算成本上限）將實現成本感知的技能治理。

### 5. LiteLLM 多提供者標記

Hive 的 LiteLLM 整合以簡單的模型名稱格式支援 100+ 提供者。Skill-0 可在技能元數據中加入 `supported_llm_providers` — 讓使用者依使用的 LLM 篩選技能，並允許語意搜尋 API 返回提供者相容的結果。

### 6. 目標導向的 Directive 強化

Hive 的 `Goal` 物件明確捕捉意圖（描述、成功標準、約束）。Skill-0 `completion` 類型的 `Directives` 概念上類似，但缺乏加權標準。為 `completion` directives 加入 `satisfaction_score` 機制，將使其與目標驅動設計對齊。

### 7. 治理流程中的 HITL 干預

Hive 的干預節點（暫停、等待人類輸入、帶逾時的升級）可以啟發 Skill-0 的治理審核者流程。在 `skill_governance.py` 流程中加入可配置的升級逾時和正式的 ESCALATE/APPROVE/REJECT 狀態，將使其達到生產級標準。

### 8. 無頭環境的 TUI 儀表板

Hive 的終端機 UI 提供無需瀏覽器的即時監控。Skill-0 可為治理儀表板提供輕量 TUI 模式 — 在 CI 管線和無頭伺服器環境中非常實用 — 使用現有的 Python TUI 函式庫（如 Textual 或 Rich）。

### 9. 憑證管理模式

Hive 內附加密憑證儲存（`~/.hive/credentials`）用於管理各代理的 API 金鑰。Skill-0 沒有憑證管理機制。在 `resource_dependency` Schema 的 `credentials` 類型中加入整合秘密儲存的專屬憑證區塊，將強化生產環境就緒性。

## 市場角色分析

### Skill-0：知識基礎設施層

- **角色**: AI 技能生命週期管理的後端知識平台
- **價值**: 技能定義的結構化、語意可發現性、治理與版本管理
- **市場**: 企業 AI 平台、MCP 工具註冊中心、技能市集、AI 治理團隊

### Hive：代理執行執行時期層

- **角色**: 具自我改進能力的生產級自主代理執行時期
- **價值**: 部署執行真實業務流程的目標驅動代理，失敗時自我修復，無需硬編碼流程工程
- **市場**: 為業務流程建構生產 AI 代理的開發團隊（CRM、客服、分析、資料管線）

### 競爭分析

直接競爭**極小**，因為兩個系統在互補的層級運作：
- Skill-0 是**元系統**（管理、索引和治理技能知識）。
- Hive 是**執行系統**（建構並執行代理以達成目標）。
- Hive 的節點架構和代理定義本身可被 Skill-0 解析並索引為結構化技能條目。

### 合作機會

1. **Hive 代理作為 Skill-0 條目**: 將 Hive 的節點模板和 Worker Agent 定義解析為 Skill-0 的三元格式，為 Hive 模式建立可搜尋的結構化條目。

2. **Skill-0 作為 Hive 的知識骨幹**: Skill-0 的語意搜尋 API 可作為 Hive 程式碼代理搜尋可重用代理模式時的檢索層 — 實質上成為 Hive 節點藍圖的「技能商店」。

3. **Hive 技能的治理管線**: Skill-0 的治理流程（審核、稽核、安全掃描）可在 Hive 代理匯出檔案投入生產前套用，增加正式批准閘道。

4. **三元 ↔ 目標映射**: Skill-0 的 Actions 對應 Hive 節點執行；Skill-0 的 Rules 對應 Hive 的 `EvaluationRule` 和 `Constraint` 物件；Skill-0 的 Directives 對應 Hive 的 `Goal` 描述。雙向轉換器將實現往返互操作性。

5. **品質評分平台**: Skill-0 的分析工具可根據約束覆蓋率、規則完整性和 HITL 存在性評估和評分 Hive 代理圖 — 為潛在的代理市集提供品質認證層。

## 總結矩陣

| 面向 | Skill-0 | Hive | 協同潛力 |
|------|---------|------|----------|
| 核心角色 | 知識管理 | 代理執行執行時期 | Skill-0 索引 Hive 代理模式 |
| 執行 | 靜態分析 | 即時自適應執行 | Skill-0 治理 Hive 所執行的技能 |
| 驗證 | Schema + CI 語法檢查 | 三角驗證（規則 + LLM + 人類） | 借鑑三角模型提升技能品質 |
| 自適應性 | 無 | 反思迴圈（自我改進） | 在 Skill-0 Schema 中加入 failure_patterns |
| HITL | 手動審核流程 | 一等干預節點 | 為 Skill-0 治理升級加入 HITL 逾時 |
| 成本控制 | 無 | 預算 + 模型降級 | 在 resource_dependency 中加入 budget_constraint |
| 記憶體 | 向量嵌入（語意搜尋） | 每節點 STM/LTM | 兩者都展示記憶體優先的 AI 架構 |
| MCP 整合 | 解析 102+ 個 MCP 技能 | 內附 102 個 MCP 工具 | Skill-0 提供索引；Hive 提供執行時期 |
| 儀表板 | React 網頁儀表板 | 終端機 TUI | 交叉借鑑：Skill-0 加入 TUI 模式 |
| 多 LLM | 單一嵌入模型 | LiteLLM 100+ 提供者 | 在技能中標記 supported_llm_providers |
| 治理 | 流程 + 稽核日誌 | 社群 + HITL 升級 | 結合：Skill-0 正式治理應用於 Hive 代理 |

> [!WARNING]
> 此比較基於 Skill-0 儲存庫（pingqLIN/skill-0）與 Hive 儲存庫（bryanadenhq/hive）截至 2026-02 的內容。專案功能與定位可能隨時間變更。Hive 由 Aden（Y Combinator）支持且處於積極開發中；路線圖項目（JS/TS SDK、雲端部署、評估系統）可能在本文件更新前上線。

## 來源

- Skill-0 儲存庫: https://github.com/pingqLIN/skill-0
- Hive 儲存庫: https://github.com/bryanadenhq/hive
- Hive 文件: https://docs.adenhq.com/
- Hive 架構: https://github.com/bryanadenhq/hive/blob/main/docs/architecture/README.md
- Hive 路線圖: https://github.com/bryanadenhq/hive/blob/main/docs/roadmap.md
