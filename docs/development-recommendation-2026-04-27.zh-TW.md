# Skill-0 開發建議書

日期：`2026-04-27`
Repo：`<repo-root>`
文件狀態：`Reviewed / external-agent blockers addressed`
依據文件：`docs/external-agent-audit-synthesis-2026-04-27.zh-TW.md`
執行模式：`project-development-loop / 8HR`

---

## 1. 決策摘要

本建議書採納 4 名外部代理獨立審計與 2 名外部代理建議書審查後的共同結論：Skill-0 的方向是正面的，但下一階段不應直接擴大 skill corpus 或宣稱 strict equivalence。正確路線是先把現有能力變成可被外部 reviewer、operator、pilot user 信任的證據鏈。

本輪 8 小時開發採用 `Must / Should / Stretch` 控制過度承諾：

1. **Must**：修補 scan HTML export escaping、production CORS compose 覆蓋風險、README / authority index 漂移、Dependabot vulnerability 盤點。
2. **Should**：擴充既有 fixture-based fidelity gate，補 governance operator telemetry 的 reviewer-facing 欄位與 copy。
3. **Stretch**：release rehearsal runbook、DB identity drift report、完整 regression / push。

---

## 2. 目前基線

最新可驗證基線如下：

| 項目 | 狀態 |
|---|---|
| Branch | `main` |
| Remote sync | `origin/main` 已更新到 `1ba22a5` |
| parsed corpus | `196` checked-in JSON |
| converted-skills corpus | `164` directories |
| schema validation | `196 passed, 0 failed` |
| Python + dashboard API regression | `219 passed` |
| dashboard web tests | `26 passed` |
| dashboard web build | passed |
| GitHub security signal | push 後回報 `6` 個 Dependabot vulnerabilities（`2 high`, `4 moderate`） |

本基線代表 Skill-0 已具備可執行工程骨架；但 Dependabot warning、HTML export escaping、fixture-based fidelity gate 與 release rehearsal 仍是下一階段信任門檻。

---

## 3. 開發原則

1. 不以新增功能數量衡量進度，以「可信證據鏈」衡量。
2. 不把 `fidelity`、similarity、coverage 描述為 strict equivalence。
3. 不在 fixture-based fidelity gate 建立前擴張大量 skill corpus。
4. 不把 production readiness 建立在未演練的 compose/env 假設上。
5. 不讓入口文件與 authority index 繼續使用錯誤路徑或舊數字。
6. 每個 stage 必須有驗證命令或可審查文件輸出。

---

## 4. 外部審查處置

本建議書初稿經 2 名外部代理只讀審查，已採納以下 blocker / should-fix：

| 審查意見 | 處置 |
|---|---|
| 8HR loop 缺少外部持久 state，不能直接啟動 | 新增第 8 節，指定 `output/project-development-loop/state.json`、checkpoint cadence 與 state schema |
| Stage D 2 小時承諾 full release rehearsal / full regression / push 過度 | Stage D 改為 risk inventory + compose config dry-run + runbook stub，完整 compose up / full regression / push 改為 stretch |
| CORS compose 覆蓋 `.env` 風險應提前 | Stage A 加入 production CORS compose 修正與 `docker compose -f docker-compose.prod.yml config` 驗收 |
| Stage B 未驗新 fixture gate | Stage B 改為擴充既有 `tests/fixtures/complex_skills` 與 `tests/test_complex_skill_parser.py` |
| HTML export 安全項目不夠具體 | Stage A 明列 `html.escape`、URL allowlist、`rel=\"noopener noreferrer\"`、CSS class enum、惡意輸入測試斷言 |
| Dependabot warning 未閉合 | Stage A 加入 6 個 vulnerability 來源盤點、direct/transitive 分類、safe bump / deferral reason |
| Governance telemetry acceptance 不夠明確 | Stage C 加入 response fields 與 UI visibility acceptance |

---

## 5. 8 小時執行分段

### Stage A：Must - 安全與文件信任硬化

時間目標：`0-2.5h`

交付：

1. 修補 `skill-0-dashboard/apps/api/routers/scans.py` 的 HTML export escaping / sanitization。
2. 所有 text node 使用 `html.escape`；HTML attribute / URL context 不直接插入 raw input。
3. `standard_url` 僅允許 `http` / `https`，輸出連結加上 `rel=\"noopener noreferrer\"`。
4. CSS class suffix 僅允許固定 enum，不接受 finding payload 直接決定 class name。
5. 新增 API regression test，斷言輸出不含 raw `<script`、`onerror=`、`javascript:`。
6. 修正 `docker-compose.prod.yml` 不以空字串覆蓋 `.env.production.example` 的 `CORS_ORIGINS`。
7. 以 `docker compose -f docker-compose.prod.yml config` 驗證 production compose config 可解析，且 CORS 不被空字串覆蓋。
8. 修正 README 的 parsed/test count 與現行基線不一致問題。
9. 修正 authority index 中 current baseline / review artifacts 的舊絕對路徑。
10. 盤點 GitHub push warning 提到的 6 個 Dependabot vulnerabilities：列出來源、direct/transitive、safe bump 候選、需要延期時的 deferral reason。

驗收：

```bash
.venv/bin/python -m pytest skill-0-dashboard/apps/api/tests tests/test_doc_checks.py -q
.venv/bin/python tools/check_doc_status_markers.py
docker compose -f docker-compose.prod.yml config
rg -n "<repo-root>" docs/document-authority-index-2026-03-27.md README.md
git diff --check
```

### Stage B：Should - Fixture-Based Fidelity Gate 初版

時間目標：`2.5-4.5h`

交付：

1. 擴充既有 `tests/fixtures/complex_skills` 與 `tests/test_complex_skill_parser.py`，不要平行新增另一套 fixture 格式。
2. 補 3-5 個代表性 fixture 或 expected assertion，覆蓋 provenance、complex decomposition、known failure notes。
3. 文件明確說明這是 fixture-based fidelity gate，不是 strict equivalence proof。
4. 如需新增 CLI，名稱採 `tools/validate_parser_quality_fixtures.py`，但不以新 CLI 阻塞初版落地。

驗收：

```bash
.venv/bin/python -m pytest tests/test_complex_skill_parser.py tests/test_schema_contract.py tests/test_auto_parse.py -q
.venv/bin/python tools/validate_skill_schema.py parsed
```

### Stage C：Should - Governance Operator Telemetry

時間目標：`4.5-6.5h`

交付：

1. 不重做底層 job runner；優先把已存在的 job/item fields 轉成 reviewer-facing report / API response / UI copy。
2. API response 或 serialized report 必含：`target_revision_id`、`attempt_number`、`max_attempts`、`claimed_by`、`lease_expires_at`、`retry_of_item_id`、`error_code`、`suggested_next_step`。
3. Cancel trace 若現有 schema 不支援 `cancelled_at/by`，本輪至少文件化缺口並避免假裝已完成。
4. UI 測試覆蓋 retry lineage 與 cancel trace / cancellation reason 可見，或在無 UI 時提供 API snapshot assertion。

驗收：

```bash
.venv/bin/python -m pytest skill-0-dashboard/apps/api/tests/test_governance.py skill-0-dashboard/apps/api/tests/test_skills.py -q
cd skill-0-dashboard/apps/web && npm test -- --run src/pages/ReviewQueue.test.tsx src/pages/SkillDetail.test.tsx
```

### Stage D：Stretch - Release Rehearsal 與 Loop Handoff

時間目標：`6.5-8h`

交付：

1. 建立 release rehearsal risk inventory，不承諾完整 production deployment。
2. 補 production compose config dry-run evidence 或 runbook stub。
3. 檢查 `.env.production.example` placeholder fail-fast、CORS、auth、healthcheck、DB volume persistence 的明確風險。
4. 建立 `skills.db` / `governance.db` identity drift report 的後續工作項。
5. 寫 stage completion report。
6. 若時間足夠才跑 full regression、commit、push；否則保留乾淨 stage boundary 與明確 next action。

驗收：

```bash
docker compose -f docker-compose.prod.yml config
.venv/bin/python tools/check_doc_status_markers.py
.venv/bin/python tools/check_shared_docs.py
.venv/bin/python tools/check_shared_docs_mirror.py --gui-root <skill-0-gui-root> --require-gui-root
git status --short
```

Stretch 驗收：

```bash
.venv/bin/python -m pytest tests skill-0-dashboard/apps/api/tests -q
cd skill-0-dashboard/apps/web && npm test -- --run && npm run build
git push origin main
```

---

## 6. 不做事項

本輪 8 小時不做：

1. 大規模 20-skills expansion。
2. production deployment。
3. secret rotation。
4. 大型 queue / worker 架構替換。
5. 大型 dashboard redesign。
6. strict equivalence 宣稱或對外 benchmark 結論。

---

## 7. Dirty State 與 Commit 規則

1. 開始每個 stage 前先看 `git status --short`。
2. Dirty state 只允許本輪文件、測試、程式變更；若出現不相關變更，先停下標記，不混入 commit。
3. 每個 commit 必須是可描述的單一主題，例如 `fix: escape scan html export`、`docs: align current development plan`。
4. 若 full regression 未跑完，commit message 或 stage report 必須寫明驗證範圍。
5. Remote push 可用時才 push；若 GitHub auth 或 branch protection 擋住，不阻塞本地 loop，但要在 stage report 標記。

---

## 8. Loop State 啟動規格

`project-development-loop / 8HR` 必須有 repo-local 持久狀態，不依賴模型 session 記憶。

State 檔案：

```text
output/project-development-loop/state.json
```

最低欄位：

```json
{
  "mode": "project-development-loop",
  "duration_hours": 8,
  "started_at": "<ISO-8601>",
  "deadline_at": "<ISO-8601>",
  "active_stage": "Stage A",
  "last_checkpoint": "development recommendation reviewed",
  "next_intended_action": "start Stage A HTML export and CORS hardening",
  "status": "running"
}
```

Checkpoint cadence：

1. 每個 stage 開始時更新 `active_stage` 與 `next_intended_action`。
2. 每個 stage 驗證後更新 `last_checkpoint`。
3. 遇到 blocker 時將 `status` 改為 `blocked`，並寫入 `blocker`。
4. 到 8 小時 deadline 或停止時將 `status` 改為 `completed` 或 `paused`。

State 檔案屬本地執行狀態，不納入 commit；若需要保留可審查摘要，寫入 `docs/` 的 stage report。

---

## 9. Loop 啟動條件

進入 `$project-development-loop 8HR` 前必須成立：

1. 已 push 現有審計與報告 commit。
2. 本建議書已被外部代理審查。
3. blocker 級審查意見已修正。
4. repo 工作區乾淨或 dirty state 已明確屬於本輪建議書修正。
5. `output/project-development-loop/state.json` 已建立。
