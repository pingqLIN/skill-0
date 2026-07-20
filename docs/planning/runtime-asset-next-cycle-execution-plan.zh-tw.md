# Runtime Asset 下一輪執行計畫

**狀態：** 已核准的執行範圍；operator 決策仍是明確關卡

**日期：** 2026-07-18

**權威版本：** 英文版；本文件為繁體中文閱讀參考

## 目標

在不削弱 P0 相容性邊界下，依序完成四個階段：

1. 為目前 196 個 Asset 建立真實、可稽核的 Governance authority；
2. 證明 strict drift doctor 健康狀態與可回復性；
3. 以可重現證據審查依賴與供應鏈安全；
4. 將 P1 Search 實驗擴充為凍結且經獨立審核的證據集。

Production FTS5、第二種 Asset Type、實體資料庫整併與 Dashboard 改名均不在
本輪範圍；除非後續 P1 決策另行明確授權。

## 執行模式與關卡

- 規模為 **Large**；本機、可逆且已在授權範圍內的工作採分階段快速執行。
- 每階段在 commit 前都要完成實作審核與聚焦測試。
- 產生的 review packet、decision manifest、資料庫、備份與 benchmark 證據只放在
  ignored 本機路徑。
- AI 可以準備與驗證 operator decision packet，但不得捏造人類 reviewer、核准理由
  或核准決策。
- 資料庫發布、依賴異動及任何 public push 仍是明確關卡；關卡失敗時只停止受影響
  階段，並如實回報。

## 前置階段 — production security hardening closure

**狀態：** `2026-07-20` 已完成本機 source/contract hardening 與 isolated Compose technical rehearsal；production clearance 仍受獨立的 security 與 external-control gates 阻擋。

### 已交付的本機控制

- Production startup 與 `runtime_doctor --production` 會拒絕 `SKILL0_RUNTIME_ALLOW_INITIALIZE=true`；production boot 不得初始化空的 Runtime ledger。
- Public `/health` 只回傳 liveness status。Authenticated `/api/health/detail` 不回傳 filesystem、storage、model、version metadata。
- Isolated Compose rehearsal 在 production startup 前，經 entrypoint-overridden helper 初始化 disposable Runtime volume；stack 啟動後全程保持 Runtime initialization disabled。
- [`../production-security-policy.md`](../production-security-policy.md) 已提升至 policy `1.3.0`；已實作的控制不再列為 known unenforced gaps。

### Validation evidence

- Focused production contract regression：`7 passed`。
- Full Python/API regression：`508 passed, 76 warnings`。
- Schema validation：`196 passed, 0 failed`。
- Isolated PowerShell Compose rehearsal 已通過 service health、production doctor、governed dry-run、deterministic Evidence、three-store backup/restore、restart persistence 與 cleanup checks；詳見 [`../reports/runtime-production-compose-rehearsal-2026-07-20.zh-tw.md`](../reports/runtime-production-compose-rehearsal-2026-07-20.zh-tw.md)。
- 此 batch 前 Git worktree 為 clean；未引入 Asset type、FTS5 integration、Dashboard redesign、real adapter、physical database migration。

### Rehearsal evidence 與剩餘 production boundary

請求的 live isolated rehearsal 現為 `TECHNICAL_REHEARSAL_PASS`。演練只使用 synthetic rehearsal values、loopback ports、唯一 Compose project 與 disposable volumes；沒有讀取真實 production configuration，也沒有建立 public route。第一次執行發現 repository-local Governance DB 會經 Dashboard image 被 Docker volume copy-up 匯入；commit `0b3acbb` 已移除該 image input 並加入 build-context guard。clean rerun 已通過，且最後沒有殘留該 project 的 container、volume 或 network。

這不等於 production clearance。Dependency/image review 仍為 `PRODUCTION_NO_GO_PENDING_BASE_CVE_FIX`：offline scans 已驗證 Dashboard 為 1 Critical／2 High、Web 為 1 Critical／9 High。External TLS、network、secret-manager、encrypted-backup 與 monitoring controls 也仍需 operator evidence。

## 階段 1 — P0.2 真實 Governance authority

### 交付物

- 新增 `tools/runtime_asset_governance_bootstrap.py`，分成 `preview`、
  `validate-decision` 與 `apply` 指令。
- `preview` 從 `LegacySkillAssetRepository` 建立不可變的 196-item packet，包含 corpus
  snapshot、canonical Asset ID、revision ID、content digest、source path/digest、identity
  strategy、version 與唯讀 security scan 摘要。
- packet 使用 canonical JSON 計算 deterministic digest；易變的建立時間不納入 digest。
- operator decision manifest 必須綁定 packet digest 與 snapshot；每個 candidate 都要由
  operator 明確 approve 或 reject，且包含 reviewer identity 與非空理由。
- `apply` 在任何寫入前重建並驗證 packet，先建立私有 staging Governance DB，沿用既有
  `GovernanceDB` lifecycle，驗證完整性與 audit provenance，全部通過才以原子方式發布。

### 安全規則

- 絕不沿用 repo 根目錄那個無關的 `governance.db`。
- 絕不把未完成的 authority DB 寫進 `governance/db/governance.db`。
- P0.2 bootstrap 一律拒絕既有 target。backup、restore 與 replacement 是獨立的階段 2
  operator workflow；bootstrap 絕不直接修改 live authority state。
- 被 reject 或遺漏的 Asset 不得產生假的 doctor `healthy`。
- Governance record 的唯一名稱採 canonical Asset ID；人類可讀 display name 只留在證據，
  以避開現存重複的 `pdf` 名稱。

### 驗收

- packet deterministic 與所有 fail-closed decision validation 測試通過。
- 三個由來源名稱衍生的 Java canonical ID 都能無歧義綁定。
- fully-approved 測試 corpus 透過真實 Governance schema 得到 doctor `healthy` / exit `0`；
  存在 rejection 時得到 `authority-missing` / exit `2`。
- live 196-item apply 必須已有真實 operator decision；在此之前階段狀態為
  `AWAITING_OPERATOR_DECISION`，不得宣稱完成。

## 階段 2 — strict doctor 健康與 restore

### 執行

1. 將完全相符且已審核的決策套用到 staging DB。
2. 驗證 `PRAGMA integrity_check`、196 個 current canonical binding、精確 content digest、
   approval provenance 與預期 audit event 數。
3. 以原子方式發布 staging DB。
4. 不使用 `--allow-nonhealthy-evidence` 執行 index maintenance，再執行第二次 no-op。
5. 執行獨立 doctor，並以一個一般 Asset 與一個衍生 Java canonical Asset 做 Runtime admission。
6. 由已驗證備份／副本演練 restore，之後重跑 doctor。

### 驗收

- strict maintenance 不靠例外旗標即 accepted。
- 第二次執行為 no-op。
- restore 演練前後 doctor 都是 `healthy` / exit `0`。
- source Registry snapshot 與 derived Index identity 不變。

## 階段 3 — 安全與依賴審查

### 證據批次

- 以專案 Node 20 目標執行 npm lockfile 的 development 與 production scope audit。
- 在 disposable、ignored 環境解析 Python dependency graph 並 audit，不修改現有 repo 環境。
- 分別審查 container base-image pin、Python lock coverage、GitHub Actions pin 與 CI advisory gate。
- 僅在有 authenticated read-only 權限時讀取 GitHub Dependabot alerts；否則狀態記為
  `UNKNOWN`。

### 修補規則

- Critical/high runtime-direct finding 在修補或具有可稽核且會到期的例外前，阻擋 release/push。
- 每次只做最小 ecosystem-scoped 變更，不做 broad upgrade 或無關 lockfile churn。
- 依賴異動是獨立 mutation batch，必須跑聚焦測試、完整 regression 並單獨 commit。

### 驗收

- 已檢查的 runtime graph 與 image 無未處理 critical/high finding。
- 每個延後項目都有 package/advisory、reachability、owner、expiry 與 revalidation command。
- 若有修補，通過 Node 20 lint/test/build、Python regression、相關 Docker build 與 scoped
  secret/artifact review。

## 階段 4 — 擴充 P1 Search 證據

### 凍結協定

- 新增且不覆寫舊資料的 v2 suite：84 queries（42 lexical、42 semantic）、至少 40 個不同
  direct targets、每題 1–3 個 graded qrels。
- curator 只能讀 corpus metadata/payload；第二位 reviewer 在任何 retrieval measurement 前
  審核 wording、target resolution、subset label 與 taxonomy coverage。
- benchmark 前凍結 suite digest、corpus snapshot、qrel count 與 taxonomy matrix。
- 預先登記三個 FTS5 profile：目前 baseline、`detail=none`、
  `detail=none,columnsize=0`；mapping table bytes 也納入 storage。
- 不得在看到結果後刪減 indexed content、修改 tokenizer/weights 或更動 qrels 來通過 25% gate。

### 驗收

- 每個 profile 都要評估既有 quality、recall、latency、isolation、196 projection、query
  coverage 與 storage gate。
- 只能從其他 gate 全部通過的 profile 中選最小者。
- 產出英文權威決策報告與 `.zh-tw.md` companion，且列出所有 profiles。
- `GO_P1_PROTOTYPE` 只授權後續另一份 reviewed prototype plan；任一 gate 失敗即產生有證據的
  `NO_GO`，production 維持 vector-only。

## 最終整合與回復

- 依變更範圍執行 schema validation、Python regression、frontend checks 與文件／連結檢查。
- 未來若要 push，需先審查 staged diff 與 generated evidence，避免 secrets 或 private planning
  data 被意外發布。
- 每個完成批次獨立 commit。本計畫不授權 push、release、資料庫整併或 production FTS5。
- 原始碼可由各批 commit 回復；本機 authority state 由已驗證 SQLite backup 回復；失敗的 staging
  artifact 直接捨棄，不碰 live target。
