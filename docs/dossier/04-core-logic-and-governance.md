# 04. Core Logic and Governance

## 4.1 Core Logical Layers

從邏輯角度看，Skill-0 可以拆成四層：

1. 表示層：schema 與 parsed JSON
2. 搜尋層：embedding、向量索引、semantic search
3. 治理層：skill metadata、scan、test、approval、audit
4. 呈現層：dashboard API 與 web UI

這四層彼此銜接，但責任邊界相對清楚。

## 4.2 Decomposition Logic

Skill-0 的第一個邏輯核心，是把技能拆成：

- Actions
- Rules
- Directives

這層邏輯的價值不在於分類本身，而在於它把技能變成：

- 可驗證
- 可查詢
- 可比較
- 可治理

一旦 skill 已被轉為統一 schema，後續所有功能才有共同輸入格式。

## 4.3 Semantic Search Logic

搜尋層的邏輯是：

1. 從 `parsed/` 讀取 skill JSON
2. embedder 讀取名稱、描述與結構資訊生成 embedding
3. embedding 寫入 SQLite-vec
4. 搜尋時把 query 也轉成 embedding
5. 透過近鄰查找回傳候選 skill
6. API 把距離轉為較易閱讀的 similarity

這個設計有幾個特點：

- query 不需要依賴精確關鍵字
- skill discovery 可以跨名稱與描述用語差異
- 相似技能查找與聚類都可建立在同一向量基礎上

## 4.4 Search API Logic

core API 主要分成幾種端點：

- 查詢型：`/api/search`、`/api/similar`、`/api/cluster`、`/api/stats`、`/api/skills`
- 管理型：`/api/index`
- 認證型：`/api/auth/token`、`/api/auth/me`
- 健康與觀測：`/health`、`/metrics`

從邏輯上看，這些端點形成兩條路徑：

### Public query path

- skill inventory query
- semantic search
- stats and discovery

### Controlled admin path

- re-index
- auth-protected operations

這表示 core API 雖然以搜尋為主，但已經有基本的平台管理職責。

## 4.5 Governance Logic

治理層邏輯主要圍繞 skill 的生命週期管理。

一個 skill 在治理層可能經歷：

1. 被註冊到 governance DB
2. 填入來源、作者、授權與格式資訊
3. 被 security scan
4. 被 equivalence test
5. 根據風險與測試結果進入 pending / approved / rejected / blocked
6. 所有關鍵操作寫入 audit log

治理層的核心並不只是「批准或拒絕」，而是把每一步都變成可被查詢與追蹤的資料。

## 4.6 Governance Database Logic

`tools/governance_db.py` 把治理資料拆成數個表：

- `skills`
- `security_scans`
- `equivalence_tests`
- `audit_log`

這種設計對應的是典型的 workflow/event 資料模型：

- `skills` 是目前狀態
- `security_scans` 與 `equivalence_tests` 是驗證歷史
- `audit_log` 是操作歷史

因此 dashboard 並不是只讀單一當前表，而是從狀態與歷史的組合中重建治理視圖。

## 4.7 Dashboard Service Logic

`GovernanceService` 是 dashboard API 的邏輯中樞。

它的角色包括：

- 把 DB record 轉為前端需要的 summary / detail shape
- 聚合 stats
- 執行 scan / test readiness 檢查
- 驗證 path 是否落在 allowed roots
- 提供 review queue、risk distribution、audit log

這層 service 很重要，因為它讓 router 層保持單薄，同時把資料組裝與防護集中在一處。

## 4.8 Frontend Auth and Session Logic

前端的 auth flow 現在是完整的：

1. 使用者在 login page 輸入帳密
2. 前端呼叫 core API `/api/auth/token`
3. 拿到 access token 後寫入 local storage
4. `api` client 對 dashboard API 請求自動附帶 Bearer token
5. `AuthProvider` 用 `/api/auth/me` 初始化目前登入者
6. 若 dashboard API 回 `401`，前端清除 token 並切回未登入狀態

這個設計讓責任分工清楚：

- core API：簽發 token、回答身份
- dashboard API：驗證 token 並保護治理端點
- web：管理 session state 與 route access

## 4.9 Why the Dashboard Matters

dashboard 不是裝飾層，而是把治理層真正變成可操作系統的關鍵。

沒有 dashboard 的話：

- scan / test / review 流程只能走 CLI
- audit trail 難以被一般 reviewer 使用
- governance 雖存在，但可用性不足

現在 dashboard 提供的主要管理視圖包括：

- 總覽
- skills list
- skill detail
- review queue
- security
- audit log

這讓 Skill-0 的治理能力不再只是 developer-only 工具。

## 4.10 Current Logical Maturity

從邏輯完整度來看，目前最成熟的是：

- decomposition vocabulary
- search API
- governance data model
- auth-protected dashboard API

仍有進一步演進空間的則是：

- scan / test 的大批量異步化
- 搜尋端點的更細緻錯誤處理
- 雙資料庫間的一致性治理
- 更完整的營運級 backup / restore flow
