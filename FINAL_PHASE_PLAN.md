# Skill-0 專案最終階段開發計畫書
# Skill-0 Final Phase Development Plan

**生成日期 / Generated**: 2026-02-11  
**專案版本 / Project Version**: v2.3.0  
**Git 狀態 / Git Status**: 285+ files staged, merge conflicts resolved, all tests passing, duplicate files fixed  
**評估者 / Evaluator**: Antigravity AI Agent

---

## 執行摘要 / Executive Summary

Skill-0 專案目前已完成核心功能開發，包含：
- ✅ 三元分類系統 (Actions/Rules/Directives)
- ✅ 32 個技能解析範例
- ✅ 語意搜尋引擎 (SQLite-vec + sentence-transformers)
- ✅ REST API (FastAPI, 2 個獨立伺服器)
- ✅ 治理儀表板 (React 19 + Vite)
- ✅ 自動化測試套件 (32 tests, 100% pass)

**主要缺口 / Primary Gaps**:
1. 生產環境部署配置缺失 (Docker/Kubernetes)
2. API 安全性配置不足 (CORS 全開放、無驗證機制)
3. 缺乏整合測試與端對端測試
4. 儀表板功能未完整實作 (UI 存在但後端服務未串接)
5. 文件與實際狀態有部分落差

---

## 第一部分：專案現狀評估
## Part 1: Current Project State Assessment

### 1.1 已完成功能 / Completed Features

| 模組 | 狀態 | 備註 |
|------|------|------|
| **核心解析器** | ✅ 完成 | `tools/batch_parse.py`, 32 skills parsed |
| **語意搜尋** | ✅ 完成 | `vector_db/`, CLI + Python API |
| **Schema v2.1** | ✅ 完成 | `schema/skill-decomposition.schema.json` |
| **REST API (Core)** | ✅ 完成 | `api/main.py`, port 8000, 10 endpoints |
| **REST API (Dashboard)** | ⚠️ 部分完成 | `skill-0-dashboard/apps/api/`, port 8001, 5 routers but incomplete services |
| **Dashboard UI** | ⚠️ 部分完成 | React app built successfully, but not fully integrated with backend |
| **測試框架** | ✅ 完成 | `tests/`, 32 tests, pytest configured |
| **文件系統** | ✅ 完成 | CLAUDE.md, SKILL.md, reference.md, examples.md, AGENTS.md |

### 1.2 技術堆疊驗證 / Tech Stack Validation

**Python 後端 (已驗證)**:
```bash
✅ Python 3.12+
✅ FastAPI 0.100.0+ (2 instances)
✅ Pydantic v2 (type-safe models)
✅ SQLite-vec (vector storage)
✅ sentence-transformers (all-MiniLM-L6-v2)
✅ pytest 7.0+ (32 tests passing)
```

**React 前端 (已驗證)**:
```bash
✅ React 19.2.0
✅ Vite 7.2.4
✅ TailwindCSS 3.4.19
✅ TypeScript 5.9.3
✅ React Router 7.13.0
✅ TanStack Query 5.90.20
✅ Recharts 3.7.0 (charts)
✅ Radix UI (primitives)
✅ ESLint 9.39.1 (0 errors)
```

**建置驗證 / Build Verification**:
```bash
✅ Web: npm ci && npm run build (312 packages, 0 vulnerabilities)
✅ Web: npm run lint (0 errors, 5 warnings - all non-blocking)
✅ Python: compileall (all .py files compile)
✅ Python: pytest (32/32 tests passed, 12 warnings)
✅ Git: 0 conflict markers, 0 whitespace issues
```

### 1.3 發現的問題 / Identified Issues

#### 🔴 Critical (阻擋生產部署)

1. **安全性漏洞 / Security Vulnerabilities**
   - **CORS 全開放**: `allow_origins=["*"]` in both `api/main.py` and `skill-0-dashboard/apps/api/main.py`
   - **無認證機制**: No authentication/authorization in any API endpoints
   - **無 HTTPS**: Development-only HTTP configuration
   - **無 API Rate Limiting**: Vulnerable to DoS attacks
   - **檔案位置**:
     - `api/main.py` line 35
     - `skill-0-dashboard/apps/api/main.py` line 23

2. **部署配置缺失 / Missing Deployment Configuration**
   - **無 Docker**: No Dockerfile or docker-compose.yml found
   - **無 Kubernetes**: No k8s manifests (deployment, service, ingress)
   - **無環境變數管理**: No .env files, no secrets management
   - **無 CI/CD**: No GitHub Actions, GitLab CI, or other pipelines
   - **無生產 DB 設定**: SQLite only (not production-ready for scale)

3. **儀表板服務未完整實作 / Dashboard Services Incomplete**
   - **檔案**: `skill-0-dashboard/apps/api/services/governance.py` (36,503 bytes)
   - **問題**: 
     - Service layer exists but may contain mock/incomplete implementations
     - Database path uses relative `../../skills.db` (fragile)
     - No database schema migration system
     - `governance/db/governance.db` exists but not documented

4. **Vector Search GPU 相容性崩潰 / Vector Search CUDA Crash** *(v1.1 新增)*
   - **問題**: `torch.AcceleratorError: CUDA error: no kernel image is available for execution on the device`
   - **原因**: 目前 GPU (GTX 1080, sm_61) 與安裝的 PyTorch 版本不相容 (需要 sm_70+)
   - **臨時解法**: `CUDA_VISIBLE_DEVICES=""` 強制使用 CPU 模式可正常運作
   - **影響**: 任何沒有設定該環境變數的部署都會直接崩潰
   - **檔案**: `vector_db/embedder.py` — 缺乏 GPU fallback 處理邏輯
   - **修復建議**: 在 embedder 初始化時加入 try/except，自動偵測 CUDA 可用性並回退到 CPU

5. **儀表板零測試覆蓋 / Dashboard Has Zero Tests** *(v1.1 新增)*
   - **Dashboard API**: 無 `tests/` 目錄, 無任何測試檔案
   - **Dashboard Web**: 無 `__tests__/`, 無 `.test.tsx` / `.spec.ts` 檔案
   - **風險**: 任何修改都無法驗證正確性

#### 🟠 High (影響可用性)

4. **測試覆蓋不足 / Insufficient Test Coverage**
   - **缺失**:
     - ❌ No API integration tests (FastAPI endpoint testing)
     - ❌ No dashboard backend tests (`skill-0-dashboard/apps/api/tests/`)
     - ❌ No frontend tests (`skill-0-dashboard/apps/web/src/__tests__/`)
     - ❌ No E2E tests (Playwright, Cypress)
   - **現有**:
     - ✅ Unit tests for core utilities (`tests/test_helper.py`, 32 tests)
   - **覆蓋率**: Unknown (no coverage reports)

5. **錯誤處理不一致 / Inconsistent Error Handling**
   - API endpoints use basic `HTTPException` without structured error responses
   - No global exception handler
   - No error logging/monitoring (Sentry, CloudWatch, etc.)

6. **效能基準測試缺失 / Missing Performance Benchmarks**
   - Vector search claimed "~75ms latency" but no load testing
   - No API response time monitoring
   - No database query optimization analysis

#### 🟡 Medium (技術債務)

7. **文件與實際狀態不同步 / Documentation Drift**
   - README.md claims "171 imported skills from converted-skills/" but parser can't process them
   - `tools/AGENTS.md` states all scripts are executable but no `chmod +x` found in git
   - Dashboard API claims "governance workflow" but implementation incomplete

8. **程式碼重複 / Code Duplication**
   - Two separate FastAPI apps with similar CORS/startup logic
   - API client configuration duplicated across files
   - Security scanning patterns repeated in `tools/advanced_skill_analyzer.py` and `tools/skill_scanner.py`
   - ~~3 files with exact duplicate content~~ *(v1.1: 已修復 — `dependencies.py`, `schemas/review.py`, `requirements.txt`)*

9. **環境設定硬編碼 / Hardcoded Configuration**
   - Database paths hardcoded in code (not env vars)
   - API URLs in frontend use fallback defaults only
   - No config validation at startup

10. **Governance DB 與 Vector DB 不同步 / DB Sync Gap** *(v1.1 新增)*
    - `governance/db/governance.db`: 163 個已核准技能
    - `skills.db` (vector store): 僅 32 個已索引技能
    - 差距 131 個技能未被 vector search 覆蓋
    - **修復建議**: 擴充 `batch_parse.py` 支援 `converted-skills/` 格式, 或建立同步腳本

11. **CI/CD Pipeline 不完整 / Incomplete CI** *(v1.1 新增)*
    - `.github/workflows/ci.yml` 存在但僅執行 flake8 + JSON schema validation
    - **缺失**: pytest 未在 CI 中執行
    - **缺失**: Web build (`npm run build`) 未在 CI 中驗證
    - **缺失**: Dashboard API 測試未包含
    - **修復建議**: 擴展 CI workflow 涵蓋所有驗證步驟

#### 🟢 Low (改善項目)

12. **TODO/FIXME 標記 / Code Markers**
    - Found in `converted-skills/` markdown files (documentation level)
    - No actionable TODOs in core codebase (Python/TypeScript)

13. **依賴版本未鎖定 / Unlocked Dependencies**
    - Python: Uses `>=` ranges (e.g., `fastapi>=0.100.0`)
    - Node: Uses `^` ranges (e.g., `"react": "^19.2.0"`)
    - **風險**: Potential breaking changes on `npm install` / `pip install`
    - **建議**: Generate `package-lock.json`, `poetry.lock`, or `requirements.lock`

14. **日誌系統缺失 / Missing Logging Infrastructure**
    - No structured logging (JSON logs)
    - No log rotation
    - No centralized logging (ELK, CloudWatch)

15. **已刪除垃圾檔案 / Stale File Removed** *(v1.1 新增)*
    - `## Chat Customization Diagnostics.md` — 已刪除 (非專案檔案, 1,156 bytes)

---
## Part 2: Final Phase Development Roadmap

### Phase 1: 安全性與生產準備 (優先級：P0)
### Phase 1: Security & Production Readiness (Priority: P0)

**目標**: 解決所有 Critical 安全性問題，達到可部署狀態

**Agent 分派**:
- A: 安全架構設計（Auth/Rate limit/CI 設計）
- B: 高風險推理與安全風險評估（CORS/JWT/攻擊面）
- C: API/部署實作（CORS/JWT/Rate limiting/Docker/CI）
- D: 文件與配置（.env 模板、部署說明）
- E/F: 小型修補與腳本整理（低風險）

#### Task 1.1: API 安全性強化
**預估時間**: 2-3 天  
**負責模組**: `api/main.py`, `skill-0-dashboard/apps/api/main.py`

**子任務**:
1. [ ] **CORS 限制**
   - 將 `allow_origins=["*"]` 改為環境變數控制的白名單
   - 生產環境只允許特定域名
   - 檔案: `api/main.py` L35, `skill-0-dashboard/apps/api/main.py` L23

2. [ ] **API 認證機制**
   - 實作 JWT-based authentication
   - 使用 `fastapi-users` 或 `python-jose`
   - 新增 `/api/auth/login`, `/api/auth/logout` endpoints
   - 保護所有敏感端點 (POST/PUT/DELETE)

3. [ ] **Rate Limiting**
   - 整合 `slowapi` 或 `fastapi-limiter`
   - 設定: 100 requests/minute per IP
   - 重點保護: `/api/search`, `/api/index`

4. [ ] **HTTPS 配置**
   - Nginx reverse proxy with Let's Encrypt
   - 強制 HTTPS redirect
   - HSTS headers

**驗收標準**:
- [ ] CORS 只允許配置的域名
- [ ] 所有 API 端點需要有效 JWT token
- [ ] Rate limiting 阻擋過量請求
- [ ] 安全掃描工具 (OWASP ZAP) 無高危漏洞

#### Task 1.2: 部署配置建置
**預估時間**: 3-4 天  
**負責模組**: 專案根目錄

**子任務**:
1. [ ] **Docker 容器化**
   ```dockerfile
   # 建立以下檔案
   - Dockerfile.api           # Core API (port 8000)
   - Dockerfile.dashboard     # Dashboard API (port 8001)
   - Dockerfile.web           # React frontend
   - docker-compose.yml       # Local development orchestration
   - docker-compose.prod.yml  # Production configuration
   ```

2. [ ] **Kubernetes 清單**
   ```yaml
   # k8s/ 目錄
   - deployment-api.yaml
   - deployment-dashboard.yaml
   - deployment-web.yaml
   - service-api.yaml
   - service-dashboard.yaml
   - ingress.yaml
   - configmap.yaml
   - secrets.yaml (template only)
   ```

3. [ ] **環境變數管理**
   ```bash
   # 建立範本檔案
   - .env.example               # Development template
   - .env.production.example    # Production template
   
   # 需要的變數
   SKILL0_DB_PATH=skills.db
   GOVERNANCE_DB_PATH=governance/db/governance.db
   CORS_ORIGINS=http://localhost:5173,http://localhost:3000
   JWT_SECRET_KEY=<generate-secure-key>
   API_RATE_LIMIT=100/minute
   LOG_LEVEL=INFO
   ```

4. [ ] **CI/CD Pipeline**
   ```yaml
   # .github/workflows/
   - test.yml         # Run pytest + npm test on PR
   - build.yml        # Build Docker images on push to main
   - deploy-dev.yml   # Deploy to dev environment
   - deploy-prod.yml  # Manual approval for production
   ```

**驗收標準**:
- [ ] `docker-compose up` 啟動完整堆疊
- [ ] Kubernetes 部署成功 (Minikube/Kind 測試)
- [ ] 所有環境變數從 ConfigMap/Secrets 載入
- [ ] CI pipeline 綠燈通過

#### Task 1.3: 儀表板後端服務完成
**預估時間**: 2-3 天  
**負責模組**: `skill-0-dashboard/apps/api/services/governance.py`

**子任務**:
1. [ ] **審查現有實作**
   - 檢查 `governance.py` (36,503 bytes) 的完整性
   - 確認資料庫 schema (`governance/db/governance.db`)
   - 驗證所有 router 呼叫的 service 方法存在且有效

2. [ ] **資料庫遷移系統**
   - 整合 Alembic (SQLAlchemy migrations)
   - 建立初始 migration: `alembic init alembic`
   - 記錄現有 schema: `alembic revision --autogenerate -m "initial schema"`

3. [ ] **修正資料庫路徑**
   - 將 `../../skills.db` 改為環境變數 `SKILL0_DB_PATH`
   - 確保路徑在容器環境中可正確解析

4. [ ] **補全缺失功能**
   - 實作所有 router 端點的實際邏輯 (非 mock)
   - 新增事務支援 (transaction management)
   - 新增錯誤回滾機制

**驗收標準**:
- [ ] 所有 API endpoints 返回真實資料 (非 mock)
- [ ] Database migrations 可執行
- [ ] 整合測試覆蓋所有 CRUD 操作

#### Task 1.4: Vector Search GPU Fallback *(v1.1 新增)*
**預估時間**: 0.5 天  
**負責模組**: `vector_db/embedder.py`

**子任務**:
1. [ ] **CUDA 可用性偵測**
   - 在 `SkillEmbedder.__init__()` 中加入 try/except
   - 嘗試載入 CUDA → 如失敗自動回退到 CPU
   - 記錄警告日誌：`WARNING: CUDA unavailable, falling back to CPU`

2. [ ] **環境變數支援**
   - 支援 `SKILL0_DEVICE=cpu|cuda|auto` 環境變數
   - 預設為 `auto` (先嘗試 CUDA, 失敗則 CPU)

3. [ ] **測試驗證**
   - 新增 unit test 確認 CPU fallback 邏輯
   - 在 CI 中驗證 (CI 環境通常無 GPU)

**驗收標準**:
- [ ] 無 GPU 環境下 vector search 正常運作 (無需手動設定 `CUDA_VISIBLE_DEVICES`)
- [ ] 有 GPU 但不相容時自動回退, 無 crash

---

### Phase 2: 測試覆蓋擴展 (優先級：P1)
### Phase 2: Testing Coverage Expansion (Priority: P1)

**目標**: 達到 80%+ 程式碼覆蓋率，確保系統穩定性

**Agent 分派**:
- A: 測試策略與覆蓋率規劃
- B: 高風險/易碎測試分析與穩定化
- C: API/後端整合測試實作
- D: 前端測試架構與文件
- E/F: 測試案例撰寫、fixtures、mock 資料

#### Task 2.1: API 整合測試
**預估時間**: 3-4 天  
**負責模組**: 新建 `tests/integration/`

**子任務**:
1. [ ] **Core API 測試**
   ```python
   # tests/integration/test_api_core.py
   - test_search_endpoint_returns_results()
   - test_similar_endpoint_with_valid_skill()
   - test_cluster_endpoint_grouping()
   - test_stats_endpoint_accuracy()
   - test_index_endpoint_reindex()
   - test_pagination_on_skills_list()
   - test_cors_headers_present()
   - test_rate_limiting_enforced()
   ```

2. [ ] **Dashboard API 測試**
   ```python
   # tests/integration/test_api_dashboard.py
   - test_stats_summary()
   - test_skills_list_pagination()
   - test_skill_detail_retrieval()
   - test_review_workflow_create_approve()
   - test_scan_execution_and_results()
   - test_audit_log_recording()
   ```

3. [ ] **資料庫狀態測試**
   - 使用 in-memory SQLite 進行隔離測試
   - 每個測試前後自動清理
   - 測試資料 fixtures

**驗收標準**:
- [ ] 50+ integration tests 通過
- [ ] 測試覆蓋所有 API endpoints
- [ ] CI pipeline 自動執行

#### Task 2.2: 前端測試
**預估時間**: 4-5 天  
**負責模組**: 新建 `skill-0-dashboard/apps/web/src/__tests__/`

**子任務**:
1. [ ] **單元測試 (Vitest + React Testing Library)**
   ```typescript
   // src/__tests__/components/
   - SkillsTable.test.tsx       // Table rendering, sorting, filtering
   - SkillDetail.test.tsx       // Detail view with security findings
   - StatCard.test.tsx          // Stats display
   - SecurityBadge.test.tsx     // Risk level badges
   ```

2. [ ] **整合測試 (API Mocking)**
   ```typescript
   // src/__tests__/pages/
   - Dashboard.test.tsx         // Dashboard with mocked API
   - SkillsPage.test.tsx        // Skills list with pagination
   - ReviewsPage.test.tsx       // Review workflow
   ```

3. [ ] **E2E 測試 (Playwright)**
   ```typescript
   // e2e/
   - dashboard.spec.ts          // Navigate dashboard, view stats
   - skills-search.spec.ts      // Search and filter skills
   - review-workflow.spec.ts    // Complete review process
   - authentication.spec.ts     // Login flow (after auth implemented)
   ```

**驗收標準**:
- [ ] 30+ 前端單元測試
- [ ] 10+ 整合測試
- [ ] 5+ E2E 測試
- [ ] 覆蓋率 > 70%

#### Task 2.3: 效能測試
**預估時間**: 2 天  
**負責模組**: 新建 `tests/performance/`

**子任務**:
1. [ ] **API 負載測試 (Locust)**
   ```python
   # tests/performance/locustfile.py
   - Search endpoint: 100 concurrent users
   - Skills list: pagination stress test
   - Index operation: measure time with large datasets
   ```

2. [ ] **資料庫查詢分析**
   - 使用 `EXPLAIN QUERY PLAN` 分析 SQLite queries
   - 識別缺失的索引
   - 最佳化 vector search queries

3. [ ] **前端效能 (Lighthouse)**
   - Performance score > 90
   - Accessibility score > 95
   - Best practices score > 90

**驗收標準**:
- [ ] API 在 100 QPS 下 p95 latency < 200ms
- [ ] Vector search < 100ms (目前宣稱 ~75ms)
- [ ] 前端 Lighthouse 分數達標

---

### Phase 3: 生產部署與監控 (優先級：P2)
### Phase 3: Production Deployment & Monitoring (Priority: P2)

**目標**: 建立可靠的監控與告警系統

**Agent 分派**:
- A: 監控/告警架構設計
- B: 風險分析與告警門檻校準
- C: 監控與日誌實作（structlog/Sentry/Prometheus）
- D: 部署/運維文件與 Runbook
- E/F: 腳本與設定調整（低風險）

#### Task 3.1: 日誌與監控
**預估時間**: 2-3 天

**子任務**:
1. [ ] **結構化日誌**
   ```python
   # 使用 structlog 或 python-json-logger
   - JSON 格式日誌
   - Request ID tracking
   - User context (after auth)
   - Error stack traces
   ```

2. [ ] **APM 整合**
   - Sentry for error tracking
   - Prometheus + Grafana for metrics
   - Health check endpoints: `/health`, `/ready`

3. [ ] **告警規則**
   - API 錯誤率 > 5%
   - Response time p95 > 500ms
   - Disk usage > 80%
   - Memory usage > 85%

**驗收標準**:
- [ ] 所有日誌為 JSON 格式
- [ ] Grafana dashboard 顯示關鍵指標
- [ ] 告警成功觸發 (測試環境)

#### Task 3.2: 資料庫優化
**預估時間**: 2 天

**子任務**:
1. [ ] **SQLite 生產配置**
   - WAL mode 啟用 (Write-Ahead Logging)
   - 自動 VACUUM 排程
   - 備份策略 (每日自動備份)

2. [ ] **未來擴展性評估**
   - 評估何時需要遷移到 PostgreSQL
   - 文件化遷移路徑
   - 預估 SQLite 承載上限 (concurrent users, DB size)

**驗收標準**:
- [ ] SQLite 以 WAL mode 運行
- [ ] 備份腳本每日執行
- [ ] 擴展性文件撰寫完成

#### Task 3.3: 文件更新
**預估時間**: 1-2 天

**子任務**:
1. [ ] **部署文件**
   - `docs/deployment-guide.md`: Step-by-step deployment instructions
   - `docs/operations-runbook.md`: Troubleshooting guide
   - `docs/architecture-overview.md`: System architecture diagram

2. [ ] **API 文件補全**
   - OpenAPI spec 補充 examples
   - Authentication flow 說明
   - Rate limiting 文件

3. [ ] **同步 README**
   - 更新統計數據 (if changed)
   - 修正已知不一致處 (e.g., 171 skills claim)

**驗收標準**:
- [ ] 新成員可依文件成功部署
- [ ] API docs 包含所有端點範例
- [ ] README 與實際狀態一致

---

### Phase 4: 功能增強 (優先級：P3)
### Phase 4: Feature Enhancements (Priority: P3)

**可選項目，視資源與時程決定**

**Agent 分派**:
- A: 高風險功能設計（Hybrid search/工作流）
- B: 需求推理與可行性分析
- C: 功能實作與整合
- D: 功能規格與使用說明
- E/F: 原型與快速試驗

#### Task 4.1: 儀表板功能完善
- [ ] Skill comparison view (side-by-side comparison)
- [ ] Batch operations (approve/reject multiple skills)
- [ ] Export reports (PDF/Excel)
- [ ] Advanced filtering (by category, risk level, date range)

#### Task 4.2: Vector Search 進階功能
- [ ] Multi-language support (embeddings for other languages)
- [ ] Hybrid search (keyword + semantic)
- [ ] Search history tracking
- [ ] Recommended skills based on user behavior

#### Task 4.3: 治理工作流增強
- [ ] Multi-stage approval workflow
- [ ] Commenting system on skills
- [ ] Change history tracking (skill versioning)
- [ ] Automated security scanning triggers

---

## 可執行工作清單 / Executable Worklist

### Phase 1 (P0)

**Task 1.1: API 安全性強化**
- **步驟**: CORS 白名單環境化、JWT 認證端點、Rate limiting、HTTPS reverse proxy 設定
- **驗收**: 受保護端點需 JWT；CORS 僅允許白名單；Rate limiting 生效
- **驗證指令**:
  - `python3 -m pytest tests/ -v`
  - `python3 -m pytest tests/integration -v` (新增後)

**Task 1.2: 部署配置建置**
- **步驟**: Dockerfile*3、docker-compose*2、k8s manifests、.env templates、CI workflows
- **驗收**: `docker-compose up` 可啟動完整堆疊；CI 綠燈
- **驗證指令**:
  - `docker compose up --build`
  - `kubectl apply -f k8s/` (若啟用)

**Task 1.3: 儀表板後端服務完成**
- **步驟**: 補齊 governance services、Alembic migrations、DB path env 化
- **驗收**: 所有 router 回傳真實資料；migrations 可跑
- **驗證指令**:
  - `python3 -m pytest tests/integration/test_api_dashboard.py -v` (新增後)
  - `cd skill-0-dashboard/apps/api && uvicorn main:app --reload --port 8001`

**Task 1.4: Vector Search GPU Fallback**
- **步驟**: CUDA failover、`SKILL0_DEVICE` 支援、單元測試
- **驗收**: 無 GPU 環境不崩潰；不相容 GPU 自動回退
- **驗證指令**:
  - `SKILL0_DEVICE=cpu python -m vector_db.search stats`
  - `python3 -m pytest tests/ -v`

### Phase 2 (P1)

**Task 2.1: API 整合測試**
- **步驟**: 建立 `tests/integration/`、覆蓋核心 API/Dashboard API
- **驗收**: 50+ integration tests 通過
- **驗證指令**: `python3 -m pytest tests/integration -v`

**Task 2.2: 前端測試**
- **步驟**: Vitest 單元測試、API mock 整合測試、Playwright E2E
- **驗收**: 30+ unit、10+ integration、5+ E2E
- **驗證指令**:
  - `cd skill-0-dashboard/apps/web && npm run test` (新增後)
  - `cd skill-0-dashboard/apps/web && npx playwright test` (新增後)

**Task 2.3: 效能測試**
- **步驟**: Locust 負載測試、SQLite query 分析、Lighthouse
- **驗收**: p95 < 200ms；Vector search < 100ms；Lighthouse 達標
- **驗證指令**:
  - `python3 -m locust -f tests/performance/locustfile.py` (新增後)
  - `cd skill-0-dashboard/apps/web && npx lighthouse http://localhost:5173`

### Phase 3 (P2)

**Task 3.1: 日誌與監控**
- **步驟**: structlog/json logger、Sentry/Prometheus、告警規則
- **驗收**: JSON logs；Grafana dashboard；告警可觸發
- **驗證指令**: `python3 -m pytest tests/integration -v` (新增監控相關測試後)

**Task 3.2: 資料庫優化**
- **步驟**: WAL、VACUUM 排程、備份腳本、擴展性評估文件
- **驗收**: WAL 啟用；備份可還原
- **驗證指令**: `python - <<'PY'
import sqlite3
conn = sqlite3.connect('skills.db')
print(conn.execute('PRAGMA journal_mode;').fetchone())
conn.close()
PY`

**Task 3.3: 文件更新**
- **步驟**: 部署/運維/架構文件、API examples、README 同步
- **驗收**: 新人可依文件部署；API docs 完整
- **驗證指令**:
  - `python3 -m pytest tests/ -v` (文件與行為一致性回歸)
  - `cd skill-0-dashboard/apps/web && npm run build`

### Phase 4 (P3)

**Task 4.1~4.3: 功能增強**
- **步驟**: 依需求拆分子任務，建立最小可用原型
- **驗收**: 功能可演示、風險可控、效能可接受
- **驗證指令**: 依功能新增對應 unit/integration/E2E 測試

## 第三部分：資源需求與時程估算
## Part 3: Resource Requirements & Timeline Estimation

### 人力需求 / Staffing

| 角色 | 技能要求 | 工作量 (人日) |
|------|----------|--------------|
| **Backend Engineer** | FastAPI, SQLite, Security | 15-20 人日 |
| **Frontend Engineer** | React, TypeScript, Testing | 10-15 人日 |
| **DevOps Engineer** | Docker, Kubernetes, CI/CD | 8-12 人日 |
| **QA Engineer** | Pytest, Playwright, Load Testing | 10-12 人日 |
| **Technical Writer** | Documentation, API Specs | 3-5 人日 |

**總計**: 46-64 人日 (約 2-3 個月，2-3 人團隊)

### 多 Agents 分組（目的 / 預算）

> 依 A/B 測試結果重新分組（o4-mini / gpt-5.1-codex-mini / gpt-5.2-codex low+medium）。

| Agent | 目的 / 角色 | 模型 | 預算層級 |
|------|------------|------|----------|
| **A** | 架構與關鍵設計 | `gpt-5.2-codex (medium)` | 高 |
| **B** | 高風險推理 / 根因分析 | `o4-mini` | 高 |
| **C** | 功能實作 / API 改動 | `gpt-5.2-codex (low)` | 中 |
| **D** | 文件 / 技術規格 | `gpt-5.2-codex (medium)` | 中 |
| **E** | 低風險修正 / 小改動 | `gpt-5.1-codex-mini` | 低 |
| **F** | 探索 / 雜務 / 快速嘗試 | `gpt-5.1-codex-mini` | 低 |

**使用原則**:
- 高風險與長推理任務優先走 A/B
- 大量小任務與試探性工作走 E/F
- API 實作類工作預設走 C

### 時程規劃 / Timeline

```
Week 1-2: Phase 1 (Security & Deployment Config)
  ├─ Week 1: API security + CORS/Auth/Rate limiting
  └─ Week 2: Docker/K8s + CI/CD setup

Week 3-4: Phase 1 (Dashboard Backend) + Phase 2 Start
  ├─ Week 3: Governance services completion + DB migrations
  └─ Week 4: API integration tests + Frontend unit tests

Week 5-6: Phase 2 (Testing)
  ├─ Week 5: E2E tests + Performance testing
  └─ Week 6: Test coverage analysis + bug fixes

Week 7-8: Phase 3 (Production Prep)
  ├─ Week 7: Logging/Monitoring + Database optimization
  └─ Week 8: Documentation + Deployment dry-run

Week 9+: Phase 4 (Optional Enhancements)
  └─ Feature prioritization based on user feedback
```

### 風險評估 / Risk Assessment

| 風險 | 可能性 | 影響 | 緩解策略 |
|------|--------|------|----------|
| **認證系統複雜度** | 中 | 高 | 使用成熟套件 (fastapi-users), 預留緩衝時間 |
| **資料庫遷移問題** | 中 | 高 | 先在測試環境驗證, 準備回滾方案 |
| **前端測試延遲** | 高 | 中 | 優先覆蓋關鍵路徑, 分階段增加覆蓋率 |
| **K8s 學習曲線** | 中 | 中 | 先用 Docker Compose, K8s 為選配 |
| **效能瓶頸** | 低 | 高 | 提早進行負載測試, 預留最佳化時間 |

---

## 第四部分：優先級建議
## Part 4: Priority Recommendations

### 🚨 立即執行 (本週內)
1. **CORS 限制** - 修改 2 個檔案, 30 分鐘
2. **環境變數範本** - 建立 `.env.example`, 1 小時
3. **基礎 Dockerfile** - API + Web 容器化, 4 小時
4. **Vector Search GPU Fallback** - 修改 `vector_db/embedder.py`, 2 小時 *(v1.1 新增)*
5. ~~修復重複檔案~~ ✅ 已完成 (`dependencies.py`, `schemas/review.py`, `requirements.txt`) *(v1.1)*
6. ~~刪除垃圾檔案~~ ✅ 已完成 (`## Chat Customization Diagnostics.md`) *(v1.1)*

### ⚡ 短期 (2 週內)
1. **JWT 認證** - 保護 API, 3-4 天
2. **Docker Compose** - 本地開發堆疊, 2 天
3. **API 整合測試** - 核心端點, 3 天
4. **儀表板服務完成** - Governance workflow, 2-3 天
5. **擴充 CI Pipeline** - 加入 pytest + web build + dashboard tests, 1 天 *(v1.1 新增)*
6. **同步 Governance DB 與 Vector DB** - 將 131 個缺失技能索引到 vector store, 1-2 天 *(v1.1 新增)*

### 📅 中期 (1 個月內)
1. **CI/CD Pipeline** - GitHub Actions, 2 天
2. **前端測試套件** - Unit + E2E, 5 天
3. **監控系統** - Prometheus + Grafana, 3 天
4. **部署文件** - 完整指南, 2 天

### 🎯 長期 (2-3 個月內)
1. **Kubernetes 部署** - 生產級配置, 1 週
2. **效能最佳化** - Load testing + tuning, 1 週
3. **進階功能** - Phase 4 項目, 視需求

---

## 第五部分：成功指標
## Part 5: Success Metrics

### 技術指標 / Technical Metrics

| 指標 | 目前狀態 | 目標 | 驗證方式 |
|------|----------|------|----------|
| **測試覆蓋率** | ~40% (僅 unit tests) | >80% | `pytest --cov` |
| **API Response Time (p95)** | Unknown | <200ms | Locust report |
| **Vector Search Latency** | ~75ms (宣稱) | <100ms (驗證) | Performance test |
| **Build Time** | ~30s (Web) | <60s | CI logs |
| **安全漏洞** | 2 critical (CORS, no auth) | 0 critical | OWASP ZAP scan |
| **文件完整性** | 70% | 95% | Manual review |

### 部署指標 / Deployment Metrics

| 指標 | 目標 |
|------|------|
| **首次部署時間** | <30 分鐘 (from git clone to running) |
| **CI Pipeline 時間** | <10 分鐘 (test + build) |
| **部署成功率** | >95% |
| **Rollback 時間** | <5 分鐘 |

### 可用性指標 / Availability Metrics

| 指標 | 目標 |
|------|------|
| **Uptime** | >99.5% |
| **MTTR (Mean Time To Recover)** | <1 小時 |
| **Error Rate** | <1% |

---

## 第六部分：技術債務清單
## Part 6: Technical Debt Inventory

### 高優先級 / High Priority

1. **安全性債務**
   - 檔案: `api/main.py`, `skill-0-dashboard/apps/api/main.py`
   - 問題: CORS 全開放, 無認證
   - 預估修復: 3-4 天

2. **測試債務**
   - 檔案: 缺失整個 `tests/integration/` 目錄
   - 問題: 無 API 整合測試, 無前端測試
   - 預估修復: 1 週

3. **部署債務**
   - 檔案: 無 Docker/K8s 配置
   - 問題: 無法自動化部署
   - 預估修復: 1 週

### 中優先級 / Medium Priority

4. **程式碼重複**
   - 檔案: `tools/advanced_skill_analyzer.py` + `tools/skill_scanner.py`
   - 問題: Security patterns 重複
   - 預估修復: 2 小時 (extract to common module)

5. **硬編碼配置**
   - 檔案: 多個檔案 (DB paths, API URLs)
   - 問題: 無法靈活配置環境
   - 預估修復: 1 天

6. **日誌系統**
   - 檔案: 所有 API 檔案
   - 問題: 無結構化日誌
   - 預估修復: 2 天

### 低優先級 / Low Priority

7. **依賴版本鎖定**
   - 檔案: `requirements.txt`, `package.json`
   - 問題: 使用範圍版本
   - 預估修復: 1 小時 (generate lock files)

8. **文件同步**
   - 檔案: `README.md`, `tools/AGENTS.md`
   - 問題: 部分描述過時
   - 預估修復: 2-3 小時

---

## 第七部分：建議行動方案
## Part 7: Recommended Action Plan

### 立即行動 (今日)

```bash
# 1. 修正 CORS (30 分鐘)
# 修改 api/main.py 和 skill-0-dashboard/apps/api/main.py
# 將 allow_origins=["*"] 改為環境變數

# 2. 建立環境變數範本 (1 小時)
cat > .env.example <<EOF
SKILL0_DB_PATH=skills.db
GOVERNANCE_DB_PATH=governance/db/governance.db
CORS_ORIGINS=http://localhost:5173
JWT_SECRET_KEY=your-secret-key-here
API_RATE_LIMIT=100/minute
LOG_LEVEL=INFO
EOF

# 3. 提交當前進度 (已完成 merge conflict 解決)
git commit -m "chore: resolve merge conflicts and verify build"
git push origin main
```

### 本週行動 (Week 1)

1. **星期一**: 實作 JWT 認證基礎架構
2. **星期二**: 新增 rate limiting
3. **星期三**: 建立基礎 Dockerfile (API + Web)
4. **星期四**: 撰寫 docker-compose.yml
5. **星期五**: API 整合測試 (前 10 個端點)

### 下週行動 (Week 2)

1. **星期一-二**: 完成 Governance services
2. **星期三-四**: 設定 CI/CD pipeline
3. **星期五**: 第一次生產環境部署測試

---

## 附錄 A：檔案變更清單
## Appendix A: File Change Inventory

### 需要修改的檔案 / Files to Modify

```
api/main.py                                    # CORS + Auth
skill-0-dashboard/apps/api/main.py             # CORS + Auth
skill-0-dashboard/apps/api/services/governance.py  # Complete implementation
skill-0-dashboard/apps/api/config.py           # Add env vars
vector_db/embedder.py                          # GPU fallback (v1.1)
.github/workflows/ci.yml                       # Expand CI coverage (v1.1)
```

### 已修改的檔案 / Files Already Modified *(v1.1 新增)*

```
✅ skill-0-dashboard/apps/api/dependencies.py       # Deduplicated
✅ skill-0-dashboard/apps/api/schemas/review.py      # Deduplicated
✅ skill-0-dashboard/apps/api/requirements.txt       # Deduplicated
✅ ## Chat Customization Diagnostics.md               # Deleted (stale)
```

### 需要建立的檔案 / Files to Create

```
.env.example                                   # Environment template
Dockerfile.api                                 # Core API container
Dockerfile.dashboard                           # Dashboard API container
Dockerfile.web                                 # Frontend container
docker-compose.yml                             # Local development
docker-compose.prod.yml                        # Production config
.github/workflows/test.yml                     # CI pipeline
.github/workflows/deploy.yml                   # CD pipeline
tests/integration/test_api_core.py             # API tests
tests/integration/test_api_dashboard.py        # Dashboard tests
tests/performance/locustfile.py                # Load tests
skill-0-dashboard/apps/web/src/__tests__/      # Frontend tests directory
docs/deployment-guide.md                       # Deployment docs
docs/operations-runbook.md                     # Operations guide
k8s/deployment-api.yaml                        # K8s manifest (optional)
```

---

## 附錄 B：關鍵決策點
## Appendix B: Key Decision Points

### 決策 1: 資料庫選擇

**現狀**: SQLite (開發與生產皆使用)  
**問題**: SQLite 不適合高併發寫入  
**選項**:
- A. 繼續使用 SQLite (簡單, 適合低流量)
- B. 遷移至 PostgreSQL (複雜, 適合擴展)
- C. 混合: 讀操作用 SQLite, 寫操作用 PostgreSQL

**建議**: 選項 A (短期) → C (中期) → B (長期)

### 決策 2: 認證策略

**選項**:
- A. 自建 JWT (靈活, 需維護)
- B. 使用 `fastapi-users` (成熟, 快速)
- C. OAuth 2.0 (適合企業)

**建議**: 選項 B (開發速度優先)

### 決策 3: 前端狀態管理

**現狀**: TanStack Query (已整合)  
**是否需要**: Redux/Zustand?

**建議**: 目前無需額外狀態管理 (TanStack Query 足夠)

### 決策 4: 部署目標

**選項**:
- A. 單機 Docker (簡單)
- B. Kubernetes (複雜, 可擴展)
- C. Managed PaaS (Heroku, Vercel, AWS App Runner)

**建議**: 選項 A (Phase 1-2) → B (Phase 3+)

---

## 附錄 C：聯絡資訊與資源
## Appendix C: Contact & Resources

### 技術支援資源

- **FastAPI 文件**: https://fastapi.tiangolo.com
- **React Router 7**: https://reactrouter.com/en/main
- **SQLite-vec**: https://github.com/asg017/sqlite-vec
- **Docker 最佳實踐**: https://docs.docker.com/develop/dev-best-practices/
- **OWASP API Security**: https://owasp.org/API-Security/

### 專案文件連結

- 專案倉庫: (請填入實際 Git URL)
- 問題追蹤: (請填入 Issue Tracker URL)
- CI/CD 狀態: (請填入 CI Dashboard URL)

---

## 結論 / Conclusion

Skill-0 專案已具備堅實的技術基礎，核心功能完整且經過測試驗證。當前主要缺口集中在**生產部署準備**與**測試覆蓋擴展**，這些都是可量化且可在 2-3 個月內完成的任務。

**關鍵建議**:
1. 優先解決安全性問題 (CORS + 認證) - 這是上線的阻擋因素
2. 建立 Docker 容器化 - 簡化部署流程
3. 擴展測試覆蓋 - 確保系統穩定性
4. 逐步實作監控 - 為生產運營做準備

遵循本計畫書，專案可在 **8-10 週**內達到生產就緒狀態。

---

**文件版本**: v1.1  
**最後更新**: 2026-02-11  
**下次審查**: 2026-02-18 (1 週後)
