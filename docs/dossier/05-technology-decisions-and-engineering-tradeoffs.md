# 05. Technology Decisions and Engineering Tradeoffs

## 5.1 Decision Style

Skill-0 的技術選擇整體呈現一個明顯風格：

> 優先用 local-first、低外部依賴、易理解的組件，把系統先做成，再逐步補齊穩定性與規模化能力。

這意味著它不是為了追求最前沿架構，而是以「小而完整、能快速驗證價值」為導向。

## 5.2 Why FastAPI

core API 與 dashboard API 都選擇 FastAPI，理由很直接：

- Pydantic model 與型別定義清楚
- 自動文件生成對早期平台很有利
- async request handling 足夠應對目前規模
- Python 生態可直接銜接 embedder、SQLite、治理工具

取捨：

- 優點是開發快、結構清楚
- 代價是如果未來需要更高併發或更細緻的 service decomposition，仍可能要重新規劃

## 5.3 Why SQLite + SQLite-vec

這是專案最有代表性的工程選擇之一。

### 原因

- skill 資料量在目前階段可控
- local-first 部署成本低
- 不需要引入外部向量 DB
- 對個人或小團隊治理平台非常務實

### 好處

- 啟動簡單
- 備份方式直接
- 開發環境一致
- 不依賴外部 SaaS

### 代價

- 高併發與多寫入者場景受限
- 搜尋與治理分成兩個 SQLite DB，增加一致性治理成本
- 長期若資料量或 traffic 上升，需要重新評估

## 5.4 Why a Separate Governance DB

沒有把治理資料硬塞進向量資料庫，而是獨立成 `governance.db`，是合理決策。

理由是：

- 搜尋資料與治理資料性質不同
- dashboard 不應直接與向量索引耦合
- audit / approvals / scans / tests 比較適合 event-and-state 的 relational model

代價也很清楚：

- skill identity 需自行維護
- backup / restore 不能只考慮單一 DB

## 5.5 Why React + Vite

dashboard web 採 React 19 + Vite 7，是現代且務實的選擇。

主要優勢：

- 開發速度快
- bundle build 與 dev experience 直接
- React Query 能較自然處理 dashboard data fetching
- 路由 lazy loading 與 bundle guardrail 容易落地

近期實際也證明這個選擇可行：

- 已完成 lint、build、build:ci、Vitest smoke tests
- 已補齊 session flow 與 protected routes

## 5.6 Why JWT Shared Across Services

core API 與 dashboard API 共用 JWT secret，是一個實用但帶邊界的選擇。

好處：

- 不必額外建 auth service
- web login flow 簡單
- dashboard API 可直接信任 core API 發出的 token

限制：

- secret rotation 需要同時考慮兩邊
- 更細緻的 auth / scopes 目前還未展開

## 5.7 Why Docker Compose

Skill-0 現在的 deployment 選擇不是 Kubernetes，而是三容器 compose。

這和專案階段完全一致：

- 服務數量不多
- 部署邏輯明確
- 適合先證明整套鏈條可運作

近期也已把 production compose 修成較可靠的型態：

- 可獨立啟動
- health-gated startup
- named volume persistence
- API 與 web 對外 port 可配置

## 5.8 Why structlog and Health/Metrics

專案不只寫了 API，也把基本 observability 接上了：

- request ID
- structured logging
- `/health`
- `/metrics`

這表示系統從設計上就不是純本機實驗，而是有意識往可部署服務靠近。

## 5.9 Important Tradeoffs Accepted by the Project

目前專案明確接受了以下 tradeoffs：

1. 接受 SQLite 的規模限制，以換取部署簡單。
2. 接受模型冷啟動與快取成本，以換取不依賴外部 embedding SaaS。
3. 接受 shared-secret JWT 的簡化設計，以換取 auth integration 速度。
4. 接受 dashboard 偏 admin-console 風格，以換取治理流程先可用。
5. 接受 early-stage 文檔與實作會多次同步調整，以換取快速迭代。

## 5.10 Decisions That Should Be Revisited Later

以下不是錯誤決策，但到了下一階段應重評估：

- 是否繼續維持雙 SQLite
- 是否需要 Redis / external rate limiting
- 是否把 embedding / search 從 core API 拆出
- 是否把大批量 scan / test 改成 background job
- 是否建立更正式的 backup / restore / migration discipline

## 5.11 Engineering Character of the Repo

整體來說，這個 repo 的工程風格是：

- 重視可部署性
- 重視本地可重現
- 重視結構化與治理
- 不追求華麗抽象，偏向直接而可驗證的實作

這個風格對目前的專案階段是合適的，也解釋了為什麼它能在有限複雜度下，同時涵蓋 schema、search、governance、dashboard 與 deployment。
