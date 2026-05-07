# Review To Development Plan

更新日期：2026-05-07

## 來源與目的

本計畫將 `docs/skill-0_issue-log.md` 中的 conceptual review 問題轉成可執行的開發主線。它不取代既有 `docs/planning/` 文件，而是作為 issue-log 匯入後的任務分流表。

## 工作主線

| 主線 | 問題來源 | 近期產出 | 完成條件 |
|---|---|---|---|
| 理論基礎 | `Action / Rule / Directive` 邊界與完備性不足 | 分類判準、反例清單、schema 變更門檻 | 新 schema 欄位必須能對應至少一個已標註失敗案例 |
| 解析品質 | 指南型與工作流型 Skill 描述力不足 | 失敗案例抽樣、解析錯誤分類、fixtures | 每類主要錯誤至少有 fixture 與 regression test |
| 搜尋評估 | 通用 embedding 缺少 domain benchmark | ground truth、precision/recall/F1 報告 | 搜尋品質以 benchmark 數字描述，不用泛稱等價 |
| 治理安全 | regex scan 只能覆蓋表層風險 | 風險分類、人審節點、事件回饋流程 | 高風險項目不可只有自動核准，需留審查紀錄 |
| 文件同步 | README、評估報告與資料狀態可能漂移 | authority index、文件狀態檢查、更新節奏 | current-facing docs 可通過 doc status checks |

## P0：恢復寫入與工具基線

1. 確認 Local Project Files / MCP runtime 的 `git` 可用。
2. 重新測試 `fs_mkdir windows-projects:skill-0`。
3. 如果目標根目錄不在 Git worktree 內，調整工具層 outside-git-repo 寫入策略。
4. 驗證失敗時依 `docs/AGENTS.md` 的 Test Stage Guard 暫停，不自行安裝或繞過。

驗收：

- MCP runtime 中 `git --version` 可成功執行。
- `windows-projects:skill-0` 可建立或能明確回報非 Git 根目錄政策。
- 寫入失敗時有可追溯的 blocker 記錄。

## P1：將 conceptual review 轉成 repo-native 工作

1. 以 `docs/failure-case-analysis.md` 抽樣失敗或低信心 Skill。
2. 以 `docs/benchmark-plan.md` 定義搜尋與等價性評估基準。
3. 以 `docs/governance-hardening-plan.md` 收斂安全與審查流程。
4. 將結論回填到 `docs/planning/` 中的 live plan，而不是讓本文件成為孤立報告。

驗收：

- 每個採納項目都能追到 issue-log 原始問題。
- 每個工程項目都有測試或文件檢查入口。
- 不新增 schema 欄位，除非已有失敗案例與驗收測試。

## P2：Context Pack

後續若仍需匯出到 `windows-projects:skill-0`，建立 context pack：

- `ai-context-export/PROJECT_SUMMARY.md`
- `ai-context-export/CURRENT_STATE.md`
- `ai-context-export/TODO.md`
- `ai-context-export/NEXT_AGENT_PROMPT.md`

目前本 repo 的 source of truth 仍是 WSL checkout：`/home/miles/dev2/projects/skill-0`。

## 驗證

本文件更新後至少執行：

```bash
git diff --check
.venv/bin/python tools/check_doc_status_markers.py
.venv/bin/python tools/check_shared_docs.py
```

若上述命令缺少必要 dependency，依 Test Stage Guard 停止該驗證線並回報缺項。
