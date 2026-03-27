# Skill-0 Project Dossier

Updated: `2026-03-23`

## Purpose

本 dossier 用來提供一套可對外、可交接、可追蹤的專案說明文件組。它不是單純的進度摘要，而是把 Skill-0 的：

- 專案構想
- 發展脈絡
- 架構設計
- 核心邏輯
- 技術取捨
- 驗證結果與風險

整合成一組可索引、可交叉閱讀的主從文件。

## Recommended Reading Order

### For external reviewers

1. `docs/dossier/01-project-concept-and-positioning.md`
2. `docs/dossier/03-system-architecture-and-runtime.md`
3. `docs/dossier/06-verification-risks-and-next-steps.md`

### For engineering handover

1. `docs/dossier/02-development-history-and-change-log.md`
2. `docs/dossier/03-system-architecture-and-runtime.md`
3. `docs/dossier/04-core-logic-and-governance.md`
4. `docs/dossier/05-technology-decisions-and-engineering-tradeoffs.md`

### For operators / deployment owners

1. `docs/dossier/03-system-architecture-and-runtime.md`
2. `docs/dossier/06-verification-risks-and-next-steps.md`
3. `docs/deployment-guide.md`
4. `docs/operations-runbook.md`

## Dossier Index

| File | Purpose | Main Questions Answered |
|------|---------|--------------------------|
| `docs/dossier/01-project-concept-and-positioning.md` | 說明專案為何存在、要解什麼問題、如何定位 | Skill-0 是什麼？為何不是單純 parser？ |
| `docs/dossier/02-development-history-and-change-log.md` | 梳理從概念演進到目前產品形態的變化 | 專案怎麼一路變成現在這樣？ |
| `docs/dossier/03-system-architecture-and-runtime.md` | 描述系統拓樸、資料流、啟動方式與部署型態 | 整套系統怎麼跑？ |
| `docs/dossier/04-core-logic-and-governance.md` | 拆解核心業務邏輯、治理流程與前後端協作 | 搜尋、治理、審核、auth 如何串起來？ |
| `docs/dossier/05-technology-decisions-and-engineering-tradeoffs.md` | 說明技術棧與取捨 | 為什麼選 FastAPI、SQLite-vec、React、Docker？ |
| `docs/dossier/06-verification-risks-and-next-steps.md` | 收斂目前驗證結果、風險與下一步 | 現在能做什麼？還差什麼？ |
| `docs/dossier/07-complex-skills-analysis-strategy.md` | 納入 `skill-0-GUI` 與官方 Claude Skills 文件，說明複雜型 skills 的最佳分析策略 | 面對主副 skills、references、commands、subagents，如何用有限資源產生高價值分析與提醒？ |

## Relationship to Existing Docs

本 dossier 不取代既有文件，而是把既有文件重新組織成可閱讀的敘事主線。

| Existing doc | Role in dossier |
|--------------|-----------------|
| `docs/PROJECT-HISTORY.md` | 提供早期概念形成與版本演化脈絡 |
| `docs/implementation-summary.md` | 提供曾完成的實作範圍與工具背景 |
| `docs/project-progress-report-2026-03-23.md` | 提供功能區塊盤點與階段判讀 |
| `docs/project-review-2026-03-23.md` | 提供內部審查觀點與近期修正記錄 |
| `docs/external-review-report-2026-03-23.md` | 提供外部審核定位與摘要版本 |
| `docs/review-opinion-2026-03-23.md` | 提供正式審查意見附件 |
| `docs/final-development-phase-plan-2026-03-23.md` | 提供最後開發階段的 cross-repo 執行計畫、里程碑、驗收標準與送審定位 |
| `docs/final-phase-plan-review-2026-03-23.md` | 提供對最後開發階段計畫書的策略審查意見，補強工程規模、關鍵路徑、schema 與測試前置要求 |
| `docs/final-phase-plan-review-round2-2026-03-23.md` | 提供第二輪策略審查意見，確認計畫已可進入執行階段，並記錄執行期的小修項目 |
| `docs/schema-extension-design-complex-skills-2026-03-24.md` | 提供 complex-skill P0 的 schema extension design、parser API 相容策略、fixture 規格與 GUI consumption shape |
| `docs/shared-documentation-model.md` | 定義 `skill-0` 與 `skill-0-GUI` 的共享文件來源、鏡像同步模式與維護邊界 |
| `docs/shared/README.md` | 作為共享 contract 文件的 source-of-truth 入口 |
| `docs/shared/01-parser-contract.md` | 定義 canonical parser 與下游 consumer 的穩定契約 |
| `docs/shared/02-mode-and-equivalence-contract.md` | 定義 canonical mode / standalone mode 的語義邊界與等價性說法 |
| `docs/shared/03-shared-terminology.md` | 統一 `skill-0` 與 `skill-0-GUI` 的共用術語 |
| `docs/deployment-guide.md` | 提供部署與環境變數操作細節 |
| `docs/operations-runbook.md` | 提供營運與日常維護視角 |

## Cross-Repo Contract Notes

`skill-0` 與 `skill-0-GUI` 目前採用「`skill-0` 持有共享文件原始來源，`skill-0-GUI` 鏡像同步」模型。

這代表：

- parser contract、mode semantics、shared terminology 應優先查看 `docs/shared/`
- GUI 端的 `docs/shared/` 視為 mirrored copies，不是獨立來源
- 若 cross-repo wording 有變更，應先更新 `skill-0/docs/shared/`，再於 `skill-0-GUI` 執行 `npm run docs:sync`

## Current Baseline Summary

截至 `2026-03-23`，Skill-0 的最新可確認基線如下：

- 核心 API、dashboard API、dashboard web 均已成形
- 前端 JWT / session 流程已補齊
- 前端 `lint`、`build`、`build:ci`、`npm test` 均已通過
- Docker `api` / `dashboard` / `web` image build 均已通過
- `docker compose -f docker-compose.prod.yml up -d --build` 已通過
- API / dashboard health、JWT login、受保護 dashboard endpoint、restart persistence 均已通過 smoke test
- 專案已達可送交外部技術審核的階段，但仍不等同正式營運驗收完成

## Source-of-Truth Notes

以下幾個事實應視為本 dossier 的最新事實基線：

- production compose 入口使用 `WEB_PORT`，預設對外為 `3080`
- core API 預設對外 port 為 `8080`
- production 模式下 Swagger docs 預設關閉，受 `SKILL0_ENABLE_DOCS` 控制
- production 啟動對 JWT secret、CORS、帳密採 fail-fast
- `skills.db` 與 `governance.db` 已透過 named volumes 做持久化

## Suggested Use

- 對外送審時，主文件應搭配 `docs/external-review-report-2026-03-23.md`
- 對內交接時，主文件應搭配 `docs/project-review-2026-03-23.md`
- 若需要精簡版對外摘要，建議從主文件讀到結論後，再擷取外部報告中的摘要文字
