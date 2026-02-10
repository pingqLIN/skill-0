# Skill-0 vs Cisco AI Defense Skill Scanner：安全掃描比較評估報告

**作者**: pingqLIN  
**日期**: 2026-02-10  
**版本**: 1.0.0

## 執行摘要

本報告比較 **Cisco AI Defense Skill Scanner** 與 **Skill-0** 的定位、架構、資料格式與安全掃描能力。Skill Scanner 聚焦於 **Agent Skills 安全檢測**（prompt injection、資料外洩、惡意程式碼等），提供多引擎掃描、SARIF 輸出與 CI/CD 整合；Skill-0 則聚焦於 **技能結構解析、語義搜尋與治理**，並內建基礎的規則式安全掃描與風險評分。

結論：兩者屬於高度互補角色。Skill-0 若吸收 Skill Scanner 的「多引擎安全掃描 + AITech 威脅分類」能力，可強化治理與企業落地場景；Skill Scanner 若結合 Skill-0 的結構化拆解與語義搜尋，可提升威脅解釋性與可追溯性。

---

## 1. 專案定位對比

### Skill-0
- **定位**：技能拆解分析器與語義搜尋引擎
- **核心價值**：將 Claude Skills/MCP Tools 解析為結構化 JSON (Schema 2.3.0)，提供可組合的原子元件與治理流程
- **安全面向**：內建規則式安全掃描（SEC001-SEC007）與治理資料庫

### Cisco AI Defense Skill Scanner
- **定位**：Agent Skills 安全掃描器
- **核心價值**：多引擎偵測 prompt injection、資料外洩、惡意程式碼，支援 SARIF/JSON/Markdown 報告
- **支援格式**：Agent Skills 規範（OpenAI Codex Skills、Cursor Agent Skills）

---

## 2. 技術架構與流程對比

| 維度 | Skill-0 | Skill Scanner |
|------|---------|---------------|
| **核心流程** | 解析 → 結構化 → 向量搜尋 → 治理 | 載入技能 → 多引擎掃描 → 風險報告 |
| **安全引擎** | 規則式掃描（Python regex） | 靜態規則 (YAML/YARA) + 行為資料流 + LLM Analyzer + Meta Analyzer |
| **介面** | Python CLI + FastAPI + Dashboard | CLI + FastAPI API |
| **輸出** | 治理 DB + 報告檔 | SARIF/JSON/Markdown/Table |
| **擴展性** | Parser abstraction + governance workflow | Analyzer 插件化 + ruleset 擴充 |

---

## 3. 資料格式對比

### Skill-0：結構化 JSON
- JSON Schema 2.3.0
- Action/Rule/Directive 三元分類
- 支援 provenance 與 skill_links

### Skill Scanner：SKILL.md
- YAML Frontmatter + Markdown 指令本體
- 允許工具權限（allowed_tools）、相容性（compatibility）等欄位

---

## 4. 安全能力對比

| 能力 | Skill-0 | Skill Scanner |
|------|---------|---------------|
| **Prompt Injection** | 規則式檢測 | YAML/YARA + LLM 判斷 |
| **資料外洩** | 規則式檢測 | 行為資料流 + LLM 分析 |
| **惡意程式碼** | 規則式檢測 | 靜態規則 + 行為分析 |
| **威脅分類** | SEC001-SEC007 | AITech Taxonomy 對應 |
| **CI/CD** | 需自行封裝 | 內建 fail-on-findings + SARIF |
| **誤報抑制** | 無 meta-analyzer | Meta Analyzer 降噪 |

---

## 5. 使用情境對比

### Scenario A：技能治理與結構化分析
- **Skill-0 勝出**：可追溯的技能拆解與語義搜尋

### Scenario B：企業 CI 安全檢測
- **Skill Scanner 勝出**：SARIF 輸出、fail-on-findings、支援 LLM/行為分析

### Scenario C：安全規則與威脅分類
- **Skill Scanner 勝出**：AITech Taxonomy 與多類別威脅模型

---

## 6. 優劣勢整理

### Skill-0 優勢
1. **結構化深度**：可組合的 Action/Rule/Directive
2. **語義搜尋**：向量檢索與模式分析
3. **治理流程**：審批、風險評分、歷史紀錄

### Skill-0 劣勢
1. **安全引擎單一**：主要為規則式掃描
2. **缺乏標準化威脅分類**：未對齊 AITech/OWASP
3. **CI 報告格式不足**：缺少 SARIF

### Skill Scanner 優勢
1. **多引擎偵測**：靜態 + 行為 + LLM + Meta
2. **CI/CD 友善**：SARIF、fail-on-findings
3. **威脅分類完整**：AITech Taxonomy 對應

### Skill Scanner 劣勢
1. **缺乏結構化拆解**：無 Action/Rule/Directive
2. **無語義搜尋**：缺少跨技能模式分析
3. **治理流程較弱**：審批與 provenance 管理不足

---

## 7. 互補性與整合可能性

建議以 Skill-0 作為「結構化與治理層」，Skill Scanner 作為「安全掃描層」：

```
┌──────────────────────────┐
│ Skill Scanner            │
│ 多引擎安全掃描 (SARIF)    │
└─────────────┬────────────┘
              │ Findings
              ↓
┌──────────────────────────┐
│ Skill-0 Governance        │
│ 風險分級 + 技能拆解 + 搜尋 │
└──────────────────────────┘
```

---

## 8. 對 Skill-0 的升級與新增技能建議

### 8.1 升級項目
1. **導入 AITech 威脅分類**：在安全掃描結果中加入 taxonomy code 與 category。
2. **擴充規則引擎**：支援 YAML/YARA 規則檔案與多語言掃描。
3. **SARIF 輸出與 CI Gate**：增加 `--format sarif` 與 `--fail-on-findings` 參數。
4. **Analyzer 插件架構**：允許 LLM/行為分析器模組化啟用。
5. **SKILL.md 載入器**：直接支援 Agent Skills 格式並轉為 Skill-0 JSON。

### 8.2 建議新增技能（Skill-0 Skill 形式）
1. **Skill Security Audit**：輸入技能資料夾，輸出 SARIF/Markdown 風險報告。
2. **Threat Taxonomy Mapper**：將掃描結果映射為 AITech/OWASP/NIST 分類。
3. **Secure Skill Packaging**：檢查 allowed_tools、metadata 完整性與描述一致性。
4. **Security Rule Authoring Guide**：協助撰寫/驗證安全掃描規則與測試樣本。

---

## 9. 結論

Skill Scanner 提供了成熟的安全掃描引擎與威脅分類體系，Skill-0 則提供結構化拆解與治理。若 Skill-0 吸收 Skill Scanner 的偵測與輸出能力，可形成「結構化 + 安全 + 治理」的完整技能安全平台，提升企業與 CI/CD 場景的落地價值。

---

## 10. 參考資料

- https://github.com/cisco-ai-defense/skill-scanner
- https://raw.githubusercontent.com/cisco-ai-defense/skill-scanner/main/docs/architecture.md
- https://raw.githubusercontent.com/cisco-ai-defense/skill-scanner/main/docs/threat-taxonomy.md
- https://github.com/pingqLIN/skill-0
