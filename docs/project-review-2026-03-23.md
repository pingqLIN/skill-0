# Skill-0 專案進度審查報告

**審查日期：2026-03-23**
**更新日期：2026-03-23**
**審查者：project-review-advisor + 後續實作驗證整合**
**對應報告：** `docs/project-progress-report-2026-03-23.md`

---

## 一、最新結論

Skill-0 目前的狀態已經從「功能缺口主導」進到「部署穩定性與營運風險主導」。

先前 review 中最急迫的幾個問題，現在狀態如下：

| 項目 | 先前判斷 | 目前狀態 |
|------|----------|----------|
| Dashboard Web 無 JWT/session flow | 高風險 | **已處理** |
| Recent Activity 是 placeholder | 中高風險 | **已處理** |
| Bulk Approve Safe 未接線 | 中高風險 | **已處理** |
| CI 無 coverage gate | 中風險 | **已處理** |
| Node 18 / 20 漂移導致 frontend test 異常 | 高風險 | **已定位且已驗證** |
| Production SQLite 無持久化 volume | Critical | **已處理且已完成 restart 驗證** |
| API 容器 OOM 風險 | High | **仍成立** |
| 雙 SQLite 一致性 / 備份策略 | Medium-High | **仍成立** |

---

## 二、已確認完成的修復

### 1. 前端 JWT / Session 補齊

已補上：

- login route
- token 儲存
- axios Bearer interceptor
- `401` 自動清 session
- protected routes
- dev / production-aware API base URL

主要檔案：

- [skill-0-dashboard/apps/web/src/api/client.ts](/home/miles/dev2/skill-0/skill-0-dashboard/apps/web/src/api/client.ts)
- [skill-0-dashboard/apps/web/src/auth/AuthProvider.tsx](/home/miles/dev2/skill-0/skill-0-dashboard/apps/web/src/auth/AuthProvider.tsx)
- [skill-0-dashboard/apps/web/src/auth/context.ts](/home/miles/dev2/skill-0/skill-0-dashboard/apps/web/src/auth/context.ts)
- [skill-0-dashboard/apps/web/src/auth/useAuth.ts](/home/miles/dev2/skill-0/skill-0-dashboard/apps/web/src/auth/useAuth.ts)
- [skill-0-dashboard/apps/web/src/pages/Login.tsx](/home/miles/dev2/skill-0/skill-0-dashboard/apps/web/src/pages/Login.tsx)
- [skill-0-dashboard/apps/web/src/App.tsx](/home/miles/dev2/skill-0/skill-0-dashboard/apps/web/src/App.tsx)

### 2. Dashboard 首頁 Recent Activity 已補成真資料

首頁不再是 placeholder，現在會直接顯示 audit feed。

主要檔案：

- [skill-0-dashboard/apps/web/src/pages/Dashboard.tsx](/home/miles/dev2/skill-0/skill-0-dashboard/apps/web/src/pages/Dashboard.tsx)

### 3. Bulk Approve Safe 已實作

Review Queue 的 safe / low risk skills 現在可批次核准。

主要檔案：

- [skill-0-dashboard/apps/web/src/pages/ReviewQueue.tsx](/home/miles/dev2/skill-0/skill-0-dashboard/apps/web/src/pages/ReviewQueue.tsx)

### 4. CI coverage gate 已補上

pytest 現在帶有 `--cov-fail-under=75`。

主要檔案：

- [.github/workflows/ci.yml](/home/miles/dev2/skill-0/.github/workflows/ci.yml)

### 5. Node 版本對齊已補上

已新增：

- `.nvmrc`
- frontend `engines.node >= 20.19.0`

主要檔案：

- [.nvmrc](/home/miles/dev2/skill-0/.nvmrc)
- [skill-0-dashboard/apps/web/package.json](/home/miles/dev2/skill-0/skill-0-dashboard/apps/web/package.json)

### 6. Production DB persistence 與 compose runtime 已驗證

已補上並驗證：

- `docker-compose.prod.yml` 已改為可獨立使用的 production compose
- named volumes 已接上 `skills.db` 與 `governance.db`
- API image 已修正 DB seed 路徑
- Dashboard image / service 已修正 `tools` 路徑解析
- compose restart 後 DB 與健康檢查皆可恢復

主要檔案：

- [docker-compose.prod.yml](/home/miles/dev2/skill-0/docker-compose.prod.yml)
- [Dockerfile.api](/home/miles/dev2/skill-0/Dockerfile.api)
- [Dockerfile.dashboard](/home/miles/dev2/skill-0/Dockerfile.dashboard)

---

## 三、最新驗證結果

### Frontend

- `npm run lint`：passed
- `npm run build`：passed
- `npm run build:ci`：passed
- `npm test`：**在 Node `20.19.0` 下 passed（18 tests）**

### Docker build

- `docker build -f Dockerfile.dashboard -t skill-0-dashboard:test .`：passed
- `docker build -f Dockerfile.web -t skill-0-web:test .`：passed
- `docker build -f Dockerfile.api -t skill-0-api:test .`：passed
- `docker compose -f docker-compose.prod.yml config`：passed
- `docker compose -f docker-compose.prod.yml up -d --build`：passed
- `POST /api/auth/token` + `GET /dashboard-api/api/stats`：passed
- compose restart 後 `API / dashboard` health 與 DB persistence：passed

補充：

- `api` image build 的主要瓶頸仍是 `torch` wheel 下載，過程顯著慢於其他兩個 image
- 為避開本機既有 `3000` 佔用，production compose 的 web 預設對外 port 已調整為 `3080`

---

## 四、仍然成立的風險

### 🔴 High Priority

#### 1. API 容器 OOM 風險仍成立

- `sentence-transformers` + `torch` 在 CPU 模式下的記憶體壓力仍高
- `docker-compose.prod.yml` 的 API 上限目前已提升為 `1G`
- 這是部署風險，不是功能風險

建議：

- 實際量測容器峰值記憶體
- 若接近上限，提升到 `768M` 或 `1G`
- 若後續查詢量增長，考慮把 embedding / search 進一步拆服務

#### 2. 雙 SQLite 架構的一致性與備份策略仍未解

目前仍是：

- `skills.db` 負責向量搜尋
- `governance/db/governance.db` 負責治理與 dashboard

風險：

- skill identity 一致性依賴應用層
- 備份與恢復流程未明文化
- 寫入壓力上升時仍可能遇到 SQLite 競爭問題

#### 3. Production persistence 已驗證，但仍缺備份策略

目前已確認：

- 容器重啟後 DB 仍保留
- named volume 可正常寫入
- compose `up` 與 `restart` 皆能恢復

剩餘風險在於：

- 備份與還原流程尚未制度化
- 多實例或高寫入場景仍未驗證

### 🟠 Medium-High

#### 4. `source_path` / `installed_path` 仍是高信任模型

治理流程對 DB 中記錄的路徑仍有高度信任。

建議：

- 限制允許根目錄
- 對路徑做 resolve 後的範圍檢查
- 避免未經約束的路徑探查

#### 5. Core API 公開搜尋端點是否符合產品設計，仍需明確決策

目前搜尋端點大多為公開 API。這不一定是 bug，但需要明確設計決策：

- 如果這些端點預期公開，現況可接受
- 如果不預期公開，就需要加上 auth / rate limit / docs 限制

#### 6. 搜尋與治理操作的執行模型仍可再強化

目前部分重操作仍偏同步：

- 搜尋失敗時的錯誤處理可更明確
- scan / test batch 若持續增長，未來可能需要 worker queue 或 background job

### 🟡 Medium

#### 7. Schema / docs 版本號仍需一致化

不同文件與程式中的版本號仍可能不同步，這會影響：

- 文件可信度
- AI agent 依據舊版 schema 工作
- 使用者對相容性的判斷

#### 8. README / onboarding 尚未完全追上新基線

雖然 `.nvmrc` 與 `engines` 已補上，但 README 尚未完全同步：

- `nvm use`
- Node 20.19 基線
- frontend auth flow
- production persistence 驗證方式

---

## 五、建議的最新優先序

### 本輪最值得做的事

1. 量測 API 容器記憶體峰值，確認 `1G` 是否足夠
2. 補備份 / 還原流程與操作文件
3. 決定 Core API 搜尋端點是否應保持公開
4. 針對模型冷啟動與 `HF_TOKEN` 做部署策略
5. 補 README / onboarding 的 production 營運細節

### 不再是優先缺口的項目

以下項目已不應繼續占用最高優先級：

- 前端 token 注入
- Recent Activity placeholder
- Bulk Approve 功能缺失
- frontend test broken state（已確認是 Node 18 runtime mismatch）

---

## 六、總結

Skill-0 現在的問題重心已經改變。

先前 review 的前幾個高風險項目，多數已在這輪實作中被處理掉。專案目前不再主要卡在 dashboard 功能空洞，而是卡在：

- production runtime 可靠性
- Docker / volume / memory 驗證
- 雙 SQLite 架構的治理成本
- 文件與環境基線的一致性

如果只看目前狀態，這個專案已經達到「可交付並可送外部技術審核」的基線，但離「可放心上 production」仍差容量、備份與營運級驗證的最後一段收尾。
