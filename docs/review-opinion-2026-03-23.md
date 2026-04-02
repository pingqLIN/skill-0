# Skill-0 專案技術審查意見書

**文件編號：** SKILL0-REVIEW-2026-03-23  
**審查日期：** 2026-03-23  
**審查範圍：** 完整代碼庫、CI/CD、Docker 部署鏈、文件體系  
**審查方法：** 靜態代碼分析 + 架構審視 + 部署驗證交叉核實  
**對應文件：**
- `docs/project-progress-report-2026-03-23.md`（進度報告）
- `docs/project-review-2026-03-23.md`（內部審查報告）
- `docs/external-review-report-2026-03-23.md`（外部審核版報告）

---

## 壹、審查結論

### 總體判定

Skill-0 專案目前已達到**可送交外部技術審核**的基線。

核心功能已成形，主要部署鏈已通過 smoke test，問題重心已從功能缺口轉向營運級穩定性與容量驗證。本意見書建議以「技術審核」與「部署風險評估」為定位進行外部送審，**暫不建議視為正式營運驗收完成**。

### 判定依據

| 維度 | 判定 | 說明 |
|------|------|------|
| 核心功能完整性 | ✅ 通過 | 搜尋、治理、Dashboard 三層均已成形 |
| 認證鏈完整性 | ✅ 通過 | JWT 簽發→攔截器→受保護路由→401 自動登出 |
| 前端品質基線 | ✅ 通過 | lint、build、build:ci、18 tests 均通過 |
| Docker 部署鏈 | ✅ 通過 | 三個 image build + compose up + health check + restart persistence |
| CI/CD 完整性 | ✅ 通過 | lint→compile→pytest(coverage gate)→web build→docker build |
| 生產安全防護 | ✅ 通過 | JWT secret fail-fast、CORS 環境變數化、Swagger docs 開關、路徑白名單 |
| 營運級驗證 | ⚠️ 部分 | 記憶體壓力測試、備份策略、長時間運行觀測仍待完成 |

---

## 貳、審查過程中的重要修正

本次審查橫跨多輪迭代。以下記錄審查過程中發現的重大判斷修正，以確保意見書的透明度。

### 修正一：前端認證鏈的誤判與更正

| 時間點 | 判斷 | 依據 |
|--------|------|------|
| 初次審查 | 🔴 「前端無 token 注入邏輯」 | 僅檢視 `client.ts` 開頭片段 |
| 深度探索後 | ✅ 完整實作 | 發現 `client.ts` 含 axios interceptor + `auth/` 模組含完整 login/logout/protected routes |

**教訓：** 進度報告本身描述不準確（稱「no token attachment logic is visible」），導致初次審查採信。實際代碼庫的完成度高於報告描述。

### 修正二：Bulk Approve 功能的誤判與更正

| 時間點 | 判斷 | 依據 |
|--------|------|------|
| 初次審查 | 🟠 「Bulk Approve 刻意禁用」 | 進度報告稱 `intentionally disabled` |
| 深度探索後 | ✅ 已完整實作 | `handleBulkApproveSafe()` 邏輯完整，`disabled` 僅為操作中的 UX 防護 |

### 修正三：Swagger UI 風險的提出與解決

| 時間點 | 判斷 |
|--------|------|
| 深度探索時 | 🔴 Dashboard API `/docs`、`/redoc` 在生產環境預設公開 |
| 後續實作後 | ✅ 已透過 `SKILL0_ENABLE_DOCS` 環境變數控制，production 預設關閉 |

---

## 參、架構與技術評估

### 3.1 整體架構

```
                     ┌─────────────┐
                     │   Web UI    │ React 19 + Vite
                     │  :3080/80   │
                     └──────┬──────┘
                            │
              ┌─────────────┼─────────────┐
              ▼                           ▼
     ┌────────────────┐         ┌────────────────┐
     │   Core API     │         │ Dashboard API  │
     │   :8000/8080   │         │ :8001/internal │
     │  (搜尋/索引)   │◄─JWT──►│  (治理/審計)   │
     └───────┬────────┘         └───────┬────────┘
             │                          │
             ▼                          ▼
        ┌─────────┐            ┌──────────────┐
        │skills.db│            │governance.db │
        │(sqlite- │            │  (sqlite3)   │
        │  vec)   │            └──────────────┘
        └─────────┘
```

**評價：** 三層分離清晰，職責明確。兩個 FastAPI 服務共享 JWT secret 但各自獨立運行，是合理的微服務拆分起點。

### 3.2 技術棧評估

| 技術選擇 | 評價 | 風險等級 |
|----------|------|----------|
| FastAPI + Pydantic v2 | 型別安全、自動文件、async 支持，**合理** | 低 |
| SQLite-vec + all-MiniLM-L6-v2 | 輕量本地向量搜尋，無外部 API 依賴，**合理** | 中（擴展性受限） |
| React 19 + Vite 7 + TanStack Query | 現代前端棧，lazy loading + code splitting，**合理** | 低 |
| SQLite（雙 DB 架構） | 開發快速、零配置，**目前規模可接受** | 中高（長期） |
| Docker 三容器 + compose | 標準容器化，dev/prod 分離，**合理** | 低 |
| structlog 結構化日誌 | JSON/console 雙模式，request ID 貫穿，**良好** | 低 |

### 3.3 安全機制評估

| 機制 | 實作狀態 | 評價 |
|------|----------|------|
| JWT 認證（Core API） | ✅ 簽發 + 驗證 + 過期控制 | 良好 |
| JWT 認證（Dashboard API） | ✅ 共享 secret 驗證 | 良好 |
| 前端 token 管理 | ✅ localStorage + interceptor + 401 auto-logout | 良好 |
| 生產安全 fail-fast | ✅ 啟動時檢測 JWT secret/CORS/帳密 | 優秀 |
| Rate limiting | ✅ 自建 in-memory，async lock 保護 | 可用，不適合多 worker/反向代理 |
| CORS 控制 | ✅ 環境變數化，生產模式不允許本地/萬用位址 | 良好 |
| Swagger docs 控制 | ✅ `SKILL0_ENABLE_DOCS` 環境變數，production 預設關閉 | 良好 |
| 路徑白名單 | ✅ governance service 已補 | 良好 |
| SQL 注入防護 | ✅ 全程參數化查詢 | 良好 |
| 硬編碼 secrets | ✅ 無（test fixtures 的測試帳密可接受） | 良好 |

### 3.4 測試體系評估

| 測試層 | 數量 | 涵蓋範圍 | 評價 |
|--------|------|----------|------|
| Python 單元測試 | 45 | API security helpers、schema helper | 良好 |
| Python 整合測試 | 62 | Auth flow、rate limiting、API core endpoints | 良好 |
| Dashboard API 測試 | 50 | 全 5 個 router + governance service | 良好 |
| Frontend 測試 | 18 | Component smoke tests (Vitest) | 基礎可用 |
| **合計** | **175** | — | — |
| CI coverage gate | `--cov-fail-under=75` | 強制最低覆蓋率 | 良好 |

---

## 肆、已驗證結果

### 4.1 開發驗證

| 項目 | 結果 |
|------|------|
| `npm run lint` | ✅ passed |
| `npm run build` | ✅ passed |
| `npm run build:ci`（含 bundle size guardrail） | ✅ passed |
| `npm test`（Node 20.19.0） | ✅ 18 passed |
| Python `compileall` | ✅ passed |
| Python `pytest`（完整迴歸） | ⚠️ 待本地 dev 環境恢復後確認（CI 已含此步驟） |

### 4.2 Docker 與 Runtime 驗證

| 項目 | 結果 |
|------|------|
| `docker build -f Dockerfile.api` | ✅ passed |
| `docker build -f Dockerfile.dashboard` | ✅ passed |
| `docker build -f Dockerfile.web` | ✅ passed |
| `docker compose -f docker-compose.prod.yml config` | ✅ passed |
| `docker compose -f docker-compose.prod.yml up -d --build` | ✅ passed |
| Core API health (`http://127.0.0.1:8080/health`) | ✅ passed |
| Dashboard health (`http://127.0.0.1:3080/dashboard-api/health`) | ✅ passed |
| Web 入口 (`http://127.0.0.1:3080/`) | ✅ passed |
| `POST /api/auth/token` 取得 JWT | ✅ passed |
| JWT 存取 `GET /dashboard-api/api/stats` | ✅ passed |
| Compose restart 後 API/dashboard 恢復 healthy | ✅ passed |
| `skills.db` / `governance.db` volume persistence | ✅ passed |

---

## 伍、仍然成立的風險

### 🔴 High Priority

#### RISK-1：API 容器記憶體壓力

- **現狀：** `docker-compose.prod.yml` 上限已提升至 `1G`；`sentence-transformers` + `torch`（CPU-only）在推論時記憶體消耗仍需實測
- **觸發條件：** 容器記憶體峰值接近或超過 1G
- **應變：** 提高上限至 1.5G；或將 embedding 拆為獨立服務；或改用更輕量的推論框架（ONNX Runtime）
- **驗證方式：** `docker stats` 持續觀測 10 分鐘並發搜尋壓測

#### RISK-2：雙 SQLite 架構的一致性與備份

- **現狀：** `skills.db`（向量搜尋）與 `governance.db`（治理流程）無跨 DB 外鍵約束
- **觸發條件：** skill_id 不同步、DB 損壞、需要災難恢復
- **應變：** 制度化備份排程（cron + volume snapshot）；補應用層一致性檢查；長期評估 PostgreSQL 遷移
- **驗證方式：** 備份→刪除→還原→功能驗證

#### RISK-3：Production secrets 未覆寫

- **現狀：** `.env.production.example` 已提供範本，啟動 fail-fast 已實作
- **觸發條件：** 部署時忘記設定 `JWT_SECRET_KEY` / `API_USERNAME` / `API_PASSWORD`
- **應變：** 已有 fail-fast 保護（production 模式下若偵測到預設值，拒絕啟動）。建議在部署 checklist 中明列必填項

### 🟠 Medium-High

#### RISK-4：Rate limiter 在反向代理後行為異常

- **現狀：** 自建 in-memory rate limiter 使用 `request.client.host`，不讀 `X-Forwarded-For`
- **觸發條件：** 透過 nginx/Cloudflare 部署
- **應變：** 加入 forwarded header 解析；或遷移至 `slowapi` / Redis-backed 方案

#### RISK-5：搜尋端點無 try-catch

- **現狀：** `/api/search`、`/api/similar`、`/api/cluster` 若 embedder 或 DB 異常，直接 500
- **觸發條件：** 模型未下載、DB 損壞、記憶體不足
- **應變：** 加入 graceful error handling，回傳 503 + 結構化錯誤訊息

#### RISK-6：治理操作同步阻塞

- **現狀：** batch scan/test 為同步迴圈，阻塞 async event loop
- **觸發條件：** 大量技能同時 scan/test
- **應變：** `asyncio.to_thread()` 或引入 task queue

### 🟡 Medium

#### RISK-7：Schema 版本號散落不一致

- **位置：** `schema/*.json`（v2.4.0）vs `CLAUDE.md`（v2.0.0）vs changelog（v2.1.0）
- **影響：** AI agent 可能依據舊版 schema 生成不符格式的輸出

#### RISK-8：README 測試數字不一致

- **位置：** Project Structure 段（`111+ tests`）vs Testing 段（`157 automated tests`）
- **實際：** Python 157 + Frontend 18 = **175 total**
- **建議：** 統一為 `170+` 或確切數字

---

## 陸、文件體系一致性

本次審查同時檢視了三份對外/對內文件的交叉一致性：

| 檢查項目 | 外部報告 | 內部報告 | README | 一致性 |
|----------|----------|----------|--------|--------|
| Production ports（3080/8080） | ✅ | ✅ | ✅ | ✅ |
| JWT 登入→受保護端點流程 | ✅ | ✅ | ✅ | ✅ |
| Restart persistence 驗證 | ✅ | ✅ | — | ✅ |
| Node 20.19.0 基線 | ✅ | ✅ | ✅ | ✅ |
| Swagger docs 開關 | ✅ 已實作 | ✅ 已實作 | — | ✅ |
| API 記憶體上限 1G | ✅ | ✅ | — | ✅ |
| 測試總數 | — | — | ⚠️ 不一致 | ⚠️ |
| 剩餘風險揭露 | ✅ 誠實 | ✅ 詳細 | — | ✅ |

**結論：** 文件體系整體一致，外部報告的風險揭露誠實適度，不存在過度包裝或隱匿問題的情形。唯 README 測試數字需更新。

---

## 柒、建議行動優先序

### 送審前建議修正（低成本）

1. **統一 README 測試數字**（`111+` → `170+`）
2. **統一 schema 版本號引用**（各文件與 `CLAUDE.md` 對齊至 v2.4.0）

### 送審後、上線前建議完成

3. **API 記憶體壓測**：`docker stats` 觀測持續並發搜尋下的記憶體峰值
4. **備份策略文件化**：制定 DB 備份 SOP 並驗證還原流程
5. **搜尋端點加入 graceful error handling**
6. **Rate limiter 加入 `X-Forwarded-For` 支援**
7. **Python 完整迴歸測試重跑確認**

### 長期演進建議

8. 評估 PostgreSQL 遷移時機（技能數 > 1,000）
9. 評估 embedding 服務獨立拆分（查詢量增長時）
10. 考慮引入 task queue 處理長時間治理操作

---

## 捌、總結

Skill-0 在技術實作品質上表現良好：

- **架構合理**：搜尋、治理、Dashboard 三層分離清晰
- **安全意識到位**：JWT fail-fast、CORS 環境變數化、Swagger 生產關閉、路徑白名單、參數化查詢
- **驗證鏈完整**：前端全綠、Docker build/compose/health check/restart persistence 均已通過
- **風險揭露誠實**：文件體系未隱匿已知問題

剩餘風險集中在**營運級驗證**（記憶體壓測、備份策略、長時間運行觀測），而非核心功能缺失或架構缺陷。

**本意見書建議：可進入外部技術審核，暫不視為正式營運驗收完成。**

---

*審查意見書完*
