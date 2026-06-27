# Skill-0 治理補強與 UniText 對齊開發計畫

日期：`2026-06-19`
文件狀態：`Current follow-up plan / local gates reverified / production restore rehearsal blocked by Docker build TLS`
適用範圍：`<repo-root>`
決策分類：`current-path`

---

## 1. 決策摘要

本計畫延續 `2026-04-27` 外部審計與開發建議書的結論：Skill-0 不應先擴張 corpus 或宣稱 strict equivalence，而應先補齊治理 hardening、release rehearsal、dependency/security evidence、backup/restore、DB identity drift 與 operator-facing telemetry。

本輪新增一個明確邊界：與 UniText、AGENTS、AI runtime governance 類規則對齊時，只做通用治理契約、風險評估、文件與驗收 gate；不直接修改特定專案設定、不重寫本機 runtime path、不針對單一機器或單一 repo 做特殊最佳化。

---

## 2. 本輪實測基線

本節記錄 `2026-06-19` 在目前 checkout 的實測結果。第一批結果揭露與 4 月 current snapshot 的漂移；第二批結果記錄本輪已執行的 P0-B / P0-C 修正與驗收。

| 檢查項目 | 指令 | 結果 |
|---|---|---|
| Git 狀態 | `git status --short --branch` | `main...origin/main [ahead 1]`，本輪 P0/P1 變更仍在工作樹中，待 final review 後提交 |
| Schema validation | `.venv\Scripts\python.exe tools\validate_skill_schema.py parsed` | `196 passed, 0 failed` |
| Docs gate | `.venv\Scripts\python.exe tools\check_doc_status_markers.py` | passed |
| Shared docs gate | `.venv\Scripts\python.exe tools\check_shared_docs.py` | passed，shared source files = `5` |
| DB identity drift | `.venv\Scripts\python.exe tools\report_db_identity_drift.py --allow-missing-db` | warning：`skills_table_missing:skills.db`、`governance_db_missing:governance/db/governance.db`；parsed=`196`、vector=`0`、governance=`0` |
| Python + dashboard API regression | `.venv\Scripts\python.exe -m pytest tests skill-0-dashboard/apps/api/tests -q` | `236 passed, 65 warnings` |
| Dashboard web tests | `npm test -- --run` | `26 passed` |
| Dashboard web build | `npm run build` | passed；Vite `7.3.2`；build time `14.05s` |
| Production compose dry-run before fix | `docker compose --env-file .env.production.example -f docker-compose.prod.yml config` | failed：`env file Q:\Projects\skill-0\.env not found` |
| Web dependency audit before fix | `npm audit --json` | failed：`10` vulnerabilities：`2 low`、`1 moderate`、`6 high`、`1 critical` |
| Web dependency audit after P0-B | `npm audit --json` | passed：`0` vulnerabilities |
| Dashboard web tests after P0-B | `npm test -- --run` | passed：`26 passed` |
| Dashboard web build after P0-B | `npm run build` | passed；Vite `7.3.5` |
| Production compose dry-run after P0-C | `docker compose --env-file .env.production.example -f docker-compose.prod.yml config` | passed；rendered `CORS_ORIGINS=https://your-domain.com` |
| Production compose fail-fast check after P0-C | `docker compose -f docker-compose.prod.yml config` | expected failure：`CORS_ORIGINS` missing |

Reverification update (`2026-06-19`): after resuming this task, the same local gates were rerun against the current working tree. Schema validation, doc gates, Python/API regression, frontend audit/test/build, DB identity drift warning mode, compose dry-run, and compose fail-fast behavior all match the evidence above.

額外觀察：

1. 目前 shell Node 是 `v24.14.1`，repo `.nvmrc` 是 `20.19.0`。測試在 Node 24 通過，但不能取代 Node 20.19 的 CI/runtime 基準。
2. P0-B 已把 `npm audit` 收斂回 `0 vulnerabilities`，並保留前端 test/build 綠燈。
3. P0-C 已讓 `.env.production.example` 可作為 dry-run fixture，同時保留無 env 時的 `CORS_ORIGINS` fail-fast。

---

## 3. UniText 與系統治理對齊邊界

本計畫採用以下角色分工：

| 系統 | 建議角色 | 不做事項 |
|---|---|---|
| UniText | canonical registry、runtime projection、skill governance backbone | 不把 Skill-0 變成 UniText runtime 的設定管理器 |
| Skill-0 | skill decomposition、schema validation、semantic search、governance sidecar data layer | 不直接接管 UniText registry、runtime path、agent config |
| AGENTS / repo rules | repo-local workflow、測試、文件與安全約束 | 不把全域規則複製成 repo 專屬例外 |
| AI runtime governance | simulation-first、backup、audit log、rollback contract | 不在本輪執行 `-Apply` 類設定變更 |

### 3.1 通用治理原則

1. 只建立 portable contract，不寫死 `C:\Dev\AI_UNIFIED`、`Q:\UniText` 或使用者機器的 runtime path 作為產品假設。
2. 對外交換只透過 artifacts：skill source、parsed JSON、schema validation report、governance/audit report、identity drift report。
3. 所有 config/path 變更若未來需要執行，必須先有 risk level、simulation output、backup evidence、rollback command。
4. Skill-0 可以消費 UniText registry export，但不能假設 UniText 一定存在於部署環境。
5. 文件對齊應採「authority index + status marker + drift check」，避免跨 repo 重複規範造成互相漂移。

### 3.2 相容性風險

| 風險 | 說明 | 最佳解法 |
|---|---|---|
| Authority duplication | UniText 與 Skill-0 都可能描述 skill lifecycle | 用角色分工文件定義 source-of-truth，而不是互相複製規則 |
| Path coupling | 本機路徑可能被誤寫成產品需求 | 文件與 schema 使用 `<repo-root>`、`<registry-root>` placeholder |
| Hidden config mutation | runtime governance 工具可修改多個 AI tool 設定 | 本計畫只允許 read-only inventory / simulation，任何 apply 另開明確任務 |
| Drift between registry and parsed corpus | UniText registry 更新後，Skill-0 parsed/index 未同步 | 建立 import snapshot + checksum + drift report，而不是 live coupling |
| Context budget bloat | 把所有 governance 規則灌進入口文件會增加 agent 初始上下文 | 使用權威索引與最小入口摘要，細節放 reference docs |
| Public/private boundary | planning、runtime path、local governance 報告不一定適合 public remote | public docs 只保留可泛化規則；local-only evidence 放 ignored output 或明確標記 |

---

## 4. 工作流與交付

### P0-A：修正現行 evidence drift

目標：讓 current docs 不再宣稱已被今天實測否定的狀態。

交付：

1. 更新 document authority index，加入本計畫。
2. 把 `npm audit`、production compose dry-run、Node runtime mismatch 記為 current drift。
3. 不修改 dependency、Docker、Node 或 runtime 設定，只記錄可驗證事實與下一步 gate。

驗收：

```powershell
.venv\Scripts\python.exe tools\check_doc_status_markers.py
.venv\Scripts\python.exe tools\check_shared_docs.py
```

### P0-B：Dependency security remediation plan

狀態：`Completed on 2026-06-19`

目標：把 `npm audit` 從 drift 轉成可執行修復隊列。

交付：

1. 已升級 direct dependencies：`axios`、`react-router-dom`、`vite`、`vitest`、`@vitejs/plugin-react`。
2. 已用 npm `overrides` 收斂 transitive advisories：`@babel/core`、`brace-expansion`、`esbuild`、`form-data`、`undici`。
3. 分類 runtime exposure：browser-only、dev-server-only、test-only、Node adapter path。
4. 優先安全 bump，不做大型 frontend refactor。

驗收：

```powershell
cd skill-0-dashboard\apps\web
npm audit --json
npm test -- --run
npm run build
```

P0 完成證據：

```powershell
npm audit --json
# 0 vulnerabilities

npm test -- --run
# 26 passed

npm run build
# passed, Vite 7.3.5
```

### P0-C：Production compose env contract 修正

狀態：`Completed on 2026-06-19`

目標：讓 release rehearsal 的 dry-run 可重現，且不依賴誤放 `.env`。

交付：

1. 已將 service-level `env_file: .env` 改為 `required: false`。
2. 已保留 `${CORS_ORIGINS:?Set CORS_ORIGINS to the production origin list}` fail-fast。
3. 已新增 compose config dry-run 驗收證據。
4. 已驗證沒有 env 時仍會因 CORS 缺值失敗。

驗收：

```powershell
docker compose --env-file .env.production.example -f docker-compose.prod.yml config
```

P0 完成證據：

```powershell
docker compose --env-file .env.production.example -f docker-compose.prod.yml config
# passed; rendered CORS_ORIGINS=https://your-domain.com

docker compose -f docker-compose.prod.yml config
# expected failure: required variable CORS_ORIGINS is missing a value
```

### P1-A：Governance worker 與 telemetry hardening

狀態：`Current baseline verified on 2026-06-19`

目標：補足 operator 能決策的治理訊號，而不是只顯示 queued/running/completed。

交付：

1. 已確認 worker claim / lease / heartbeat 狀態在 API response 與 UI 中可見：`claimed_by`、`lease_expires_at`、`active_workers`、`active_lease_expires_at`、`last_item_started_at`。
2. 已確認 retry lineage 顯示 `retry_of_item_id`、`attempt_number`、`max_attempts`。
3. 已確認 cancel trace 顯示 `cancelled_at`、`cancelled_by` 與 `JOB_CANCELLED` error code；目前沒有獨立 `cancel_reason` 欄位，原因收斂在 `error_message`。
4. 已確認 failure code 對應 `suggested_next_step`。

驗收：

```powershell
.venv\Scripts\python.exe -m pytest skill-0-dashboard/apps/api/tests/test_governance.py skill-0-dashboard/apps/api/tests/test_skills.py -q
cd skill-0-dashboard\apps\web
npm test -- --run src/pages/ReviewQueue.test.tsx src/pages/SkillDetail.test.tsx
```

P1-A 證據：

1. `skill-0-dashboard/apps/api/schemas/action.py` 定義 `ActionJobSummary` 與 `ActionJobItem` telemetry 欄位。
2. `skill-0-dashboard/apps/web/src/api/types.ts` 保持前端型別同步。
3. `SkillDetail.tsx` 與 `ReviewQueue.tsx` 顯示 worker、lease、retry、cancel 與 suggested next step。
4. API 與 web 測試已覆蓋 queued/running/retry/cancel telemetry。

### P1-B：Backup / restore 與 DB identity rehearsal

狀態：`Local SQLite smoke executed on 2026-06-19; production compose attempted; API image build blocked by PyTorch TLS certificate chain`

目標：把雙 SQLite 架構從「知道有風險」推進到「有可演練回復程序」。

交付：

1. 已確認 `docs/operations-runbook.md` 包含 `skills.db` 與 `governance.db` 備份/還原 SOP。
2. 已新增 `docs/backup-restore-identity-rehearsal-2026-06-19.md` 作為本輪 rehearsal evidence。
3. 已將 bash maintenance scripts 正規化為 LF，並通過 `bash -n`。
4. 已為 backup/health scripts 加入 Python sqlite fallback，避免要求 Windows developer machine 安裝全域 `sqlite3` CLI。
5. 已用 disposable WSL `/tmp` 兩個 SQLite DB 跑過 backup + health smoke，並驗證兩個 backup DB 可讀。
6. 已驗證 public checkout identity drift report 的 expected warning。
7. 已新增 `scripts/rehearse_prod_compose.ps1`，讓 production compose / named-volume rehearsal 可用單一命令重跑。
8. named volume backup/restore smoke test 已啟動 compose build，但 API image 在 PyTorch CPU wheel index 遇到 TLS certificate chain 錯誤，未假裝完成。

驗收：

```powershell
.venv\Scripts\python.exe tools\report_db_identity_drift.py --allow-missing-db
```

P1-B 證據：

```bash
bash -n scripts/backup_db.sh
bash -n scripts/check_db_health.sh
bash -n scripts/daily_maintenance.sh
```

```bash
# Disposable WSL temp DB smoke:
# backup_files=2
# governance_*.db=ok
# skills_*.db=ok
```

```powershell
.venv\Scripts\python.exe tools\report_db_identity_drift.py --allow-missing-db --format json
# status=warning; parsed=196; vector=0; governance=0; missing runtime DB warnings expected
```

P1 完成條件：local/public checkout 與 production rehearsal 對 DB 缺席有不同、明確、可驗證的判準。完整 production completion 仍需 named-volume restore smoke test。

### P1-C：UniText alignment artifact

狀態：`Completed on 2026-06-19`

目標：建立跨系統相容契約，而不是修改任一特定 runtime 設定。

交付：

1. 已新增 `docs/skill-0-unitext-alignment.md`：定義 UniText / Skill-0 / AGENTS / runtime governance 分工。
2. 已定義 read-only import contract：UniText registry export -> Skill-0 parse/index/review。
3. 已定義 governance change contract：任何未來 config/path change 必須有 simulation、backup、rollback、audit log。
4. 已定義 drift check proposal：registry snapshot checksum vs parsed artifact checksum。

驗收：

```powershell
.venv\Scripts\python.exe tools\check_doc_status_markers.py
.venv\Scripts\python.exe tools\check_shared_docs.py
```

---

## 5. 不做事項

1. 不在本輪修改 `Q:\UniText`、`C:\Dev\AI_UNIFIED`、Codex、Claude、Gemini、VS Code、Windsurf 等 runtime 設定。
2. 不執行 AI runtime governance 的 `-Apply` 類指令。
3. 不把 UniText path 或本機 config 寫成 Skill-0 產品必要條件。
4. 不在 dependency audit 未收斂前擴張 20-skills corpus。
5. 不把 fidelity、similarity、coverage 宣稱為 strict equivalence。
6. 不做大型 queue/worker 架構替換；先補 evidence、lease discipline 與 operator telemetry。

---

## 6. 建議執行順序

1. P0-A：已更新權威索引與本計畫，關閉文件 evidence drift。
2. P0-B：已處理 web dependency audit，`npm audit --json` 回到 `0 vulnerabilities`。
3. P0-C：已修正 production compose dry-run，使 release rehearsal 可重現。
4. P1-A：已確認 governance operator telemetry 與 worker state 可視性。
5. P1-B：已建立 backup/restore 與 DB identity rehearsal artifact；production named-volume restore smoke test 待 controlled compose environment。
6. P1-C：已補 UniText alignment artifact，保持 read-only / portable / no runtime mutation。

---

## 7. 最小成功定義

下一輪完成後，至少要滿足：

1. `npm audit` high/critical 歸零，或全部有 exposure-based deferral。
2. production compose config dry-run 在乾淨 checkout 可通過。
3. Python/API regression 與 dashboard web test/build 持續通過。
4. governance job telemetry 足以讓 reviewer 判斷「失敗原因、重試脈絡、目標 revision、下一步」。
5. UniText 對齊以通用契約呈現，不引入特定機器 path 或 runtime mutation。
6. document authority index 指向本計畫，且舊 snapshot 不再被誤讀為今天的狀態。
