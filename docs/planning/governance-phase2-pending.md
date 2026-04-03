# Governance Action Phase 2 — 待處理事項

**建立日期**：2026-02-24  
**分支**：`copilot/add-action-readiness-check`  
**狀態**：P0 + P1 durable MVP + P2 完成；後續為 hardening

Status note (`2026-04-03`): 本文件原本記錄的是 P1 尚未開始時的待辦清單。現在 async batch scan/test、retry、DB-backed job persistence、以及 restart recovery 已落地；下列內容應視為歷史背景與後續 hardening 參考，而不是現況快照。

---

## 一、已完成（已 commit）

| 項目 | 說明 | 檔案 |
|------|------|------|
| P0-1 Action Readiness 端點 | `GET /api/skills/{skill_id}/action-readiness` | `routers/skills.py` |
| P0-1 ActionReadiness Schema | `can_scan`, `can_test`, `source_path_exists`, `installed_path_exists`, `reasons[]` | `schemas/action.py` |
| P0-2 ActionResult Schema | `error_code`, `error_message`, `hint`, `status`, `processed`, `results` | `schemas/action.py` |
| P0-2 GovernanceService 擴充 | `run_scan()`, `run_test()`, `run_scan_batch()`, `run_test_batch()` | `services/governance.py` |
| P0-2 錯誤碼定義 | `PATH_NOT_FOUND`, `SOURCE_PATH_MISSING`, `INSTALLED_PATH_MISSING`, `SCAN_RUNTIME_ERROR`, `TEST_RUNTIME_ERROR` | `services/governance.py` |
| P0-3 後端單元測試 | 23 個測試全數通過 | `tests/test_governance.py` |
| 前端型別 | `ActionReadiness`, `ActionResult` | `web/src/api/types.ts` |
| 前端 Hooks | `useActionReadiness`, `useTriggerScan`, `useTriggerTest` | `web/src/api/skills.ts` |
| 前端 UI (P0) | `SkillDetail` 按鈕 disabled 狀態 + inline 回饋訊息 | `web/src/pages/SkillDetail.tsx` |
| **P2-6** SkillDetail 結果面板 | 可展開面板顯示 results[]、error_code、hint | `web/src/pages/SkillDetail.tsx` |
| **P2-7** Review 訊息一致化 | approve/reject 顯示後端返回 status 與 skill_id | `web/src/pages/ReviewQueue.tsx` |
| Bug 修復 | 移除 `schemas/skill.py` 重複 class、`routers/__init__.py` 重複 export | — |

---

## 二、驗證結果 ✅

| 項目 | 結果 |
|------|------|
| 後端單元測試 | ✅ 23/23 通過 |
| Python syntax check | ✅ 7 個檔案全部通過 |
| 前端 TypeScript build | ✅ 無錯誤 |
| CodeQL 安全掃描 | ✅ 0 alerts |
| 路由順序 (`action-readiness` 在 `{skill_id}` 前) | ✅ 確認正確 |

---

## 三、後續 hardening（原 P1 後續）

### P1-H1 Worker coordination / duplicate execution protection
- 目前 durable job state 已進 DB，但仍是單 API instance 內的 daemon thread runner
- **需要**：worker lease / claim discipline，避免多個 active instance 重複執行同一 job item
- **估計工時**：1–2 天

### P1-H2 Retry / cancellation / telemetry 補強
- 目前已支援 manual retry，但尚未有 automated retry backoff、cancel semantics、與更完整的 job telemetry
- **需要**：更明確的 worker policy、metrics、與操作觀測面
- **估計工時**：1 天

---

## 四、已知問題

| 問題 | 影響範圍 | 優先度 |
|------|----------|--------|
| `prometheus_client` 套件未安裝 | `api/main.py` import 會失敗，影響 core API 測試 | 中（預先存在，非本 PR 引入） |
| `tests/test_api_security.py` 因上述問題無法 collect | 既有測試套件 | 中（預先存在） |

---

## 五、里程碑（原計劃）

| 里程碑 | 內容 | 狀態 |
|--------|------|------|
| M1（3–4 天） | P0 完成 | ✅ 完成並驗證 |
| M2（5–7 天） | P1 durable MVP（非同步 + retry + DB persistence + recovery） | ✅ 已落地 |
| M3（2–3 天） | P2 完成（UX 優化） | ✅ 完成並驗證 |

---

## 六、相關檔案索引

```
skill-0-dashboard/apps/api/
├── schemas/
│   ├── action.py          ← 新增：ActionReadiness / ActionResult
│   └── skill.py           ← 修改：移除重複 class
├── routers/
│   ├── __init__.py        ← 修改：移除重複 export
│   └── skills.py          ← 修改：加入 readiness endpoint、實作 scan/test
├── services/
│   └── governance.py      ← 修改：加入 run_scan/run_test/readiness 方法
└── tests/
    └── test_governance.py ← 新增：23 個單元測試

skill-0-dashboard/apps/web/src/
├── api/
│   ├── types.ts           ← 修改：加入 ActionReadiness / ActionResult 型別
│   └── skills.ts          ← 修改：加入 useActionReadiness / useTriggerScan / useTriggerTest
└── pages/
    ├── SkillDetail.tsx    ← 修改：按鈕 disabled + readiness + 結果面板
    └── ReviewQueue.tsx    ← 修改：approve/reject 訊息一致化
```
