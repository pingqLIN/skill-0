# Skill-0 外部代理獨立審計統整報告

日期：`2026-04-27`
Repo：`<repo-root>`
審計方式：`4 名外部代理獨立只讀審計 + 主代理統整`
結論等級：`mixed-positive / 偏正面`

---

## 1. 總結判斷

四名外部代理的獨立結論高度一致：Skill-0 已經不是單純 prototype，核心價值、工程基線、治理模型與文件防漂移機制都已經成立；但下一階段不應直接大規模擴張 skill corpus 或宣稱 strict equivalence，而應先進入 hardening、quality benchmark、operator workflow pilot 與 release rehearsal。

整體評價是「偏正面，但仍需用 benchmark 與營運證據補強」。正面不是來自概念新穎，而是 repo 已經有實際可跑的 schema validation、semantic search、FastAPI runtime、revision-aware governance、dashboard API/web、async governance jobs、CI/doc gates 與近期 full regression 證據。

---

## 2. 四名代理結論對照

| 代理面向 | Verdict | 核心評價 | 主要保留 |
|---|---|---|---|
| 產品發展性 | `mixed / 偏正面` | sidecar skill governance data layer 的定位清楚，具 adoption potential | 缺 parser benchmark、adoption package、明確 ICP、營運證據 |
| 技術架構 | `mixed / 偏正面` | schema/search/runtime/governance/dashboard 架構已超過原型 | HTML export escaping、in-process worker、rate limit 語義、vector indexing、parser quality |
| 治理與評估 | `mixed / 偏正向` | revision-aware DB、audit trail、docs authority、fidelity contract 具可信骨架 | evaluation 仍偏 similarity/coverage，不能宣稱 strict equivalence |
| 路線落地 | `mixed-positive` | 適合進入 hardening -> 小範圍 productization pilot | production compose/env、路徑漂移、舊計畫文件、dashboard E2E 覆蓋不足 |

沒有代理給出負面結論。所有代理都反對立即進入大規模 expansion，並一致要求先補「品質量測、操作可視性、部署演練、文件漂移修正」。

---

## 3. 最強正面證據

### 3.1 產品定位成立

Skill-0 的核心價值不是取代 agent runtime，而是把自然語言 skills / MCP tools 轉成可搜尋、可治理、可審查的 sidecar 資料層。這個定位能降低導入風險，讓既有 skill 保持原狀，再逐步加入 parsing、indexing、governance review 與 dashboard workflow。

最適合的初始使用者不是一般 end user，而是：

1. skill registry maintainer
2. AI ops reviewer
3. agent platform / tool governance team
4. 需要盤點、去重、審查大量 skills/tools 的內部平台團隊

### 3.2 工程基線已存在

近期本地報告與外部代理檢查共同指向同一組基線：

| 項目 | 狀態 |
|---|---|
| parsed corpus | `196` checked-in JSON |
| converted-skills corpus | `164` directories |
| schema validation | `196 passed, 0 failed` |
| Python + dashboard API regression | `219 passed` |
| dashboard web tests | `26 passed` |
| production build | passed |

這代表專案不是只有文檔或 demo，而是有可驗證的 contract、API、dashboard、governance workflow 與 regression suite。

### 3.3 Governance 是產品差異化

外部代理一致認為 revision-aware governance 是 Skill-0 相對於單純 semantic search 的主要差異化。已存在的能力包含：

1. skill revision identity
2. checksum / provenance
3. security scan / test 綁定 revision
4. audit log
5. async scan/test action jobs
6. retry / cancel / lease / heartbeat / recovery
7. dashboard audit surface

這讓 Skill-0 更接近「skill governance console」，而不是只有「skill search database」。

### 3.4 文件權威模型已有效

`docs/document-authority-index-2026-03-27.md`、status marker check、shared docs source-set check、GUI mirror drift check 讓專案具備 agent-friendly 的文件治理基礎。這是 AI-first operation 的重要能力，因為後續代理不需要猜哪份文件是現行計畫。

---

## 4. 主要風險排序

### P0：安全輸出邊界

技術架構審計指出 `skill-0-dashboard/apps/api/routers/scans.py` 的 HTML scan export 可能直接用 f-string 插入 skill/finding/url 欄位。若輸入來自不可信 skill text，這可能形成 stored/reflected HTML injection。

這是最應優先處理的單點風險，因為它不是概念問題，而是明確工程安全邊界。

### P0：Parser quality 尚無 ground truth

所有代理都指出目前 `schema pass` 只代表資料形狀正確，不代表 decomposition 語義正確。`skill_tester` 與 evaluation 目前更接近 fidelity / similarity / coverage，不是 strict equivalence proof。

在建立 benchmark 之前，專案不應宣稱：

1. strict equivalence
2. drop-in replacement
3. identical behavior
4. parser 泛化能力已被證明

### P1：Governance job operator telemetry 不足

Async governance jobs 已有 durable MVP，但 reviewer/operator 仍需要更清楚的：

1. failure reason
2. retry lineage
3. cancel trace
4. lease / heartbeat state
5. target revision
6. elapsed time
7. suggested next action

目前底層資料能力已存在，下一步應把它變成 reviewer 可決策資訊。

### P1：Release / production rehearsal 不足

`docker-compose.prod.yml`、`.env.production.example`、CORS、auth、volume、healthcheck、DB persistence、backup/restore 都需要一次正式 dry-run。外部代理特別指出 production compose 的 `CORS_ORIGINS` 設定可能覆蓋 `.env`，造成 Web/API 分離部署時瀏覽器不可用。

### P1：文件漂移仍影響外部信任

README 仍有舊數字，例如 parsed/test count 與近期報告不一致。部分文件仍寫舊路徑 `<repo-root>`，但目前 repo 在 `<repo-root>`。雖然 authority index 已經降級歷史文件，但入口文件漂移仍會削弱外部 reviewer 信任。

### P2：營運級擴展尚未完成

目前架構適合 local-first / small-team governance MVP，但還不是大型 production queue / multi-worker 系統。風險包括：

1. in-process daemon thread worker
2. vector indexing 逐筆 insert / commit
3. 雙 SQLite 一致性與備份
4. embedding cold start / cache 策略
5. search memory / latency 壓測不足

---

## 5. 統整後下一階段方向

### Stage 1：Immediate Hardening

目標：先消除明確安全與文件信任風險。

1. 修補 scan HTML export escaping / sanitization。
2. 加入含 `<script>`、HTML attribute injection、惡意 URL 的 API regression test。
3. 修正 README 與 current docs 的 dataset/test count。
4. 修正 current docs 中錯誤或過時的絕對路徑。
5. 對 root-level historical plans 加上更醒目的 archival warning，或移入 archive。

### Stage 2：Parser Quality Gate

目標：把「schema valid」推進到「quality measurable」。

1. 建立 10-20 個 representative skill fixtures。
2. 每個 fixture 都包含 source input、expected canonical JSON、comparison rules、known failure mode。
3. 將 fidelity rubric 明文化，避免 reviewer 把 similarity 當 equivalence。
4. 新增 `tools/validate_equivalence_fixtures.py` 或同等 fixture validation command。
5. 將 fixture gate 接入 CI，但先以小 corpus 啟動，不直接做大規模 20-skills expansion。

### Stage 3：Governance Operator UX

目標：讓 reviewer 能用 dashboard 做真實決策。

1. 將 action job telemetry 做成 reviewer-facing report。
2. 顯示 job/item target revision、attempt、worker、lease expiry、started/completed time。
3. 顯示 retry lineage 與 cancel trace。
4. 將 failure code 對應到 operator next step。
5. 補一條端到端 reviewer workflow：login -> review queue -> async scan/test -> retry/cancel -> approve/reject -> audit export。

### Stage 4：Release Rehearsal

目標：把 local-first MVP 推到可示範、可重啟、可恢復。

1. 用 production compose 做 dry-run。
2. 驗證 `.env.production.example`、CORS、auth、healthcheck。
3. 驗證 `skills.db` / `governance.db` volume persistence。
4. 補 backup / restore runbook。
5. 建立 skill identity drift report，比對 `skills.db` 與 `governance.db`。

### Stage 5：Productization Pilot

目標：不要先擴大 corpus，而是先做一條 30 分鐘可完成的導入路徑。

1. 定義 ICP：skill registry maintainer / AI ops reviewer / agent platform team。
2. 提供 sample corpus。
3. 提供 demo script：import existing skills -> validate -> index -> review dashboard。
4. 產出 expected outputs 與 troubleshooting guide。
5. 用 pilot 結果決定是否重啟 20-skills expansion。

---

## 6. 不建議現在做的事

1. 不建議立即大規模匯入更多 skill corpus。
2. 不建議宣稱 strict equivalence 或 drop-in replacement。
3. 不建議先做大型 dashboard 新功能。
4. 不建議在 queue / worker 還是 in-process 模型時宣稱 production multi-worker ready。
5. 不建議讓舊計畫文件繼續停留在入口路徑而沒有醒目 archival warning。

---

## 7. 最終評價

Skill-0 的發展性是正面的，但正面條件不是「概念已經被完全證明」，而是「專案已經具備足夠工程基線，可以進入下一輪可證明化」。接下來 1-2 個開發週期的關鍵，不是新增更多能力，而是把現有能力變成可被外部 reviewer、operator、pilot user 信任的證據鏈。

最合理的方向是：

> hardening first, benchmark second, operator workflow third, productization pilot fourth, expansion last.

只要下一輪能補齊 HTML export 安全邊界、parser fixture benchmark、job telemetry、release rehearsal 與 adoption package，Skill-0 就可以從「可運行且可審查的內部治理工具」推進到「可示範、可導入、可擴張的 skill governance baseline」。
