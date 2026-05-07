# Skill-0 Benchmark Plan

更新日期：2026-05-07

## 目的

建立 Skill-0 的解析與搜尋評估基準，避免只用「相似」、「等價」或 demo 查詢描述品質。此計畫回應 `docs/skill-0_issue-log.md` 中的兩個核心風險：

- 語意搜尋目前偏向通用 embedding，缺少 domain ground truth。
- 等價性測試若只比較框架可表達的內容，容易形成循環論證。

## 評估對象

| 對象 | 問題 | 評估方式 |
|---|---|---|
| Parser classification | `Action / Rule / Directive` 邊界漂移 | 標註樣本與分類 confusion matrix |
| Skill coverage | 工具型 Skill 適配較佳，指南型與工作流型較弱 | 分層抽樣 coverage report |
| Semantic search | 通用 embedding 未證明 domain retrieval 品質 | 查詢集、人工標註 relevance、precision/recall/F1 |
| Equivalence/fidelity | 等價性可能只驗證已建模部分 | 行為任務、缺失資訊標註、fidelity wording |

## Ground Truth 設計

建立 `benchmarks/` 或 `tests/fixtures/` 下的評估資料時，至少包含：

1. Skill 原文或穩定 fixture。
2. 人工標註的 expected actions/rules/directives。
3. 可接受的替代表述。
4. 查詢與 relevant skill IDs。
5. 不可判定或框架無法表達的項目。

標註原則：

- 不把 parser 目前輸出當作 ground truth。
- 不因 schema 沒有欄位就忽略原文的重要行為。
- 對指南型、工作流型、授權/安全型 Skill 分開計算結果。

## 指標

| 指標 | 用途 | 最小報告要求 |
|---|---|---|
| Precision@k | 搜尋結果前 k 筆是否相關 | k=3、k=5、k=10 |
| Recall@k | 是否找回已知 relevant skills | k=5、k=10 |
| F1 | 搜尋或分類的整體平衡 | 依分層樣本報告 |
| Classification accuracy | ARD 分類是否符合人工標註 | 需列出主要混淆類型 |
| Coverage ratio | 原文重要行為被捕捉比例 | 區分 captured、partial、missing |
| Unsupported behavior count | 框架無法表達的內容 | 需回饋到 failure-case analysis |

## 第一批查詢集

| 類型 | 查詢例 | 目的 |
|---|---|---|
| 工具操作 | `parse markdown skill references` | 驗證工具型 Skill retrieval |
| 工作流程 | `run test before commit and report blockers` | 驗證 workflow Skill retrieval |
| 安全治理 | `detect prompt injection in skill instructions` | 驗證 security/governance retrieval |
| 文件維護 | `update docs when code changes` | 驗證 documentation workflow retrieval |
| MCP runtime | `mcp server missing binary recovery` | 驗證 runtime dependency retrieval |

## 實作順序

1. 從 `converted-skills/` 抽樣至少 20 個 Skill，覆蓋工具型、指南型、工作流型、安全型。
2. 建立人工標註表與查詢集。
3. 新增 benchmark runner，輸出 JSON 與 Markdown summary。
4. 將 unsupported behavior 回填到 `docs/failure-case-analysis.md`。
5. 只有 benchmark 指標支持時，才使用強等價措辭；否則使用 fidelity 或 similarity。

## 驗收標準

- 每次 benchmark 可重跑並輸出穩定格式。
- 報告至少包含分層 precision/recall/F1。
- 報告列出失敗案例，而不是只給總分。
- 指標結果可連回具體 Skill ID、query、expected relevance。

## 驗證入口

初期文件階段：

```bash
git diff --check
.venv/bin/python tools/check_doc_status_markers.py
```

實作 benchmark runner 後，新增專用測試命令與 fixtures。
