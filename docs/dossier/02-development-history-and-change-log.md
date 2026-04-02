# 02. Development History and Change Log

## 2.1 Evolution Overview

Skill-0 的演進不是直線式的功能堆疊，而是數次概念修正後逐步擴張。

目前可以把它拆成七個階段：

1. 問題發現與定位階段
2. 三元分類模型成形階段
3. Schema 與解析樣本階段
4. 分析工具與 pattern discovery 階段
5. 搜尋 API 與向量索引階段
6. 治理資料庫與 dashboard 階段
7. 穩定化、部署與外部審核準備階段

## 2.2 Phase 1: Problem Discovery

專案早期重點在於理解市場與工具生態，並不是立刻寫後端服務。

從 [PROJECT-HISTORY.md](../PROJECT-HISTORY.md) 可以看出，早期工作包含：

- 比較不同 AI coding / agent 工具方案
- 觀察既有 skill / MCP 生態
- 分析 skill-0 與競品的關係

這一階段的重要輸出不是程式，而是定位：

- Skill-0 不適合定位成 execution runtime
- 更適合定位成 semantic analysis layer
- 重點應放在 decomposition、search、governance

## 2.3 Phase 2: Ternary Model Formation

第二階段真正定義了專案的理論核心。

最重要的概念變化，是把原本較含混的 `mission / knowledge / principle` 收斂成：

- Action
- Rule
- Directive

這一步很關鍵，因為它把原本偏直覺式的元素分類，變成較穩定的抽象模型。

這個階段的變化包括：

- `mission` 重新思考為更通用的描述性陳述
- `Directive` 取代先前較狹義的 naming
- 專案從「資料格式設計」提升成「可擴展的分析 vocabulary」

## 2.4 Phase 3: Schema and Parsed Dataset

接著專案進入 schema 化與範例資料累積階段。

這一階段的重點是：

- 建立 JSON schema
- 定義 ID pattern 與欄位結構
- 累積 parsed skill 範例
- 讓 skill 不再只是 markdown，而是可驗證的資料

這也是專案從概念驗證走向工程化的第一個實質門檻。

如果沒有這一層：

- 後續向量化沒有穩定資料來源
- 治理流程沒有結構化基礎
- dashboard 也無法形成一致欄位

## 2.5 Phase 4: Analysis Tooling

schema 成形後，專案延伸出一批分析工具，例如：

- `tools/analyzer.py`
- `tools/pattern_extractor.py`
- `tools/batch_parse.py`
- `tools/evaluate.py`

這一階段讓 Skill-0 從「可表示」進一步變成「可研究」。

也就是說，Skill-0 不只是把 skill 存成 JSON，而是開始回答這些問題：

- 常見 action 組合是什麼？
- 哪些 directive 最常出現？
- 哪些 skill 類型彼此結構接近？
- framework coverage 是否足夠？

## 2.6 Phase 5: Search Platform Expansion

後續專案明顯從 analysis tooling 擴展到 platform 化。

這一階段增加了：

- `vector_db/` 模組
- embedding 生成
- SQLite-vec 存儲
- semantic search CLI
- FastAPI search endpoints

這代表專案的角色改變了。

它不再只是「離線分析 skill 結構」，而是開始提供線上查詢能力，讓 Skill-0 成為真正可服務化的搜尋層。

## 2.7 Phase 6: Governance and Dashboard

再下一步，專案重心從 search 擴張到 governance。

這一階段新增的核心包括：

- `tools/governance_db.py`
- `tools/skill_governance.py`
- dashboard API
- dashboard web
- skill review / scan / equivalence / audit 流程

這是專案第二次重心轉移。

第一次轉移是：

- from schema → search platform

第二次轉移則是：

- from search platform → governance system

也因此，Skill-0 現在不只是找 skill，而是可以管理 skill 生命週期。

## 2.8 Phase 7: Stabilization and Deployment Hardening

最近一輪變動主要不是新功能，而是把系統拉到可交付基線。

這一輪的核心工作包括：

- 前端 JWT / session flow 補齊
- dashboard Recent Activity 與 Bulk Approve 接線
- CI 對齊 Node 20.19.0
- coverage gate 補齊
- Dockerfile 與 production compose 修正
- docs 開關、JWT secret / CORS fail-fast
- named volume persistence
- production-style compose smoke test

這一輪也修正了幾個重要誤判：

- 一開始以為前端沒有完整 auth flow，後來確認並補齊
- 一開始以為 production compose 已足夠，後來發現它其實混入了 dev bind mounts
- 一開始以為 dashboard unhealthy 是單一 import 問題，後來追到 `os.getenv(default=...)` 的 eager evaluation 語義坑

## 2.9 Important Recent Changes

最近值得被明確記錄的變動如下：

### Architecture / deployment changes

- production compose 改成可獨立使用，而不是依賴 base compose overlay
- web 外部 port 改成可配置，預設 `3080`，避免常見的本機 `3000` 佔用衝突
- `skills.db` seed 路徑修正到 `/app/data/skills.db`
- dashboard `tools` 路徑解析改成容器與本機都穩定

### Security changes

- core API 與 dashboard API 在 production 下加入 docs 開關
- JWT secret、帳密、CORS 在 production 啟動時 fail-fast
- governance service 增加 allowed path roots 防護

### Developer experience changes

- `.nvmrc` 與 frontend `engines` 對齊 Node 20.19.0
- `requirements-dev.txt` 成為 Python dev baseline
- README 對齊實際啟動與 production compose 流程

## 2.10 Current Stage Assessment

如果從整體歷程來看，目前專案已經不是「概念驗證中」，也不是「單點功能開發中」。

更準確的判斷是：

> Skill-0 已完成從概念框架到可部署治理平台的第一個完整閉環，目前進入以營運級穩定性與容量驗證為主的階段。

也就是說，主體能力已完成，剩餘問題主要集中在：

- 記憶體壓力
- 備份與恢復
- 長時間運行行為
- 維運與觀測成熟度
