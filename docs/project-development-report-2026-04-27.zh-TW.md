# Skill-0 專案開發報告

日期：`2026-04-27`
Repo：`<repo-root>`
Branch：`main`
報告類型：`project-development-loop maintenance report`

---

## 1. 本輪目的

本輪工作不是開啟新功能分支，而是把目前專案開發狀態整理成可追溯的報告，並用實際驗證結果校準 `docs/planning/executable-dev-plan-2026-03-31.zh-TW.md` 的現行基線。

本報告採用以下證據來源：

1. repo instructions：`AGENTS.md`
2. 現行執行入口：`docs/planning/executable-dev-plan-2026-03-31.zh-TW.md`
3. 改善計畫：`docs/project-improvement-plan-2026-03-27.zh-TW.md`
4. 本輪本機驗證命令輸出

---

## 2. 現況摘要

Skill-0 目前已從 prototype 階段推進到「可驗證的治理與搜尋基線」階段。核心 contract、revision-aware governance、fidelity wording、dashboard reviewer flow、以及文件漂移防護都已有可執行實作與測試覆蓋。

目前主線狀態：

| 面向 | 狀態 | 判斷 |
|---|---|---|
| Canonical schema contract | 已落地 | `schema/skill-decomposition.schema.json` 為 live source of truth，`parsed/` 本輪驗證全數通過 |
| Parsed corpus | 穩定 | `196` 個 checked-in parsed JSON，schema validation `196 passed, 0 failed` |
| Imported skill corpus | 穩定 | `converted-skills/` 目前 `164` 個目錄 |
| Core API / runtime | 穩定但需維護 | `/health` 已維持 cheap path；search failure path 已有 graceful contract |
| Governance | durable MVP 已落地 | revision-aware storage、async jobs、retry/cancel/lease/heartbeat 基線已存在 |
| Dashboard web | 穩定 | React/Vite test suite 與 production build 本輪通過 |
| Docs governance | 穩定 | status marker、shared docs source set、GUI mirror drift check 本輪通過 |

---

## 3. 本輪驗證結果

本輪在 `2026-04-27` 重新跑過以下基線：

```bash
rg --files parsed -g '*.json' | wc -l
find converted-skills -mindepth 1 -maxdepth 1 -type d | wc -l
.venv/bin/python tools/validate_skill_schema.py parsed
.venv/bin/python tools/check_doc_status_markers.py
.venv/bin/python tools/check_shared_docs.py
.venv/bin/python tools/check_shared_docs_mirror.py --gui-root <skill-0-gui-root> --require-gui-root
.venv/bin/python -m pytest tests skill-0-dashboard/apps/api/tests -q
npm test -- --run
npm run build
```

結果：

| 驗證項目 | 結果 |
|---|---|
| parsed JSON count | `196` |
| converted-skills directory count | `164` |
| schema validation | `196 passed, 0 failed` |
| doc status markers | passed |
| shared docs source-set check | passed |
| shared docs GUI mirror check | passed |
| Python + dashboard API regression | `219 passed, 60 warnings` |
| dashboard web tests | `26 passed` |
| dashboard web production build | passed |

---

## 4. 開發進度判斷

### 已完成並可視為基線

1. `CP-01` worktree 收斂已完成，主線已不再處於大規模混雜變更狀態。
2. `CP-02` governance async job durable MVP 已完成，剩餘工作屬 hardening。
3. `CP-03` runtime 風險主項已補齊，剩餘工作屬觀測性與部署邊界維護。
4. `CP-04` docs drift gate 已可實際執行，包含 shared docs 與 cross-repo mirror 檢查。
5. `CP-05` 主要歷史計畫文件已降級為 historical context，現行入口明確。
6. `CP-06` 20-skills 擴展已改為 gated backlog，不再提前啟動。
7. `CP-07` 本輪回歸驗證已完成。

### 仍需推進

1. Governance job telemetry 還可以更完整，尤其是 operator-facing 的失敗原因、耗時、重試路徑與 cancel trace。
2. `skill-0-GUI` 是否要在自己的 workflow 內獨立執行 shared docs mirror gate，仍是跨 repo governance 的下一個決策點。
3. Runtime hardening 後續應集中在觀測性、部署假設與錯誤分類，而不是重新設計 API。
4. Parser quality 的 ground truth / failure corpus 仍不足；在沒有 benchmark 前，不應把 fidelity 分數描述成 strict equivalence。

---

## 5. 下一輪建議

建議下一輪採用 maintenance-first 順序：

1. 補 governance action job telemetry 報告面，避免 reviewer 只能看到 terminal status。
2. 將 shared-doc governance gate 的責任邊界文件化到 `skill-0` 與 `skill-0-GUI` 兩側。
3. 選一個小型 parser quality fixture，建立可回歸的 failure corpus，而不是直接擴大 20-skills 匯入。
4. 外審前再跑一次完整驗證：schema、doc gates、Python regression、web tests/build。

---

## 6. Commit Hygiene

本輪發現 repo root 有一個空的未追蹤 `.codex` 檔案。該檔案沒有內容，也不是專案產物，因此本輪將 `.codex` 加入 `.gitignore`，避免本機 agent artifact 污染後續 commit 狀態。
