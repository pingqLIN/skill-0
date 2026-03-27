# Final Development Phase Plan — 第二輪策略審查意見

**審查對象：** `docs/final-development-phase-plan-2026-03-23.md`（修正後版本）
**前次審查：** `docs/final-phase-plan-review-2026-03-23.md`
**審查日期：** 2026-03-23
**審查方法：** 逐項比對前次 10 項建議的採納情形 + 代碼庫狀態二次驗證 + 新引入問題辨識

---

## 壹、前次審查建議採納情形

### 結構性修正（4 項核心建議）

| # | 前次建議 | 修正後計畫 | 採納判定 |
|---|---------|-----------|---------|
| 1 | 承認 Workstream B 起點為零 | §6B Workstream B 開頭明確聲明「新分析層的首版實作，而不是既有 parser 的小幅延伸」，並逐項列出 6 個 ❌ 不存在的能力 | ✅ 完整採納 |
| 2 | 前置 schema extension design | 新增 Foundation F1，定義 5 項最低交付物，且標示為 B/C/D 的共同前提 | ✅ 完整採納 |
| 3 | 補齊測試基礎設施 | 新增 Foundation F2，明確要求 Python fixtures、3+ complex-skill fixtures、GUI test baseline、bridge contract tests | ✅ 完整採納 |
| 4 | 標示關鍵路徑 | §6B 明確標示 `F1 → F2 → B → C → D`，且聲明 A 應獨立並行 | ✅ 完整採納 |

### 執行層建議（6 項行動建議）

| # | 前次建議 | 修正後計畫 | 採納判定 |
|---|---------|-----------|---------|
| 5 | 建立 3-5 個 complex skill test fixtures | F2 納入 | ✅ 採納 |
| 6 | GUI 安裝 Vitest | F2 提及「GUI test baseline」但未指定框架 | ⚠️ 方向採納，細節未落地 |
| 7 | 穩定 GUI source tree | Workstream C 前置條件中提及，列為開始前必須決策 | ✅ 採納 |
| 8 | Parser 雙入口策略 | Workstream B 明確寫入「保留 `parse_skill_md` + 新增 manifest-oriented entrypoint」 | ✅ 完整採納 |
| 9 | GUI CI 加入 `npm run docs:check` | ❌ 未被納入 | ❌ 遺漏 |
| 10 | 文件標註「implemented / designed / planned」三層 | ❌ 未被納入 | ❌ 遺漏 |

### 風險補齊

| 前次建議新增風險 | 修正後 §11 | 採納判定 |
|----------------|-----------|---------|
| Risk 5：Parser API 簽名斷裂 | ✅ 已加入，含 dual-entry + contract update + fixture verification | ✅ |
| Risk 6：測試基礎設施空白 | ✅ 已加入，F2 作為 mitigation | ✅ |
| Risk 7：Schema 版本分裂 | ✅ 已加入，要求 F1 含 versioning rule | ✅ |
| Risk 8：Hidden critical path delay | ✅ 已加入，明確 manage F1→F2→B→C→D | ✅ |

### 前次計畫書品質評分 vs 修正後

| 維度 | 前次 | 修正後 | 變動 |
|------|------|--------|------|
| 結構清晰度 | ★★★★★ | ★★★★★ | — |
| 定位準確性 | ★★★★★ | ★★★★★ | — |
| 工程規模估計 | ★★☆☆☆ | ★★★★☆ | ↑↑ B 的真實起點已承認；F1/F2 補上基礎工作 |
| 風險完整性 | ★★★☆☆ | ★★★★☆ | ↑ 8 項風險涵蓋結構性與執行層 |
| 驗收可測試性 | ★★★☆☆ | ★★★★☆ | ↑ §9 補充了 3 個 concrete fixtures + 3 個 GUI scenarios + docs:check |
| 關鍵路徑透明度 | ★★☆☆☆ | ★★★★★ | ↑↑↑ 明確的 F1→F2→B→C→D 標示 |
| Cross-repo 治理 | ★★★★★ | ★★★★★ | — |

**採納率：10 項建議中 8 項完整或方向採納，2 項遺漏。整體改善顯著。**

---

## 貳、前次審查的自我修正

### 修正：GUI `src/` 目錄狀態

| 前次審查聲稱 | 二次驗證結果 |
|-------------|------------|
| 「`src/` workbench 在 working tree 中已被刪除，但仍被 Git HEAD 追蹤」 | `src/` 目錄**確實存在**於磁碟上，包含 `App.tsx`（66 KB）、`components/`、`services/`、`types/` 等完整結構；`git status` 顯示 `working tree clean` |

**結論：** 前次審查關於 GUI source tree 不穩定的判斷**不正確**。第一輪探索代理的回報有誤，實際 `src/` 目錄完整存在且 Git 狀態乾淨。

**對計畫的影響：** 修正後計畫 §6B Workstream C 前置條件中仍提及「tracked `src/` workbench 與 working tree 不一致」——此描述現在**不再準確**，應刪除或改寫為確認 `src/` 目錄完整存在。這是正面消息：Workstream C 的前提比預期更健康。

---

## 參、二次驗證發現的新問題

### 🟠 新發現一：`converted-skills/` 中沒有任何 complex skill

二次驗證結果：

- `converted-skills/` 共有 **163 個 skill 目錄**
- **每一個都只含單一 `SKILL.md` 檔案**
- ❌ 無任何 skill 包含 `references/`、`scripts/`、`templates/`、supporting files
- ❌ 無任何 skill 使用 `context: fork` 或 `agent` frontmatter
- ❌ 無任何多檔 skill bundle 可供取用

**對 Foundation F2 的影響：**

計畫 F2 要求「至少 3 個 complex-skill fixtures」。前次審查建議「從 `converted-skills/` 挑選」——但現在確認**沒有可挑選的**。全部 fixtures 必須從零手工建立。

F2 的實際工作量因此包括：

1. **設計** 3-5 個漸進複雜度的 skill 結構（單檔含 frontmatter → 多檔含 references → 含 subagent delegation）
2. **編寫** 完整的 SKILL.md + supporting files（需要對 Claude Skills 官方規格有足夠了解）
3. **定義** 每個 fixture 的 expected parser output
4. **建立** pytest parametrize 或類似機制來跑多 fixture

**建議：** 在 F2 的最低交付描述中，將「至少 3 個 complex-skill fixtures」改為更具體的：

```
1. fixture-simple: 單檔 SKILL.md + rich frontmatter（allowed-tools, context, argument-hint）
2. fixture-multi-ref: SKILL.md + references/ 子目錄 + markdown 內相對連結
3. fixture-delegation: SKILL.md + context: fork + agent 指定 + scripts/ 子目錄
```

### 🟡 新發現二：兩個 repo 的 CI 都沒有 `docs:check`

| Repo | CI 檔案 | 是否含 `docs:check` |
|------|---------|-------------------|
| `skill-0` | `.github/workflows/ci.yml`（165 行） | ❌ 無 |
| `skill-0-GUI` | `.github/workflows/ci.yml`（36 行） | ❌ 無 |

前次審查建議 #9「在 GUI CI 加入 `npm run docs:check`」未被採納。

**風險：** Workstream D（Cross-repo contract closure）的 exit criteria 依賴文件一致性，但目前沒有任何自動化機制在 CI 層面防護漂移。`npm run docs:check` 存在且可用，只是沒被整合進 CI。

**建議：** 在 Workstream D 的主要工作中追加：

```
5. 在 `skill-0-GUI` CI 加入 `npm run docs:check` step
```

這是低成本高收益的變更——script 已存在、CI 已存在、只需加一行。

### 🟡 新發現三：Bridge 的 fallback 品質比預期更好

二次驗證確認 `skill0Bridge.mjs` 有完整的 fallback error handling：

- canonical parser 失敗 → catch → `buildStandaloneParserResult()` + error message
- skill-0 repo 未找到 → standalone mode + 明確 reason string
- 所有失敗路徑都設定 `bridge.error` 且產出結構化 output

**對計畫的影響：** Risk 5（Parser API 簽名斷裂）的實際嚴重度可從 🔴 High 降為 🟠 Medium-High。Bridge 不會「即時斷裂」——它會 graceful degrade 到 standalone mode 並報告錯誤。但 canonical mode 的分析品質仍會受損，因此仍需 dual-entry 策略。

---

## 肆、仍未涵蓋的先前審查風險

修正後計畫的 Workstream A 涵蓋了營運級風險（記憶體壓測、備份 SOP、Python 回歸），但以下三項代碼品質風險仍未出現在任何工作流中：

| 先前審查意見書風險 | 現狀 | 建議歸屬 |
|------------------|------|---------|
| RISK-4：Rate limiter 不讀 `X-Forwarded-For` | 未涵蓋 | Workstream A P1 |
| RISK-5：搜尋端點無 try-catch，異常直接 500 | 未涵蓋 | Workstream A P1 |
| RISK-6：治理操作同步阻塞 event loop | 未涵蓋 | Non-goal（acceptable debt for this phase） |

**建議判定：**

- RISK-4 與 RISK-5 應列入 Workstream A 的 P1 工作項，因為它們直接影響「runtime baseline 可信度」
- RISK-6（治理操作同步阻塞）可歸入 non-goal / known-debt，因為影響範圍僅在大量技能同時操作時觸發，與本階段「最後開發收斂」定位不衝突

---

## 伍、文件狀態標記建議（前次建議 #10）

前次審查建議在文件中明確標註「implemented / designed / planned」三層區分。此建議未被採納，但其重要性在修正後計畫中反而更高——因為：

- `07-complex-skills-analysis-strategy.md`（268 行）= **designed**
- `09-complex-skill-analysis-spec.md`（80+ 行）= **designed**
- `10-complex-skill-risk-schema.md`（80+ 行）= **designed**
- 實際 parser complex skill 支援 = **planned（零實作）**

外部審查方若讀到這三份成熟的設計文件，很容易高估實作完成度。

**最低建議：** 在 Workstream D 的文件收斂工作中，要求每份 dossier 或 spec 文件在頂部加入狀態標記：

```markdown
**Implementation status:** 🟢 Implemented | 🟡 Designed | ⚪ Planned
```

---

## 陸、整體重新評估

### 修正後計畫的優劣彙整

**已解決的結構性問題（前次 4 項核心 → 全部修正）：**

1. ✅ Workstream B 的真實起點不再被模糊化
2. ✅ Schema extension 作為顯式前置步驟
3. ✅ 測試基礎設施明確要求
4. ✅ 關鍵路徑完全透明

**仍需處理的小項（不影響計畫可行性，但應在執行期修正）：**

| # | 項目 | 嚴重度 | 建議處理時機 |
|---|------|--------|------------|
| 1 | Workstream C 前置條件中 `src/` 不穩定描述已不正確 | 🟡 | 下次文件更新時修正 |
| 2 | F2 fixtures 必須全部手工建立（無現成 complex skill） | 🟠 | F2 開始前明確 fixture spec |
| 3 | 兩個 repo CI 都未整合 `docs:check` | 🟡 | Workstream D 執行時補入 |
| 4 | 先前 RISK-4/5 未歸入 Workstream A | 🟡 | Workstream A 開始時追加 |
| 5 | 設計文件缺「implemented / designed / planned」標記 | 🟡 | Workstream D 文件收斂時補入 |

### 最終判定

修正後的計畫書已從「方向正確但需補強」提升至**可作為實際排程與外部審核依據的品質**。

核心改善：

- **工程誠實度大幅提升**：不再掩蓋 Workstream B 的真實規模
- **執行可預測性顯著增加**：F1→F2→B→C→D 關鍵路徑明確，A 獨立並行
- **驗收可測試性從模糊變具體**：3 個 fixture + 3 個 GUI scenario + `docs:check` exit 0
- **風險登記簿從 4 項擴充至 8 項**：涵蓋結構性與執行層風險

上表 5 項殘餘小項均為「執行期可修正」等級，不構成計畫啟動的阻礙。

**本審查建議：修正後計畫可進入執行階段。**

---

*第二輪策略審查意見完*
