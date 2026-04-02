# 06. Verification, Risks, and Next Steps

## 6.1 Verification Philosophy

Skill-0 目前的驗證不只停在「程式能 build」，而是刻意往更接近交付的方向推進：

- 單元與整合測試
- 前端 lint / test / build
- Docker image build
- production-style compose 啟動
- health check
- JWT login
- 受保護 dashboard endpoint 驗證
- restart 後 persistence 驗證

這代表專案目前的可信度，不是建立在文件聲稱，而是建立在一條已跑通的驗證鏈上。

## 6.2 Verified Baseline

截至 `2026-03-23`，已確認通過的基線如下：

### Frontend

- `npm run lint`
- `npm run build`
- `npm run build:ci`
- `npm test` on Node `20.19.0`，共 `18 passed`

### Python / API

- dashboard 相關 Python 變更已完成語法檢查
- CI 已配置：
  - lint
  - compile check
  - combined pytest
  - coverage gate `--cov-fail-under=75`

### Docker / Runtime

- `Dockerfile.api` build passed
- `Dockerfile.dashboard` build passed
- `Dockerfile.web` build passed
- `docker compose -f docker-compose.prod.yml config` passed
- `docker compose -f docker-compose.prod.yml up -d --build` passed
- `http://127.0.0.1:8080/health` passed
- `http://127.0.0.1:3080/dashboard-api/health` passed
- `http://127.0.0.1:3080/` passed
- `POST /api/auth/token` passed
- JWT access to `/dashboard-api/api/stats` passed
- compose restart 後 health 與 DB persistence 仍成立

## 6.3 What Was Actually Fixed in the Last Hardening Round

最近一輪驗證不是單純跑命令，而是實際修掉數個 deployment blocker：

1. production compose 改成可獨立使用
2. API image 改為 CPU-only torch 與 runtime-only dependency path
3. `skills.db` seed 路徑修正為 persistent volume 可用路徑
4. dashboard `tools` 路徑解析修正為容器與本機兼容
5. production docs 開關與 JWT/CORS fail-fast 補齊
6. web 外部 port 改為 `3080` 預設，避開常見 `3000` 佔用

這些修正的重要性在於，它們不是 cosmetic，而是直接決定 deployment 是否真的能起來。

## 6.4 Remaining Risks

### High

#### Memory pressure in API

雖然 production compose 的 API 上限已提升到 `1G`，但 embedding model 與 CPU-only torch 在持續查詢下的峰值記憶體仍未量測。

需要補的不是理論討論，而是實測：

- `docker stats`
- 併發搜尋壓測
- 冷啟動與熱啟動差異

#### Dual SQLite governance

雙資料庫設計目前合理，但真正的風險在：

- 備份排程
- 災難恢復
- 資料一致性檢查
- 高寫入場景行為

這些都不是 schema 問題，而是營運問題。

#### Secrets and deployment discipline

雖然 production 已有 fail-fast，但正式部署仍需確保：

- JWT secret 不是範例值
- API 帳密不是範例值
- CORS 實際對應正式網域
- 是否提供 `HF_TOKEN`

### Medium

#### Cold start and external model dependency

即使系統已可啟動，首次冷啟動仍依賴 Hugging Face 模型下載與 cache。

這意味著：

- 沒有快取的環境會較慢
- 無 token 下載速率較差
- 正式環境應建立 model warm-up 策略

#### In-memory rate limiting

目前 rate limit 仍是單機記憶體內實作。

在單容器 / 小規模下可接受，但若未來：

- 經過反向代理
- 多副本
- 需要信任 `X-Forwarded-For`

就需要更成熟的方案。

#### Synchronous governance operations

大批量 scan / test 目前仍偏同步處理。當技能量增加時，會出現：

- event loop 被阻塞
- 使用者等待時間變長
- 操作與 UI 感受變差

## 6.5 What Is No Longer a Primary Risk

以下幾項已不再是主要 blocker：

- 前端沒有 auth/session
- dashboard 首頁僅有 placeholder
- bulk approve 不可用
- production compose 無法實際拉起
- DB persistence 缺失

## 6.6 Suggested Next Actions

### P0

1. 量測 API 容器在搜尋壓力下的記憶體峰值
2. 把 backup / restore 流程寫成可執行 SOP
3. 在完整 dev 環境下重跑本地 Python 全迴歸測試

### P1

4. 為搜尋端點補更清楚的 graceful error handling
5. 對 `HF_TOKEN`、模型預熱與 cache 策略形成部署指引
6. 決定 search endpoints 是否維持公開

### P2

7. 評估 background job / queue 化 scan 與 test
8. 規劃雙 SQLite 的長期演進路徑
9. 持續整理 docs 與版本號一致性

## 6.7 Final Assessment

目前 Skill-0 已達到：

- 可送外部技術審核
- 可做架構與部署風險評估
- 可做內部交接與持續開發

但仍未達到：

- 營運級壓測完成
- 備份與恢復完全制度化
- 容量與長期穩定性完全驗證

換句話說，Skill-0 現在的最佳描述是：

> 功能主體與部署主鏈已完成驗證，進入營運級強化前的成熟基線階段。
