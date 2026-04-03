# Skill-0 現階段可執行開發計畫（YOLO 模式）

更新日期：`2026-04-03`  
文件狀態：`Working v0.5`  
適用範圍：`/home/miles/dev2/skill-0`  
協作模式：主代理（全局監察/決策整合） + 子代理 5.3（文件落地/細節修編）

Status note: `2026-04-02` 已完成 worktree 收斂主線，CP-01 可視為完成；本文件目前作為後續 checkpoint 的現行執行入口，而非 2026-03-31 當下的未整理快照。

---

## 1. 文件目的

本文件將目前 repo 內「尚未完成 / 待執行 / 待對齊」事項，轉為可直接執行的 checkpoint 計畫，供主代理持續推進與整合驗證。

本計畫優先遵循：

1. `docs/document-authority-index-2026-03-27.md` 的權威文件分層
2. `docs/project-improvement-plan-2026-03-27.zh-TW.md` 的 P0/P1/P2 主軸
3. `docs/remaining-worktree-triage-2026-03-27.md` 的實務分支拆分建議

---

## 2. 現況盤點（未完成 / 待執行 / 待對齊）

### 2.1 未完成主線（高優先）

1. **Worktree 收斂主線已完成，僅剩尾端殘項待清理**
   - 現況：原本混雜的 `parsed/`、dashboard、docs 已拆成 4 個 commit；目前只剩 `parsed/agent-skills-skill.json` 與少量 process docs 未收束
   - 來源：`docs/remaining-worktree-triage-2026-04-02.md`

2. **Governance Phase 2 durable MVP 已落地，剩餘工作轉向 hardening**
   - 現況：dashboard API 與主要 UI 已接上批次 scan/test 非同步 job、job/item 狀態查詢與 retry；job/item state 現在持久化到 `governance.db`，service 啟動時會自動回收 queued/running job 並重啟未完成項目
   - 來源：`docs/planning/governance-phase2-pending.md`

3. **Runtime 核心風險已補齊，剩餘工作轉向長尾 hardening**
   - 現況：trusted proxy aware client IP extraction 與搜尋端點統一 graceful `503` 已落地；後續主要是觀測性、部署邊界與回歸維護
   - 來源：`docs/review-opinion-2026-03-23.md`、`docs/final-phase-plan-review-round2-2026-03-23.md`

4. **CI 文件漂移防護仍需擴充**
   - 現況：`docs-status` 與 shared-doc drift gate 已落地，但尚未涵蓋 owner discipline、跨 repo mirrored docs drift 與更嚴格的來源責任邊界
   - 來源：`docs/final-phase-plan-review-round2-2026-03-23.md` + 本輪落地結果

5. **舊計畫與新基線對齊尚未完全收束**
   - 現況：本輪已為主要舊計畫補上 historical status note，但仍需持續清查其他歷史文件是否誤被當成現行排程依據
   - 來源：`docs/planning/plan.md`、`docs/planning/plan-20-skills.md`、`docs/contract-decision.md`、`docs/document-authority-index-2026-03-27.md`

### 2.2 已完成但需維持的基線

1. Canonical contract（`v2.4.0`）已建立與驗證  
2. Revision-aware governance 已落地（P0）  
3. fidelity/equivalence 語義分流已啟動  
4. Node `20.19.0` 與前端測試建置基線已形成

### 2.3 最新驗證事實（截至 2026-04-03）

以下事項已由主代理在本地重新驗證，可作為本計畫的最新證據基線：

1. `parsed/` 目前共有 `196` 個 checked-in JSON。  
2. `converted-skills/` 目前共有 `164` 個目錄。  
3. Python 測試收集數量為 `201`，最近一次完整回歸結果為 `201 passed`。  
4. Dashboard web 測試結果為 `24 passed`。  
5. Dashboard web production build 已成功完成。  

本輪驗證指令：

```bash
rg --files parsed -g '*.json' | wc -l
find converted-skills -mindepth 1 -maxdepth 1 -type d | wc -l
.venv/bin/python -m pytest tests skill-0-dashboard/apps/api/tests -q
cd skill-0-dashboard/apps/web && npm test -- --run
cd skill-0-dashboard/apps/web && npm run build
```

---

## 3. 執行原則（YOLO 持續推進）

1. **先收斂再擴張**：未完成 P1 收斂前，不啟動新一輪大規模功能擴張。  
2. **證據先於敘事**：每個 checkpoint 都要有可驗證輸出（文件、測試、指令結果）。  
3. **分支隔離審查噪音**：將 runtime、parsed corpus、review docs 分流處理。  
4. **對外說法一致**：除 strict benchmark 外，不把 fidelity 分數表述為 strict equivalence。  

---

## 4. 可執行 Checkpoints

| Checkpoint | 目標 | 主要交付 | 驗收標準 | 依賴 |
|---|---|---|---|---|
| CP-01 | Worktree 收斂與分流 | 分支拆分執行單（A/B/C + cleanup） | 各分支變更範圍清楚、噪音檔排除（`skills.db-wal/shm`） | 無 |
| CP-02 | Governance P1 規格落地 | 非同步 job + retry 的 API/資料流設計稿 | 文件明確定義 `job_id`、狀態流轉、重試策略、失敗語義 | CP-01 |
| CP-03 | Runtime 風險補齊規格 | Rate limiter 代理情境與 search error handling 設計 | 補齊 RISK-4/RISK-5 的實作與測試需求 | CP-01 |
| CP-04 | 文件/CI 對齊 | 文件漂移防護方案（CI step + owner + fail rule） | CI 有可執行的 docs drift gate（至少定義命令與觸發時機） | CP-01 |
| CP-05 | 規劃文件語境對齊 | `docs/planning/*` 舊計畫加註狀態與新基線對應 | 不再把 `v2.0` 時期待辦誤當成現行主線 | CP-01 |
| CP-06 | 20-skills 擴展重排 | `plan-20-skills` 新版 gating 條件 | 清楚寫出「何時可啟動擴展」與先決條件 | CP-02, CP-03, CP-05 |
| CP-07 | 回歸驗證 | 驗證紀錄（schema、python tests、web tests/build） | 必要命令可重現且結果可追溯 | CP-02, CP-03, CP-04 |
| CP-08 | 外部審查包 | 送審摘要、風險揭露、變更清單 | 外審可快速辨識已完成/已設計/待實作 | CP-07 |
| CP-09 | 審查意見修正關閉 | 審查回覆與修正差異稿 | 所有阻塞級意見有處置結論 | CP-08 |

### 4.1 本輪 checkpoint 狀態更新

1. `CP-04` 已部分落地：  
   - 已新增 `tools/check_doc_status_markers.py`
   - 已在 `.github/workflows/ci.yml` 加入 `docs-status` gate
   - 已新增 `tools/check_shared_docs.py`，檢查 `docs/shared/` source set 與 `docs/shared-documentation-model.md` / `docs/shared/README.md` 不漂移
   - 後續仍需決定是否擴大到跨 repo mirrored docs 與 owner 規則

2. `CP-05` 已部分落地：  
   - 已為 `plan.md`、`plan-20-skills.md`、`yolo-dev-plan.md` 補上 historical status note
   - 已將本文件加入 `document-authority-index`
   - 後續仍可逐步擴大到其他歷史規劃/評估文件

3. `CP-02` 已完成規格收斂：  
   - 已新增 `governance-p1-async-retry-spec-2026-03-31.md`
   - 已定義 `job_id`、job/item 狀態機、retry policy、API 與資料模型邊界
   - `2026-04-02` 已落地單 instance MVP：dashboard API 支援 async batch scan/test job、job status/items 查詢與 manual retry

4. `CP-03` 已完成規格收斂：  
   - 已新增 `runtime-risk-hardening-spec-2026-03-31.md`
   - 已定義 trusted proxy header policy、client IP extraction 與 search `503` contract
   - `2026-04-02` 已在 `api/main.py` 落地 trusted proxy client IP extraction 與 search/similar/cluster graceful `503` handling

5. `CP-07` 已對本輪文件治理切片完成驗證：  
   - `python tools/check_doc_status_markers.py` passed
   - `python tools/validate_skill_schema.py parsed` passed
   - Python / web regression 與 web build 已在本輪重跑並通過

6. `CP-01` 已於 `2026-04-02` 完成收斂：  
   - `e2fc8c1` `Add yolo-unattended skill and targeted parser safety`
   - `99f56e5` `Harden dashboard auth and governance runtime`
   - `3534eb0` `Normalize parsed corpus and align fidelity tooling`
   - `6d3ad5e` `Add review dossier and shared documentation bundle`
   - 剩餘未收斂項已降到單檔 spillover 與少數 process docs

7. `CP-03` 核心實作已於 `2026-04-02` 補齊：
   - rate limiter 已切換到 trusted proxy aware client IP extraction
   - `/api/search`、`/api/similar`、`/api/cluster` backend failure 已統一回傳 structured `503`
   - 最小驗證：`.venv/bin/python -m pytest tests/test_api_security.py tests/integration/test_rate_limiting.py tests/integration/test_api_core.py -q`

8. `CP-02` MVP 已於 `2026-04-02` 補齊：
   - dashboard API 新增 `scan-jobs` / `test-jobs` / `action-jobs` / retry endpoints
   - 首版為 cached `GovernanceService` 內的單 instance memory-backed job runner
   - 保留既有同步 `scan/test` 入口，未破壞現有 UI 路徑
   - 最小驗證：`.venv/bin/python -m pytest skill-0-dashboard/apps/api/tests -q`
   - `2026-04-02` 補上第一個 UI 接線：`SkillDetail` 單技能頁已改為顯示 async job queued/running/completed 狀態、item 細節與 single-item manual retry

9. `CP-02` 前端覆蓋已於 `2026-04-03` 再往前推一格：
   - `ReviewQueue` 已支援 pending queue 的 batch scan/test job 觸發
   - 頁面會顯示最新 async job summary、item 狀態與 batch retry failed items
   - job 執行中會鎖住 approve/reject 與其他 batch 動作，避免交錯操作
   - 最小驗證：`cd skill-0-dashboard/apps/web && npm test -- --run src/pages/ReviewQueue.test.tsx src/pages/SkillDetail.test.tsx && npm run build`

10. `CP-02` durability / restart recovery 已於 `2026-04-03` 落地：
   - async action jobs 與 job items 已持久化到 `governance.db`
   - `GovernanceService` 啟動時會回收 `queued/running` job，將 orphaned item 重設為可重跑狀態並重新排入執行
   - action job API 不再依賴 process-local memory 作為唯一真實狀態
   - 最小驗證：`.venv/bin/python -m pytest skill-0-dashboard/apps/api/tests/test_governance.py skill-0-dashboard/apps/api/tests/test_skills.py -q`

11. `CP-02` worker claim discipline 已於 `2026-04-03` 補齊：
   - runner 改為循環從 DB 原子 claim `queued/retrying` items，而不是先把整批 active items 載入記憶體
   - 當其他 worker 仍持有 `running` item 時，job 不會被過早 finalize 成 terminal status
   - 這一層已能防止多個 active API instance 對同一 item 重複執行；更進一步的 lease/heartbeat/cancel 仍屬 hardening
   - 最小驗證：`.venv/bin/python -m pytest skill-0-dashboard/apps/api/tests/test_governance.py -q`

12. `CP-02` lease / heartbeat 已於 `2026-04-03` 再補一格：
   - claimed item 現在帶有 `lease_expires_at`，active worker 會在執行期間定期 refresh lease
   - recovery 只會回收 lease 已過期的 `running` item，仍在有效 lease 內的 item 會保留給既有 worker
   - 這讓「active worker 被誤當 orphaned」的風險下降，後續剩餘工作集中在 cancel semantics 與 richer telemetry
   - 最小驗證：`.venv/bin/python -m pytest skill-0-dashboard/apps/api/tests/test_governance.py -q`

---

## 5. 近期排程建議（可直接執行）

### 5.0 本輪已落地項

1. 新增本文件作為目前的 checkpoint execution entrypoint。  
2. 已將 `docs/planning/plan.md`、`plan-20-skills.md`、`yolo-dev-plan.md` 補上 historical status note。  
3. 已將本文件加入 `docs/document-authority-index-2026-03-27.md`。  
4. 已新增 `tools/check_doc_status_markers.py`，並在 `.github/workflows/ci.yml` 加入 `docs-status` gate。  
5. 已新增 Governance P1 與 Runtime hardening 兩份可執行規格草案。  
6. 已在 dashboard web 補上 `ReviewQueue` 的 async batch scan/test job UI 與 retry failures 接線。  

### Sprint S1（1-2 天）

1. 推進 CP-02 下一階段：補上 job telemetry、取消語義，以及更完整的 lease expiry / heartbeat observability。  
2. 擴大 async UI 覆蓋面：評估是否將 batch job 狀態延伸到更多治理入口，而不重複造輪子。  
3. 持續收斂 CP-05：補齊其他歷史規劃/評估文件的 status note 與權威入口對齊。  

### Sprint S2（2-4 天）

1. 擴充 CP-04：決定 owner discipline 與 mirrored docs drift 的 gate 邊界。  
2. 補齊 CP-03 長尾 hardening：觀測性、部署假設與回歸防護。  
3. 完成 CP-06：20-skills 擴展計畫改為 gated 啟動條件。  

### Sprint S3（1-2 天）

1. 完成 CP-07：跑完整驗證並固化結果。  
2. 完成 CP-08：輸出外部審查包。  
3. 完成 CP-09：回收審查意見後修正與關閉。  

---

## 6. 驗證基線（每輪都要跑）

```bash
.venv/bin/python tools/validate_skill_schema.py parsed
.venv/bin/python -m pytest tests skill-0-dashboard/apps/api/tests -q
cd skill-0-dashboard/apps/web && npm test && npm run build
```

若某輪涉及 CI 或部署文件，需額外附上對應工作流結果與差異說明。

---

## 7. 外部審查與修正流程（必做）

1. 送審前整理：  
   - 本輪完成項（Implemented）  
   - 已設計待落地（Designed）  
   - 尚未啟動（Planned）  

2. 外審輸入分類：  
   - Blocking（需先修）  
   - Non-blocking（可排入下一輪）  
   - Disputed（需補證據再決策）  

3. 修正關閉規則：  
   - 每條 Blocking 都需有「修正 commit/文件節點 + 驗證證據」  
   - 無證據者不得標記為 closed  

---

## 8. 非目標（避免 scope creep）

1. 不在本輪直接推進全量 schema 大擴張（`2.5+`）。  
2. 不在 P1 收斂前開啟大規模新功能面。  
3. 不把歷史性 review 文件直接當作現行排程依據。  

---

## 9. 主代理整合建議

1. 先以 CP-01 作為整合入口，確保後續每個工作流有乾淨審查邊界。  
2. 把 CP-02/03/04 視為同一批「基線可信度」任務並行推進。  
3. 在 CP-07 前，不對外宣稱新一輪能力擴張完成。  
4. 完成 CP-09 後再刷新權威索引與下一版執行計畫。  
