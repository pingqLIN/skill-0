# Final Development Phase Plan — 策略審查意見

**審查對象：** `docs/final-development-phase-plan-2026-03-23.md`
**審查日期：** 2026-03-23
**審查基礎：** 計畫書全文、先前技術審查意見書（SKILL0-REVIEW-2026-03-23）、dossier 全 7 章、shared contracts 4 份、`auto_parse.py` 原始碼、`skill-0-GUI` 完整 codebase 與文件、schema v2.4.0 JSON

---

## 壹、整體評價

本計畫書在結構品質與定位清晰度上表現**優於多數同類文件**。它正確地：

- 以已驗證基線為出發點，而非重複描述願景
- 明確劃定 non-goals，避免稀釋焦點
- 將 cross-repo contract 視為顯式工作流，而非附帶事項
- 區分「可審核」與「正式營運 ready」的定位

然而，經交叉比對實際代碼庫狀態與文件系統後，本審查發現**計畫書對若干工作流的工程規模存在系統性低估**，且有數項執行層級風險在現有風險清單（§11）中缺席。

**總體判定：計畫方向正確，但需補強執行層解析度後方可作為實際排程依據。**

---

## 貳、強項與穩健決策

### 2.1 計畫結構

| 優點 | 說明 |
|------|------|
| 基線定義清晰 | §3 明確列舉已驗證事實，不混入願望 |
| Non-goals 有約束力 | §5 將 mono-repo 合併、HA 驗證、full graph IDE 明確排除 |
| 四條工作流分工合理 | A（營運加固）、B（parser P0）、C（GUI surface）、D（文件收斂）四者職責不重疊 |
| 驗收標準存在且可審計 | §9 五項 acceptance criteria 可追溯、可檢查 |
| 外部審查引導 | §12 直接告訴外部審查方該看什麼，降低誤判 |

### 2.2 Cross-repo 治理成熟度

Shared documentation model 已實際運行：

- `docs/shared/` 包含 4 份 contract 文件
- `skill-0-GUI` 已有 `npm run docs:sync` + `npm run docs:check`
- `shared-docs.manifest.json` + `sync-shared-docs.mjs` 已驗證可用
- 術語表、parser contract、mode/equivalence contract 定義清楚

這是少見的——多數 cross-repo 專案在此階段不會有如此完整的 contract 基礎設施。

### 2.3 Complex-skill 策略方法論

`07-complex-skills-analysis-strategy.md`（268 行）的三階段策略（Discovery → Dependency Summary → Selective Deep Parse）是本計畫最強的智識資產。它正確地拒絕了「先完整展平再分析」的直覺，選擇了 manifest-first、warning-driven、按需深解析的路線。

---

## 參、關鍵問題：計畫與代碼庫現實的落差

### 🔴 問題一：Workstream B 的工程規模被嚴重低估

計畫書 §6 Workstream B 描述為「把目前停留在策略與文件層的 complex-skill analysis，正式做進 `skill-0`」，給人一種「接上去」的印象。

**但代碼庫的實際狀態是：**

| 計畫書假設 | 代碼庫實際狀態 |
|-----------|--------------|
| 「正式做進」暗示在既有基礎上延伸 | `auto_parse.py` 的 parser **沒有任何** complex skill 支援 |
| manifest extraction | ❌ 不存在 |
| frontmatter structured field extraction | ❌ 僅做簡單 key/value，不解析 YAML 複合結構 |
| markdown relative-link extraction | ❌ 不存在 |
| supporting files summary | ❌ 不存在 |
| command-reference risk grading | ❌ 命令提取僅抓最多 5 筆 fenced code block，轉為 generic actions，無風險分級 |
| mode-aware confidence / warning basis | ❌ 不存在 |

**結論：** Workstream B 不是「將策略落地」，而是**從零實作一個全新的分析層**。計畫書應明確承認此落差，否則排程與資源預期會嚴重失準。

### 🔴 問題二：Schema 擴展工作完全不可見

計畫書提到 parser 應能「emit manifest-oriented structure」，但 `skill-decomposition.schema.json`（v2.4.0）目前：

| 已有 | 缺少 |
|------|------|
| `provenance` 物件結構 | 明確的 `manifest` 頂層欄位 |
| `provenance_location` | `supporting_files` 集合 |
| `parser_meta` | `command_references` 結構化類型 |
| `requires_deep_parse` flag | `risk_grade` / `execution_authority` 欄位 |
| `related_elements` | `delegation_nodes`（for `context: fork` / `agent`） |

Schema 擴展本身不難，但它牽動：

1. parser output format（B 的產出）
2. GUI consumption shape（C 的輸入）
3. shared contract wording（D 的同步對象）
4. schema 版本號（現已散落 v2.0 / v2.4，不宜再新增混亂）

**建議：** 在 Workstream B 開始前，先完成一次 schema extension design，作為 B/C/D 的共同基礎。

### 🟠 問題三：Parser API 函數簽名斷裂風險

`skill-0-GUI` 的 bridge 直接呼叫：

```python
parse_skill_md(skill_name, text)
```

但 complex-skill analysis 需要的輸入不再是「一個技能名 + 一段文字」，而是：

- 一個進入點路徑
- 可能包含多個 supporting files
- 可能需要 filesystem context（解析相對路徑連結）

**如果 Workstream B 改變了 parser 函數簽名，bridge 就會斷裂。**

計畫書完全沒有提及這個 API migration 策略。建議的解法：

1. **維持 `parse_skill_md(name, text)` 做向後相容路徑**
2. **新增 `parse_skill_manifest(entry_path, options)` 做 complex skill 入口**
3. **在 parser contract（`01-parser-contract.md`）中明確記錄雙入口**

### 🟠 問題四：skill-0-GUI 沒有測試框架

計畫書 §6 Workstream C 的 exit criteria 要求 GUI 能：

- 區分 canonical vs standalone mode
- 顯示 manifest summary
- 渲染 prioritized warning set
- 明確表達 fallback degradation

但 `skill-0-GUI` 的 `package.json` **連測試框架都沒有安裝**：

```json
"devDependencies": {
  "@types/express": "^4.17.21",
  "@types/node": "^22.14.0",
  "tailwindcss": "^4.1.14",
  "tsx": "^4.21.0",
  "typescript": "~5.8.2",
  "vite": "^6.2.0"
}
```

- ❌ 無 Vitest、Jest、Playwright、Cypress
- ❌ 無任何 `.test.ts` / `.spec.tsx` 檔案
- ❌ bridge 也沒有測試

**建議：** 在 Workstream C 開始前，先把 Vitest 加入 GUI devDependencies，並建立最低限度的 bridge contract test。否則 exit criteria 無法被機器驗證，只能人眼判斷。

### 🟠 問題五：GUI 的 source tree 不穩定

探索結果顯示 `skill-0-GUI` 的 `src/` workbench 在 working tree 中已被刪除，但仍被 Git HEAD 追蹤。計畫書 Workstream C 的前提是在 GUI 上建構 review surface，但目前的 codebase 狀態是：

- 營運 frontend 是 `dist/`-driven（可用但不利於開發）
- source tree 與 Git state 不一致

**建議：** Workstream C 應在開始前先做一次 source tree stabilization：要嘛正式刪除 `src/` 並以 `dist/` 為交付基線，要嘛重建 `src/` 並恢復 dev build 流程。模糊狀態會拖慢所有後續開發。

---

## 肆、工作流排序與隱藏關鍵路徑

計畫書把四條工作流並列呈現，但實際執行順序不是自由的：

```
                    ┌─────────────────┐
                    │  Schema Design  │ ← 新增：B/C/D 的共同前提
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼                             ▼
    ┌─────────────────┐          ┌─────────────────┐
    │   Workstream A  │          │   Workstream B   │
    │ Runtime harden  │          │  Parser P0 impl  │
    │   （獨立可並行） │          │  （最大工作量）   │
    └─────────────────┘          └────────┬─────────┘
                                          │
                                          ▼
                                ┌─────────────────┐
                                │   Workstream C   │
                                │  GUI integration │
                                │ （等 B 產出才能做）│
                                └────────┬─────────┘
                                          │
                                          ▼
                                ┌─────────────────┐
                                │   Workstream D   │
                                │  Doc closure     │
                                │ （等 B+C 穩定後） │
                                └─────────────────┘
```

**關鍵觀察：**

| 工作流 | 實際依賴 | 相對工作量 |
|--------|---------|-----------|
| A（Runtime hardening） | 獨立 | 小（量測 + SOP + 文件更新） |
| B（Parser P0） | Schema design | **大**（全新實作 6 個子功能） |
| C（GUI integration） | B 的 output shape | 中（但受 source tree 穩定性影響） |
| D（Doc closure） | B + C 基本穩定 | 小（但必須等在最後） |

**問題：** 如果 B 延遲，C 和 D 全部連鎖延遲。整個計畫的 critical path 就是 B。

**建議：**

1. 在計畫書中明確標註 B → C → D 的順序依賴
2. 允許 C 在 B 未完成時先做「mode awareness」與「fallback degradation display」——這些不依賴新 parser output
3. A 應立刻開始，不等 B

---

## 伍、風險清單缺項

計畫書 §11 列了 4 項風險。以下是經代碼庫交叉驗證後發現的**額外風險**：

### 新增 Risk 5：Parser API 簽名斷裂

- **觸發條件：** Workstream B 改變 `parse_skill_md()` 簽名或語義
- **影響：** GUI bridge 即時斷裂，standalone fallback 行為偏離
- **應變：** 雙入口策略（保留舊簽名 + 新增 manifest 入口）
- **嚴重度：** 🔴 High

### 新增 Risk 6：測試基礎設施空白

- **觸發條件：** Workstream B/C 進入驗收階段
- **影響：** Exit criteria 無法機器驗證，只能人眼確認
- **應變：** 優先補齊 Python parser fixture tests + GUI Vitest 基礎
- **嚴重度：** 🟠 Medium-High

### 新增 Risk 7：Schema 版本分裂加劇

- **觸發條件：** Workstream B 新增 schema 欄位但未統一版本號
- **影響：** 已知的 v2.0 / v2.4 分裂進一步惡化；AI agent 可能依據舊版格式生成不相容的輸出
- **應變：** 在 schema extension 時一併收斂所有版本引用至單一編號
- **嚴重度：** 🟡 Medium

### 新增 Risk 8：Complex skill 測試 fixtures 不存在

- **觸發條件：** Parser P0 實作完成後需要驗證
- **影響：** 沒有範本 complex skill（含 supporting files、subagent、frontmatter）可用於測試
- **應變：** 從 `converted-skills/` 挑選或手動建立 3-5 個漸進複雜度的 test fixtures
- **嚴重度：** 🟡 Medium

---

## 陸、驗收標準的可測試性評估

| §9 Acceptance Criteria | 可測試性 | 建議 |
|------------------------|---------|------|
| 1. runtime baseline remains reproducibly verifiable | ✅ 可測試：重跑 Docker compose + health check | 維持現有驗證流程 |
| 2. complex-skill analysis exists in code | ⚠️ 模糊：「at least P0 analysis exists in code」未定義具體檢查方式 | 補充：parser 能對至少 3 個不同複雜度的 test fixture 產出 manifest + warnings |
| 3. GUI can present mode-aware, evidence-backed, reviewer-meaningful output | ❌ 不可測試：「reviewer-meaningful」是主觀判斷 | 補充：定義 3 個 concrete acceptance scenarios，每個有明確的 expected UI state |
| 4. shared-doc mirroring is operational and current | ✅ 可測試：`npm run docs:check` 應 exit 0 | 直接可用 |
| 5. document package clearly separates verified / risks / roadmap | ⚠️ 半可測試：結構可查，「清楚程度」主觀 | 補充：要求外部審查方視角的 smoke read test |

---

## 柒、逆向思考：失敗場景分析

### 場景 A：Parser P0 做出來但 GUI 接不上

**觸發條件：** B 產出的 manifest 結構與 C 預期的 consumption shape 不一致
**原因：** 沒有先做 schema extension design，B 和 C 各自假設
**後果：** C 必須大量返工適配，D 的 contract sync 也被迫重做
**預防：** schema extension design 先行 + parser output example 先跑通一次 end-to-end

### 場景 B：Complex skill 分析品質不夠、被外部審查方質疑

**觸發條件：** P0 只做了 manifest extraction 但沒有真正有價值的 warning
**原因：** warning basis 缺乏真實世界 complex skill 的 ground truth
**後果：** 外部審查方認為 complex skill 能力只是文件聲明
**預防：** 用 3-5 個真實 skill（含 anthropic-pdf-skill 等已有案例）做 demo-grade output

### 場景 C：計畫完成但文件比實作更完整

**觸發條件：** 已有 268 行策略文件 + 80 行 analysis spec + 80 行 risk schema，但 parser 只做了基本 manifest
**原因：** 文件系統太成熟，對比之下實作顯得單薄
**後果：** 外部審查方看文件以為能力很強，實際測試後落差大
**預防：** 在文件中明確標註「implemented / designed / planned」三層區分

### 場景 D：Cross-repo sync 在高頻變更下失控

**觸發條件：** Workstream B 密集修改 parser contract，D 追不上
**原因：** `docs:sync` 是手動觸發，不在 CI 中
**後果：** GUI 端文件與 skill-0 端漂移，外部審查方收到不一致的版本
**預防：** 在 GUI 的 CI 中加入 `npm run docs:check`，變更不一致時 fail

---

## 捌、具體行動建議

### 優先序一：計畫書修正（立即）

1. **在 Workstream B 開頭加入明確聲明**：目前 parser 對 complex skill 的支援為零，本工作流為全新實作
2. **新增 "Workstream B.0: Schema Extension Design"**：在 parser 實作前，先定義 manifest / supporting_files / command_references 的 schema 結構，並產出 sample output JSON 供 C 提前準備
3. **在 §11 補入 Risk 5-8**（parser API 斷裂、測試空白、schema 分裂、fixture 缺失）
4. **在 §7 Milestones 中標註依賴關係**：M2 depends on schema design；M3 depends on M2；M4 depends on M2+M3

### 優先序二：執行前準備工作

5. **建立 3-5 個 complex skill test fixtures**：從 `converted-skills/` 挑選 + 手動構建，涵蓋單檔、多檔、含 subagent、含 frontmatter 四種類型
6. **在 GUI 安裝 Vitest**：`npm install -D vitest`，建立一個最低限度的 bridge contract test
7. **穩定 GUI source tree**：決定 `src/` 的命運——刪除或重建

### 優先序三：執行中防護

8. **Parser 雙入口策略**：`parse_skill_md()` 維持向後相容，新增 `parse_skill_manifest()` 為 complex skill 入口
9. **在 GUI CI 加入 `npm run docs:check`**：防止 cross-repo 文件漂移
10. **每個 milestone 產出時同步更新「implemented / designed / planned」標記**：確保文件不會跑在實作前面

---

## 玖、與先前審查意見書的銜接

| 先前審查意見書（SKILL0-REVIEW-2026-03-23）風險項 | 本計畫是否涵蓋 |
|----------------------------------------------|-------------|
| RISK-1：API 容器記憶體壓力 | ✅ Workstream A 包含量測 |
| RISK-2：雙 SQLite 備份策略 | ✅ Workstream A 包含 SOP |
| RISK-3：Production secrets 未覆寫 | ⚠️ 未明確提及，但 fail-fast 已存在 |
| RISK-4：Rate limiter 反向代理行為 | ❌ 未被計畫涵蓋 |
| RISK-5：搜尋端點無 try-catch | ❌ 未被計畫涵蓋 |
| RISK-6：治理操作同步阻塞 | ❌ 未被計畫涵蓋 |
| RISK-7：Schema 版本散落 | ⚠️ 間接涵蓋（Workstream A README 更新） |
| RISK-8：README 測試數字 | ⚠️ 間接涵蓋（Workstream A wording 收斂） |

**觀察：** 計畫書的 Workstream A 涵蓋了營運級風險（RISK 1-3），但先前審查發現的代碼品質風險（RISK 4-6）未被納入任何工作流。建議在 Workstream A 中追加「搜尋端點 graceful error handling」與「rate limiter forwarded-header 支援」作為 P1 項目。

---

## 拾、總結判定

### 計畫書品質

| 維度 | 評分 | 說明 |
|------|------|------|
| 結構清晰度 | ★★★★★ | 13 個章節邏輯連貫，可單獨抽讀 |
| 定位準確性 | ★★★★★ | 正確區分審核基線與營運結案 |
| 工程規模估計 | ★★☆☆☆ | Workstream B 嚴重低估；schema 擴展不可見 |
| 風險完整性 | ★★★☆☆ | 4 項風險合理但不完整；缺少 4 項執行層風險 |
| 驗收可測試性 | ★★★☆☆ | 5 項中有 2 項不夠具體 |
| 關鍵路徑透明度 | ★★☆☆☆ | 工作流依賴未標示；B 是 critical path 但未被識別 |
| Cross-repo 治理 | ★★★★★ | 業界少見的完整度 |

### 最終建議

本計畫書**方向正確、定位成熟、cross-repo 治理優秀**，但在進入執行前，需要：

1. **承認 Workstream B 的真實起點是零**，調整對外溝通與資源預期
2. **前置 schema extension design**，讓 B/C/D 有共同的結構基礎
3. **補齊測試基礎設施**，讓 exit criteria 可被機器驗證
4. **標示關鍵路徑**，讓排程決策者知道 B 的延遲 = 全計畫延遲

完成以上四項修正後，本計畫書可作為外部技術審核與內部執行協調的**可靠依據**。

---

*策略審查意見完*
