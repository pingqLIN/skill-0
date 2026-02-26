# Skill-0 開發計畫 v2.0

> 基於 2026-02-26 專案審計，修正 FINAL_PHASE_PLAN.md 中已過時的評估
>
> **架構原則**：Opus 規劃與驗收、Sonnet 4.6 撰寫代碼、子代理（tb2）輔助

---

## 角色分工

| 角色 | 模型 | 職責 |
|------|------|------|
| **Architect / Reviewer** | Claude Opus 4.6 | 規劃、設計決策、Code Review、驗收測試 |
| **Primary Coder** | Claude Sonnet 4.6 | 專案代碼撰寫、測試實作、配置檔建立 |
| **Sub-agent: Code Gen** | GPT-5.3-codex (tb2) | 重複性代碼生成、boilerplate、批量轉換 |
| **Sub-agent: Review** | Gemini 3.1 Pro (tb2) | 安全審計、依賴漏洞掃描、文件校對 |

---

## 已完成項目確認（無需重做）

以下項目在最新 commit 中已驗證完成：

- [x] CORS 環境變數化（兩個 FastAPI 應用）— commit `501596f`
- [x] JWT 認證框架（api/main.py）— commit `501596f`
- [x] Docker 容器化（3 Dockerfile + 2 docker-compose）— commit `c71b84a`
- [x] GPU fallback 機制（vector_db/embedder.py `_resolve_device()`）— commit `c71b84a`
- [x] 資料庫路徑環境變數化 — commit `c71b84a`
- [x] Schema v2.4.0 + Hive features — commit `6d96be5`
- [x] Windows 啟動腳本 — commit `cffb9ec`
- [x] Docker healthcheck 修復 — commit `5875a8a`

---

## 真正待完成項目（4 個 Sprint）

### Sprint 1：CI/CD 補完 + Rate Limiting 驗證（P0）
**預估：1-2 天 | 執行者：Sonnet 4.6**

#### Task 1.1 — 擴展 CI Pipeline
**目標**：`.github/workflows/ci.yml` 目前僅有 flake8 + JSON schema 驗證，需補充

```yaml
# 需要添加的 CI 步驟：
- pytest 單元測試（32 個既有測試）
- pytest 覆蓋率報告（coverage >= 80%）
- Dashboard web build 驗證（npm run build）
- Dashboard API 啟動驗證
- Docker image build 驗證（不 push）
```

**檔案變更**：
- `修改` `.github/workflows/ci.yml`

**驗收標準（Opus）**：
- [ ] CI 在 GitHub Actions 上 green pass
- [ ] 測試失敗時 CI 正確 fail
- [ ] PR 觸發 CI 自動執行

#### Task 1.2 — Rate Limiting 狀態確認與補完
**目標**：確認 `api/main.py` 中 Rate Limiting 是否真正生效

**調查項目**：
- `API_RATE_LIMIT` 和 `AUTH_RATE_LIMIT` 環境變數已定義
- 但需確認是否有 `slowapi` 或類似中介軟體真正掛載
- 若未掛載，由 Sonnet 實作

**檔案變更**：
- `修改` `api/main.py`（如有需要）
- `修改` `requirements.txt`（如需新增 slowapi）

**驗收標準（Opus）**：
- [ ] 連續請求超過限制時返回 429
- [ ] 不同端點有不同限制（auth 更嚴格）

#### Task 1.3 — 儀表板 API 認證對齊
**目標**：主 API 已有 JWT，但 Dashboard API（port 8001）無認證

**設計決策（Opus 決定）**：
- 方案 A：Dashboard API 共用主 API 的 JWT 模組 → **採用**
- 方案 B：Dashboard API 獨立認證系統 → 拒絕（增加複雜度）

**檔案變更**：
- `修改` `skill-0-dashboard/apps/api/main.py`
- `新增` `skill-0-dashboard/apps/api/auth.py`（從主 API 提取共用模組）

**驗收標準（Opus）**：
- [ ] 未帶 token 的請求被拒絕（401）
- [ ] /health 端點免認證
- [ ] /docs 端點在 development 環境可訪問

---

### Sprint 2：測試覆蓋率提升（P1）
**預估：2-3 天 | 執行者：Sonnet 4.6 + GPT-5.3-codex**

#### Task 2.1 — Dashboard API 測試（Sonnet 主導）
**目標**：從零建立 Dashboard API 測試套件

**測試範圍**：
```
tests/dashboard/
├── test_stats_router.py      # 統計端點
├── test_skills_router.py     # 技能列表/詳情
├── test_reviews_router.py    # 審核流程
├── test_scans_router.py      # 掃描結果
├── test_audit_router.py      # 稽核日誌
└── conftest.py               # fixtures (test DB, client)
```

**指派策略**：
- **Sonnet**：撰寫 conftest.py、核心業務邏輯測試（stats、skills、reviews）
- **GPT-5.3-codex**：生成 scans、audit 的 boilerplate 測試案例（結構重複性高）

**驗收標準（Opus）**：
- [ ] >= 30 個測試案例
- [ ] 覆蓋所有 5 個 router 的主要端點
- [ ] 所有測試 pass

#### Task 2.2 — 主 API 整合測試（Sonnet 主導）
**目標**：測試跨模組互動（API → Vector DB → 回應）

**測試範圍**：
```
tests/integration/
├── test_search_flow.py       # 搜尋端點 → embedder → vector DB
├── test_skill_crud.py        # 技能 CRUD 完整流程
├── test_auth_flow.py         # 登入 → token → 受保護端點
└── test_rate_limiting.py     # 超限 → 429
```

**驗收標準（Opus）**：
- [ ] >= 20 個整合測試
- [ ] 測試使用獨立 test DB（不影響 production data）
- [ ] CI 中執行不超過 60 秒

#### Task 2.3 — 前端基礎測試（Sonnet + codex）
**目標**：建立前端測試基礎設施

**範圍限定**（避免過度工程）：
- 安裝 Vitest + @testing-library/react
- 撰寫 5-10 個核心元件的 smoke test
- 不追求高覆蓋率，優先確保 build 不壞

**指派策略**：
- **Sonnet**：配置 Vitest、撰寫 App.test.tsx
- **GPT-5.3-codex**：批量生成元件 smoke test（render + 不 crash）

**驗收標準（Opus）**：
- [ ] `npm test` 可執行且通過
- [ ] CI 中整合前端測試步驟

---

### Sprint 3：資料一致性 + 監控（P1-P2）
**預估：1.5 天 | 執行者：Sonnet 4.6**

#### Task 3.1 — 資料庫同步修復
**目標**：Governance DB 163 筆 vs Vector DB 32 筆，填補 131 筆落差

**方案**：
- 建立同步腳本 `scripts/sync_vector_db.py`
- 從 governance DB 讀取所有已核准技能
- 若對應 parsed JSON 存在 → 嵌入並寫入 vector DB
- 若不存在 → 記錄到 `sync_report.log`

**檔案變更**：
- `新增` `scripts/sync_vector_db.py`
- `修改` `scripts/` 中可能需要的工具

**驗收標準（Opus）**：
- [ ] 同步後 Vector DB 涵蓋所有有 parsed JSON 的技能
- [ ] 同步腳本可重複執行（冪等性）
- [ ] 產出同步報告

#### Task 3.2 — 結構化日誌
**目標**：替換 print/logging 為 structlog

**範圍**：
- 主 API 和 Dashboard API 加入 structlog
- JSON 格式輸出（適合 ELK/CloudWatch）
- 請求 ID 串聯（已有 `request_id_var`，需整合）

**檔案變更**：
- `修改` `api/main.py`
- `修改` `skill-0-dashboard/apps/api/main.py`
- `修改` `requirements.txt`

**驗收標準（Opus）**：
- [ ] 日誌為 JSON 格式
- [ ] 每個請求有唯一 request_id
- [ ] 錯誤日誌包含 stack trace

---

### Sprint 4：文件同步 + 收尾（P2）
**預估：1 天 | 執行者：Sonnet 4.6 + Gemini 3.1 Pro**

#### Task 4.1 — README 與實際狀態同步
**目標**：修正 README.md 中的過時數據

**調查項目**（Gemini 3.1 Pro 負責校對）：
- 技能數量：README 聲稱 171 → 核實實際數量
- API 端點清單是否完整
- 架構圖是否反映 v2.4.0
- 安裝步驟是否可重現

**檔案變更**：
- `修改` `README.md`
- `修改` `README.zh-TW.md`

#### Task 4.2 — CI/CD 最終驗證
**目標**：確保完整 pipeline 可運作

**驗收標準（Opus）**：
- [ ] Push → CI 觸發 → 全綠
- [ ] Docker build 在 CI 中成功
- [ ] 測試報告可在 PR 中查看

#### Task 4.3 — 依賴版本鎖定
**目標**：消除破壞性升級風險

**執行**：
- Python：`pip freeze > requirements.lock`
- Node：確認 `package-lock.json` 存在且 up-to-date

---

## 執行排程總覽

```
Sprint 1 ──▶ Sprint 2 ──▶ Sprint 3 ──▶ Sprint 4
CI/Rate      Testing      Data/Logs    Docs/Final
(1-2 天)     (2-3 天)     (1.5 天)     (1 天)

總計：約 5.5-7.5 個工作天
```

## 工作流程

```
┌─────────┐     設計 / 規格     ┌────────────┐
│  Opus   │ ──────────────────▶ │  Sonnet    │
│ 規劃者  │                     │  實作者    │
│ 驗收者  │ ◀────────────────── │            │
└─────────┘     PR / 成品       └────────────┘
     │                               │
     │  安全審計 / 文件校對          │  重複性代碼
     ▼                               ▼
┌────────────┐               ┌──────────────┐
│ Gemini 3.1 │               │ GPT-5.3      │
│ Pro (tb2)  │               │ Codex (tb2)  │
└────────────┘               └──────────────┘
```

## 每個 Task 的執行循環

1. **Opus** 定義 Task 規格與驗收標準
2. **Sonnet** 實作代碼（使用 Task tool 以 worktree 隔離）
3. **Sub-agents**（如適用）生成輔助代碼
4. **Opus** Review 成品：
   - 讀取變更的檔案
   - 執行測試驗證
   - 檢查是否符合驗收標準
5. 通過 → 合併；不通過 → 回饋 Sonnet 修正

---

## 風險與緩解

| 風險 | 影響 | 緩解措施 |
|------|------|----------|
| Dashboard API 結構複雜，測試難寫 | Sprint 2 延遲 | 優先 smoke test，逐步加深 |
| 163 筆技能中部分無 parsed JSON | 同步不完整 | 同步報告標記缺失項，不阻擋 |
| 子代理 API 不穩定 | 輔助代碼延遲 | Sonnet 可獨立完成所有任務（子代理為加速用） |
| CI 環境與本地差異 | 測試本地過但 CI 失敗 | Docker-based CI 確保一致性 |

---

*計畫由 Claude Opus 4.6 於 2026-02-26 制定*
*版本：v2.0 — 基於最新 codebase 審計*
