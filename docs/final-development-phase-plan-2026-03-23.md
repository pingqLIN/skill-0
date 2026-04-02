# Skill-0 Final Development Phase Plan

Updated: `2026-03-23`

## 1. Document Purpose

本文件作為 `skill-0` 與 `skill-0-GUI` 的最後開發階段計畫書，供外部技術審查、內部執行協調與交付前收尾使用。

本文件的定位不是重新描述專案願景，而是明確回答以下問題：

1. 目前已經完成到哪裡
2. 進入最後開發階段後，還有哪些工作流必須完成
3. 哪些事項屬於交付前必要條件，哪些屬於後續優化
4. 外部審查方應如何理解本階段的交付基準

## 2. Plan Scope

本計畫涵蓋三個互相關聯的範圍：

1. `skill-0`
   Canonical parser、schema、search、governance、dashboard 與 deployment baseline。

2. `skill-0-GUI`
   Parser bridge、standalone fallback、review workbench runtime、complex-skill analysis surface。

3. Shared contracts
   `skill-0/docs/shared/` 所維護的 parser contract、mode/equivalence contract、shared terminology，以及 GUI 的 mirrored shared docs。

## 3. Current Baseline

截至 `2026-03-23`，本計畫以以下可確認事實為基線：

### 3.1 `skill-0`

- core API、dashboard API、dashboard web 已成形
- frontend JWT/session 已補齊
- production-style Docker 驗證已跑通
- `docker compose -f docker-compose.prod.yml up -d --build`、health check、JWT login、protected stats access、restart persistence 已驗證
- dossier、external review、review opinion、diagram assets 已建立
- complex-skill strategy 已形成明確方法論，但尚未正式落入 canonical parser 實作

相關文件：

- [project-review-2026-03-23.md](project-review-2026-03-23.md)
- [external-review-report-2026-03-23.md](external-review-report-2026-03-23.md)
- [project-dossier-2026-03-23.md](project-dossier-2026-03-23.md)
- [07-complex-skills-analysis-strategy.md](dossier/07-complex-skills-analysis-strategy.md)

### 3.2 `skill-0-GUI`

- canonical bridge to `skill-0` works
- standalone fallback mode works
- deployable Node/Express runtime exists
- chaptered external-review-ready docs package exists
- complex-skill analysis spec / risk schema / warning template docs exist
- shared-doc mirroring mechanism exists and has been verified

相關文件：

- [GUI docs index](../../skill-0-GUI/docs/README.md)
- [08-development-status-risks-and-roadmap.md](../../skill-0-GUI/docs/08-development-status-risks-and-roadmap.md)
- [09-complex-skill-analysis-spec.md](../../skill-0-GUI/docs/09-complex-skill-analysis-spec.md)
- [10-complex-skill-risk-schema.md](../../skill-0-GUI/docs/10-complex-skill-risk-schema.md)
- [11-evidence-based-warning-template.md](../../skill-0-GUI/docs/11-evidence-based-warning-template.md)

### 3.3 Shared-doc model

- `skill-0` is the source of truth
- `skill-0-GUI` mirrors selected files into `docs/shared/`
- `npm run docs:sync` and `npm run docs:check` are working on the current machine baseline

相關文件：

- [shared-documentation-model.md](shared-documentation-model.md)
- [docs/shared/README.md](shared/README.md)

### 3.4 Baseline authority note

本計畫的 authoritative baseline 來自 `2026-03-23` 的 review、dossier 與 runtime 驗證文件。

應視為目前送審與排程基線的文件包括：

- [external-review-report-2026-03-23.md](external-review-report-2026-03-23.md)
- [project-review-2026-03-23.md](project-review-2026-03-23.md)
- [project-dossier-2026-03-23.md](project-dossier-2026-03-23.md)

較早期的開發計畫，例如 `FINAL_PHASE_PLAN.md` 與部分 `docs/planning/*` 文件，在本階段應視為歷史背景，而不是主要排程依據。

## 4. Final-Phase Objective

最後開發階段的總目標是：

> 把目前已可運行、可審核、可部署的基線，推進到「可穩定交付、可持續評估、可對複雜 skills 提供高價值分析」的狀態。

這個階段不再以「新增大量功能」為主，而是聚焦在四個結果：

1. `skill-0` 的營運級與解析級基線可被信任
2. `skill-0-GUI` 能把 complex-skill analysis 轉成 reviewer 真正可用的表面
3. 兩個 repo 之間的 contract wording 不漂移
4. 外部審查方可清楚判斷目前能力、限制與剩餘風險

## 5. Non-Goals

本階段不以以下事項作為 blocking deliverables：

- 完整重寫所有 parser heuristics
- 一次性實作完整 multi-skill graph IDE
- 把 `skill-0` 與 `skill-0-GUI` 合併為 mono-repo
- 做到正式 production operations 結案等級的容量與 HA 驗證
- 把所有 roadmap 願景全部提前交付

## 6. Workstreams

最後開發階段建議拆成六個可排程單元，其中兩個是前置 foundations，四個是主要工作流。

## 6A. Pre-Workstream Foundations

### Foundation F1: Schema extension design

目的：

- 在 parser、GUI、shared contracts 之前，先定義 complex-skill P0 的共同資料形狀

原因：

- 現行 schema 雖有 provenance 與 parser meta，但缺少 first-class `manifest`、`supporting_files`、`command_references`、`delegation_nodes`
- 若沒有先做 schema extension design，B 與 C 很容易各自假設不同 output shape

最低交付：

1. schema additions proposal
2. versioning rule
3. parser output example
4. GUI consumption example
5. shared-contract wording impact note

### Foundation F2: Test infrastructure baseline

目的：

- 讓 parser P0 與 GUI integration 有最基本的機器驗證能力

最低交付：

1. Python fixture-based tests for complex-skill parser scenarios
2. 至少 3 個手工建立的 complex-skill fixtures
3. GUI test baseline，至少可驗證 bridge/runtime-facing 行為
4. canonical / standalone mode 的 bridge contract tests

說明：

- `converted-skills/` 目前沒有可直接重用的多檔 complex-skill 樣本，fixtures 必須手工建立
- GUI 雖已有測試相關檔案與 smoke-test 跡象，但正式 test baseline、依賴與 CI 還需收斂成穩定入口
- parser P0 若沒有 fixtures，也無法穩定驗證 manifest、references、warnings 這類新輸出

## 6B. Main Workstreams

依賴順序：

- F1 與 A 可並行
- F2 可與 A 並行，但必須在 B 驗收前完成
- B 依賴 F1、F2
- C 依賴 B 的 output shape 與 GUI 測試基線
- D 依賴 B 與 C 穩定後再收斂

關鍵路徑：

> F1 → F2 → B → C → D

其中 A 應獨立並行，不應被 B 阻塞。

### Workstream A: Runtime hardening and release baseline

目的：

- 鞏固目前 `skill-0` 已達成的部署與驗證成果
- 補齊交付前仍需落地的營運級基線

主要工作：

1. 量測 API 容器記憶體峰值與冷啟動/熱啟動差異
2. 補 backup / restore 可執行 SOP
3. 在完整 dev 環境重跑 Python 全迴歸
4. 收斂 README / onboarding / version wording
5. 明確決策 public search endpoints 的安全邊界
6. 補強 rate limiter 在反向代理情境下的 client IP 判定策略
7. 為搜尋端點補更明確的 graceful error handling / try-catch 邊界

主要產出：

- runtime measurement note
- backup/restore SOP
- refreshed verification record
- updated deployment/readme wording

### Workstream B: Canonical complex-skill analysis P0

目的：

- 從幾乎沒有現成支援的起點，為 `skill-0` 新增第一版 complex-skill analysis layer

現況說明：

- 現行 `auto_parse.py` 主要支援單檔 `SKILL.md` 啟發式拆解
- frontmatter 僅做簡單 key/value 解析
- relative-link extraction、supporting-files summary、structured command references、delegation nodes、mode-aware warning basis 目前都不存在

因此本工作流應視為：

> 新分析層的首版實作，而不是既有 parser 的小幅延伸。

P0 實作範圍：

1. manifest extraction
2. frontmatter structured field extraction
3. markdown relative-link extraction
4. supporting files summary
5. command-reference risk grading
6. mode-aware confidence / warning basis
7. parser API migration strategy
8. minimal schema additions needed by the above outputs

Parser API strategy：

- 保留 `parse_skill_md(name, text)` 作為向後相容入口
- 新增 manifest-oriented complex-skill entrypoint，例如 `parse_skill_manifest(...)`
- bridge 不應在同一輪被迫切換到不相容介面

本工作流的關鍵原則：

- 先做 discovery pass，不先追求完整 graph 推理
- 先做高訊號提醒，不先追求完整 narrative generation
- 先讓 output 可追溯，再擴大深度

主要產出：

- parser-facing manifest layer
- parser output additions for supporting refs / command summaries
- first usable evidence-backed warning basis

### Workstream C: GUI reviewer surface integration

目的：

- 讓 `skill-0-GUI` 不只是 bridge shell，而是 complex-skill review 的可操作介面

前置條件：

- Workstream B 的 output shape 已穩定到足以消費
- GUI source-driven baseline 已確認存在，需在開始前決定本階段以哪一層作為主要交付面：既有 `src/` workbench、bridge/runtime surface，或兩者並行收斂

現況風險：

- `skill-0-GUI` 同時存在 `src/` workbench 與 bridge/runtime surface
- 若本階段交付面未先明確，C 的開發與驗收仍可能在兩條實作路線間反覆切換

本階段優先事項：

1. 把 manifest summary 納入 GUI response/display
2. 顯示 canonical / standalone mode 與 equivalence caveat
3. 把 high-value warnings 轉成 reviewer-facing cards or summaries
4. 讓 unresolved references / authority class / fallback caveats 可見

若資源足夠，可再延伸：

- lightweight dependency graph
- operator reminder panel

但不以 full graph IDE 為本階段 blocking item。

主要產出：

- manifest-aware GUI review surface
- mode-aware warning presentation
- reviewer-readable result shape

### Workstream D: Cross-repo contract and documentation closure

目的：

- 確保 `skill-0`、`skill-0-GUI`、external review package 三者的說法一致

主要工作：

1. 維持 `docs/shared/` 為唯一 shared source-of-truth
2. 每次 contract wording 變更後，同步 GUI mirrored docs
3. 把 final-phase 計畫與 external-review package 對齊
4. 確保 dossier、review report、GUI docs index 互相可索引
5. 在 `skill-0-GUI` CI 中整合 `npm run docs:check`
6. 為關鍵設計 / 規格文件加入 `implemented / designed / planned` 狀態標記

主要產出：

- synchronized shared docs
- stable external-review document set
- no known contract drift across repos

## 7. Milestones

### Milestone 1: Verified release baseline freeze

目的：

- 把目前可運行但仍有口語判斷的狀態，收斂成可審核的固定基線

Exit criteria：

1. Python regression 在完整 dev 環境重跑完成
2. runtime measurement note completed
3. backup/restore SOP completed
4. README / deployment wording updated where necessary

### Milestone 2: Schema and test foundations complete

目的：

- 為 parser P0、GUI integration、shared contracts 建立共同基礎

Exit criteria：

1. schema extension design completed
2. versioning approach documented
3. at least 3 complex-skill fixtures exist
4. Python fixture tests can run
5. GUI test baseline exists for bridge/runtime-facing verification

### Milestone 3: Complex-skill parser P0 complete

目的：

- 讓 `skill-0` 真正有能力對複雜型 skills 輸出高價值 discovery-level analysis

Exit criteria：

1. parser can emit manifest-oriented structure for fixtures
2. frontmatter control fields are extracted
3. supporting file references are summarized
4. command references receive basic authority/risk grading
5. old parser entrypoint remains backward-compatible
6. output can support evidence-based reminders

### Milestone 4: GUI review integration complete

目的：

- 把 parser 的 complex-skill analysis 能力，轉成 reviewer usable surface

Exit criteria：

1. GUI visibly distinguishes canonical vs standalone mode
2. GUI can show manifest summary and major unresolved references
3. GUI can render prioritized warning/reminder set
4. fallback degradation is made explicit in the UI/result layer
5. GUI verification scenarios can be executed with the adopted test baseline

### Milestone 5: External review package closure

目的：

- 讓外部審查方收到的是一組穩定、一致、可追溯的審查資料

Exit criteria：

1. final-phase plan completed
2. dossier and review package references are up to date
3. shared docs mirrored and checked
4. external reviewers can trace current capability, remaining risk, and next-stage direction from the document set alone

## 8. Deliverables

本階段的主要交付物如下：

| Deliverable | Repo | Type | Review Value |
|-------------|------|------|--------------|
| Runtime hardening records | `skill-0` | verification docs / ops docs | 證明可部署基線不是口頭聲稱 |
| Complex-skill parser P0 | `skill-0` | parser / schema-facing implementation | 讓複雜 skills 分析從方法論走向實作 |
| Complex-skill reviewer surface | `skill-0-GUI` | bridge / UI integration | 讓外部 reviewer 能真正使用分析結果 |
| Shared contract sync | both | docs / process | 降低 cross-repo 語義漂移 |
| Final external review package | `skill-0` + `skill-0-GUI` | dossier / reports / indices | 提供正式送審材料 |

補充基礎交付：

| Schema extension design | `skill-0` | design / contract | 避免 parser 與 GUI 各自假設不同資料形狀 |
| Complex-skill fixtures and tests | both | test infrastructure | 讓 B / C 的驗收可機器驗證 |

## 9. Acceptance Criteria

若要判定本階段「完成到可交外審版本」，最低應滿足：

1. `skill-0` runtime baseline remains reproducibly verifiable
2. complex-skill analysis is no longer document-only; at least P0 analysis exists in code
3. `skill-0-GUI` can present mode-aware, evidence-backed, reviewer-meaningful output
4. shared-doc mirroring is operational and current
5. document package clearly separates:
   - verified facts
   - remaining risks
   - unimplemented roadmap

為避免主觀判斷過重，應補充以下具體檢查方式：

1. 至少 3 個 complex-skill fixtures 通過 parser P0 驗證
2. 至少 3 個 GUI review scenarios 可重現：
   - canonical mode summary
   - standalone mode degradation notice
   - unresolved reference / command-risk warning rendering
3. `npm run docs:check` exits `0`

## 10. Dependencies and Assumptions

本計畫依賴以下前提成立：

1. `skill-0` remains the canonical parser and contract owner
2. `skill-0-GUI` remains an independent repo and runtime
3. shared docs continue to be mirrored rather than symlinked or submoduled
4. complex-skill analysis should optimize for review value, not full semantic completeness
5. current deployment baseline remains single-node / small-scale unless explicitly expanded

## 10.1 Dependency register

本階段真正會阻塞里程碑完成的依賴如下：

1. full Python regression rerun in a complete dev environment
2. API memory/load measurement and backup strategy completion
3. schema extension design approval before parser P0 implementation
4. GUI source-baseline decision before deeper review-surface work
5. GUI test-baseline adoption before C milestone sign-off
6. shared-doc ownership remains anchored in `skill-0/docs/shared/`

## 11. Main Risks in This Final Phase

### Risk 1: Scope inflation

最容易失控的風險是把 complex-skill analysis 直接做成 full graph platform，導致 parser、GUI、docs 三邊同時膨脹。

Mitigation：

- P0 只做 manifest + references + command risk + warnings basis
- full graph reasoning stays explicitly out of scope for this phase

### Risk 2: Document/implementation drift

目前文件系統已很完整，反而更需要防止「文件先走太遠、實作沒跟上」。

Mitigation：

- every milestone must produce both code truth and document truth
- shared-doc changes must be mirrored and checked

### Risk 3: GUI/source mismatch

`skill-0-GUI` 目前 runtime 可用，但 source-driven UI baseline 仍不穩。

Mitigation：

- prioritize review-surface integration before product polish
- do not treat design-model backlog as if already implemented

### Risk 4: External reviewers over-assume production readiness

若文件沒有清楚區分「可審核」與「正式營運 ready」，外部很容易高估目前成熟度。

Mitigation：

- keep runtime verification, remaining risks, and non-goals explicit
- preserve mode/equivalence caveats in both repos

### Risk 5: Parser API signature breakage

若 B 直接改寫現有 parser 入口，GUI bridge 與現有 consumer 可能立即斷裂。

Mitigation：

- dual-entry strategy
- explicit parser contract update
- fixture-based compatibility verification

### Risk 6: Test infrastructure gap

若 F2 沒先完成，B/C 的 exit criteria 會退化成只能靠人眼判斷。

Mitigation：

- establish Python fixtures first
- add GUI test baseline before C sign-off

### Risk 7: Schema version drift

目前 repo 內仍存在較舊的 schema version wording；若 B 再擴欄位但不收斂版本管理，漂移會加劇。

Mitigation：

- schema extension design must include versioning rule
- contract docs and schema references should be updated in the same phase

### Risk 8: Hidden critical path delay

若 B 延遲，C 和 D 會連鎖延遲。

Mitigation：

- explicitly manage F1 → F2 → B → C → D as the critical path
- let A run independently and early

## 12. Recommended External Review Focus

外部審查方在本階段最值得聚焦的是：

1. `skill-0` 是否已具備可信的 canonical analysis baseline
2. complex-skill P0 設計是否合理，是否符合有限資源下的高 ROI 原則
3. `skill-0-GUI` 是否有效承接 review surface，而不是複製 parser 責任
4. cross-repo contract management 是否足夠清楚
5. remaining risks 是否被正確揭露，而不是被隱藏在願景敘事之下

## 13. Final Statement

本計畫所定義的「最後開發階段」不是專案結案階段，而是：

> 從已可運作、已可驗證、已可送審的成熟基線，推進到可穩定交付、可分析複雜 skills、且 cross-repo contract 清晰收斂的最後一段開發週期。

若本計畫完成，則外部審查方將能以更高信心判斷：

- 專案的 canonical 能力是否可信
- GUI 的 reviewer value 是否成立
- 複雜 skills 分析是否已從概念走向實作
- 剩餘風險是否已收斂到可治理範圍
