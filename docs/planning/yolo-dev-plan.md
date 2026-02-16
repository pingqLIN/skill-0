# Skill-0 YOLO 開發計畫（可執行版）

> 更新日期：2026-02-13  
> 範圍：依既有文件中「未完成/待強化」事項彙整為可執行計畫

## 執行進度（自動化）

- [x] `POST /api/auth/token` 改為環境變數帳密驗證，移除非空即通過邏輯
- [x] 新增 `AUTH_RATE_LIMIT` 並對登入端點施加更嚴格限流
- [x] 全域 API 基線限流（排除 health/docs/metrics 類端點）
- [x] 生產環境安全守門（`SKILL0_ENV=production` 時拒絕不安全 JWT/CORS/帳密配置）
- [x] 新增 `scripts/check_db_health.sh` 驗證 WAL 與備份新鮮度
- [x] 新增 `scripts/daily_maintenance.sh` 串接備份 + DB 健康檢查 + 安全掃描
- [x] 新增 `scripts/rotate_jwt_secret.sh` 支援 JWT key 輪替（含 env 檔備份）
- [ ] JWT key 版本化與無中斷輪替機制
- [ ] 反向代理 TLS 與網段封鎖落地
- [ ] 安全掃描告警通道整合（Email/Slack/PagerDuty）

## 0. 盤點基準（來源）

- `docs/planning/plan.md`
- `docs/planning/plan-20-skills.md`
- `docs/deployment-guide.md`
- `docs/architecture-overview.md`
- `docs/operations-runbook.md`
- `docs/test-equivalence-report.md`
- `docs/helper-test-results.md`
- `docs/implementation-summary.md`
- `docs/PROJECT-HISTORY.md`
- `docs/conversation-2026-01-23.md`
- `docs/skill-0-analysis.md`
- `docs/dashboard-design.md`

---

## 1. 立即修補（安全/生產風險）

### 1.1 認證與密鑰硬化（D0-D3）
- 目標：封堵預設弱認證與憑證風險，讓生產環境最小可用且可審計。
- 主要任務：
1. 在 `POST /api/auth/token` 實作真實使用者驗證（移除「非空即通過」邏輯）。
2. 重新產生並輪替 `JWT_SECRET_KEY`，縮短 token 時效（15 分鐘或更短）。
3. 補上失敗登入與 token 簽發稽核紀錄（含 request_id）。
- 驗收標準：
1. 無效帳密回傳 401，且不產生 token。
2. 安全測試可驗證舊密鑰無法簽發新 token。
3. 日誌可追溯登入成功/失敗事件（含 request_id 與時間戳）。
- 建議負責角色：Backend Engineer（主責）、Security Engineer（審核）。
- 引用來源路徑：`docs/deployment-guide.md`、`docs/architecture-overview.md`、`docs/operations-runbook.md`

### 1.2 邊界防護與流量治理（D0-D5）
- 目標：降低未授權跨域與濫用請求風險。
- 主要任務：
1. 將 `CORS_ORIGINS` 收斂為正式網域，移除 localhost 白名單。
2. 調整 `API_RATE_LIMIT` 並對高風險端點設定更嚴格限制。
3. 反向代理啟用 HTTPS-only，限制 API 直連入口。
- 驗收標準：
1. 非白名單來源 CORS 預檢被拒絕。
2. 壓測下 429 行為符合預期，且不影響健康檢查。
3. 外部掃描僅可經 TLS 入口訪問服務。
- 建議負責角色：SRE/DevOps（主責）、Backend Engineer（協作）。
- 引用來源路徑：`docs/deployment-guide.md`、`docs/operations-runbook.md`

### 1.3 資料保護與事故復原（D1-D7）
- 目標：建立可恢復的生產基線，避免資料毀損造成服務中斷。
- 主要任務：
1. 啟用每日自動備份（`scripts/backup_db.sh`）與保留策略。
2. 驗證 `skills.db` 與 `governance.db` 的 WAL 模式與還原流程。
3. 每日排程安全掃描並保存 `SECURITY_SCAN_REPORT_*.md`。
- 驗收標準：
1. 連續 7 天可取得可用備份檔，且可成功 restore。
2. WAL 檢查在兩個 DB 均為 `wal`。
3. 安全掃描報告每日產出，Critical/High 會觸發告警。
- 建議負責角色：SRE（主責）、Security Engineer（協作）。
- 引用來源路徑：`docs/operations-runbook.md`、`docs/deployment-guide.md`

---

## 2. 短期（測試與品質，1-3 週）

### 2.1 測試金字塔補齊（W1-W2）
- 目標：從「工具層通過」擴展到 API 與治理流程層的回歸保護。
- 主要任務：
1. 新增 Core API / Dashboard API 的整合測試（auth、search、index、governance flow）。
2. 新增安全回歸測試（JWT、CORS、rate limit、health degraded 情境）。
3. 將 20 skills 解析流程加入端到端 smoke test。
- 驗收標準：
1. 測試報告能區分 unit/integration/e2e，且每次 PR 可重跑。
2. 高風險 API 具失敗案例測試（401/403/429/5xx）。
3. 解析流程在 CI 中可穩定完成且結果可重現。
- 建議負責角色：QA Engineer（主責）、Backend Engineer（協作）。
- 引用來源路徑：`docs/test-equivalence-report.md`、`docs/helper-test-results.md`、`docs/operations-runbook.md`

### 2.2 品質門檻與發布守門（W1-W3）
- 目標：建立「可發布」定義，避免功能完成但品質未達標。
- 主要任務：
1. 設定品質門檻：測試通過率、關鍵路徑覆蓋、lint/type check。
2. 建立發布前檢查單（安全掃描、健康檢查、資料備份、回滾演練）。
3. 統一版本化輸出（analysis/evaluation 報告附版本與日期）。
- 驗收標準：
1. 未達門檻禁止合併到主幹。
2. 發布流程有可追溯 checklist 與責任人簽核。
3. 每次發布都能產出同格式品質報告。
- 建議負責角色：Tech Lead（主責）、QA Engineer / DevOps（協作）。
- 引用來源路徑：`docs/implementation-summary.md`、`docs/operations-runbook.md`

---

## 3. 中期（20 skills 擴展，3-6 週）

### 3.1 20 Skills 資料集建置（W3-W4）
- 目標：把規劃清單轉成可分析的正式資料集。
- 主要任務：
1. 凍結 20 個新增 skills 清單與備選規則（避免重複/來源失效）。
2. 收集 SKILL.md 或等效定義，補齊來源與分類標註。
3. 建立資料品質檢查（完整性、唯一性、可解析性）。
- 驗收標準：
1. 20/20 skill 均可追溯來源與類型。
2. 無重複 skill，資料完整率 100%。
3. 解析前檢查通過率 >= 95%。
- 建議負責角色：Data Engineer（主責）、Domain Reviewer（協作）。
- 引用來源路徑：`docs/planning/plan-20-skills.md`、`docs/planning/plan.md`

### 3.2 批次解析與覆蓋率驗證（W4-W5）
- 目標：完成 31 skills（既有 11 + 新增 20）的框架驗證。
- 主要任務：
1. 執行 batch parse 並轉換 v2.0/2.1 JSON。
2. 執行 analyzer / pattern extractor / evaluate 全流程。
3. 針對低覆蓋類型（例如指南型）建立例外標註策略。
- 驗收標準：
1. 整體覆蓋率 >= 90%，Directive 覆蓋率 >= 85%。
2. 解析總耗時 <= 1.5 秒（31 skills）。
3. 產出 report、patterns、evaluation 三份更新報告。
- 建議負責角色：Backend Engineer（主責）、Data Engineer（協作）。
- 引用來源路徑：`docs/planning/plan-20-skills.md`、`docs/PROJECT-HISTORY.md`

### 3.3 擴展後質量回顧與修正（W5-W6）
- 目標：把「擴展完成」轉成「可維護」狀態。
- 主要任務：
1. 比對擴展前後品質指標（覆蓋率、效能、錯誤率）。
2. 抽樣人工審核分類結果，記錄 false positive/negative。
3. 對 schema 與解析器提出最小必要修訂清單。
- 驗收標準：
1. 有前後對照報告，指標趨勢可解釋。
2. 人工抽樣一致性達預設門檻（例如 >= 90%）。
3. 形成下一輪實作 issue backlog（含優先級與 owner）。
- 建議負責角色：Tech Lead（主責）、QA Engineer（協作）。
- 引用來源路徑：`docs/planning/plan.md`、`docs/skill-0-framework-evaluation.md`

---

## 4. 長期（CI/CD、可視化、多語言、LLM，6 週+）

### 4.1 CI/CD 正式化（M2-M3）
- 目標：讓測試、安全、打包與部署流程自動化且可審核。
- 主要任務：
1. 建立完整 CI pipeline（test、lint、security scan、artifact）。
2. 加入 CD gate（健康檢查、回滾條件、部署驗證）。
3. 針對資料庫備份/還原建立演練排程。
- 驗收標準：
1. 每次合併自動觸發 CI 並產出可追溯報告。
2. 部署失敗可在目標時間內回滾。
3. 每月至少一次備援演練並留存紀錄。
- 建議負責角色：DevOps Engineer（主責）、Tech Lead（協作）。
- 引用來源路徑：`docs/implementation-summary.md`、`docs/architecture-overview.md`

### 4.2 可視化與治理儀表板（M2-M4）
- 目標：把分析結果轉為可決策的治理視圖。
- 主要任務：
1. 實作風險分布、狀態分布、規則違規統計圖表。
2. 串接審核佇列與審計日誌視圖，支援追蹤閉環。
3. 加入關鍵 KPI（高風險數、平均等價分數、趨勢）。
- 驗收標準：
1. Dashboard 可對應 API 提供的統計端點。
2. 管理員可從風險圖直達技能細節與審核紀錄。
3. 團隊每週例會可直接用儀表板完成狀態檢視。
- 建議負責角色：Frontend Engineer（主責）、Backend Engineer（協作）。
- 引用來源路徑：`docs/dashboard-design.md`、`docs/architecture-overview.md`、`docs/conversation-2026-01-23.md`

### 4.3 多語言文件與內容治理（M3-M4）
- 目標：提升跨語言協作，降低文件落差。
- 主要任務：
1. 建立文件多語言優先順序（README、SKILL、Runbook、Plan）。
2. 定義雙語版控流程（原文、翻譯、審校責任）。
3. 加入術語表與版本對齊規範。
- 驗收標準：
1. 核心文件具至少中英雙語版本且版本同步。
2. 新版文件可在同一發布週期完成雙語更新。
3. 術語一致性審查可追溯。
- 建議負責角色：Technical Writer（主責）、Maintainer（審核）。
- 引用來源路徑：`docs/implementation-summary.md`、`docs/skill-0-analysis.md`

### 4.4 LLM 輔助解析與生成（M3+）
- 目標：在不犧牲可驗證性的前提下，提升解析與模式發現能力。
- 主要任務：
1. 設計可重複執行的 LLM prompt 模板與輸出約束。
2. 導入不確定性處理策略（confidence、retry、human review trigger）。
3. 建立 LLM 輔助的缺口分析與新 skill 建議流程。
- 驗收標準：
1. LLM 輸出可被 schema 驗證，且失敗可回退到規則式流程。
2. 不確定性欄位可量化，人工覆核流程可追蹤。
3. 每月產出可用的 skill 建議清單與命中率回顧。
- 建議負責角色：ML Engineer（主責）、Backend Engineer / Domain Expert（協作）。
- 引用來源路徑：`docs/PROJECT-HISTORY.md`、`docs/conversation-2026-01-23.md`、`docs/skill-0-framework-evaluation.md`、`docs/skill-mcp-tools-comparison.md`

---

## 5. 建議執行順序（跨軌道）

1. 先完成 1.x（安全基線）再開放中期擴展主線。
2. 2.x（測試與品質）需與 3.x（20 skills）並行，避免擴展後才補測。
3. 4.x（長期）以「CI/CD -> 可視化 -> 多語言 -> LLM」順序推進，降低風險。
