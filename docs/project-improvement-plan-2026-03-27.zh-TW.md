# Skill-0 專案改善計劃書

更新日期：`2026-03-27`  
文件狀態：`Draft`  
適用範圍：`skill-0` 核心 repo

---

## 1. 文件目的

本文件的目的不是再做一次審查，而是把最近幾份審查與反方評論轉成可執行的改善計劃。

本計劃特別回應以下三類輸入：

1. 既有外部技術審查對部署、測試、治理基線的肯定
2. Devil's Advocate 對概念、理論與分類假設的批判
3. 目前 repo 實際狀態暴露出的 contract / schema / parser / governance 斷裂

本計劃希望回答五個問題：

1. 哪些問題是概念性的，哪些是工程性的
2. 哪些應先修，哪些可以延後
3. 改善工作的依賴順序為何
4. 什麼叫做「修好了」
5. 如何避免再次陷入 scope creep

---

## 2. 現況判斷

### 2.1 可保留的基線

目前 `skill-0` 並不是一個失敗專案。以下基線仍然成立：

- core API、dashboard API、dashboard web 已具備可運行形態
- auth、rate limiting、部分 integration tests 已可運作
- Docker / compose / deployment baseline 已成形
- 專案有相對成熟的文件體系與審查文化

換句話說，專案現在缺的不是「從 0 到 1」，而是「把已存在的東西收斂成可信的 1」。

### 2.2 目前最重要的問題

根據近期 review 與本地驗證，目前最重要的問題不是 UI，也不是容器化，而是以下四條主線：

1. **Canonical contract 未收斂**
   live schema、`parsed/*.json`、parser output、embedder 消費欄位彼此不一致。

2. **Governance 綁定的是 mutable record，不是 immutable artifact**
   approval / scan / test 目前缺乏 revision-level traceability。

3. **Equivalence 用語過度承諾**
   現行 tester 更接近 similarity / fidelity，而不是 strict equivalence。

4. **三元模型的可驗證性不足**
   缺少 ground truth、failure corpus、confidence / ambiguity discipline。

### 2.3 改善總原則

本計劃採用以下原則：

- **先收斂，再擴張**：先修 contract，再談 schema extension / GUI surface / 新功能
- **先證據，再論述**：沒有 benchmark 的主張不再升級成對外結論
- **先 revision，再 governance**：沒有 artifact identity 的治理不能算真正治理
- **先減法，再加法**：在 `2.4.x` 沒穩定前，不推進大規模 `2.5` 擴張

### 2.4 P0 執行進度更新（2026-03-27）

截至 `2026-03-27`，P0 已完成以下可驗證進展：

1. **Canonical contract 已落地**
   - 已新增 schema validator、normalizer 與 CI gate
   - `parsed/` 全部 `195` 個 skill JSON 已完成正規化並通過 live schema validation

2. **Governance 已改為 revision-aware**
   - 已引入 `skill_revisions` 與 `current_revision_id`
   - scan / test / approve / reject / audit 已綁定 `revision_id`
   - dashboard API 與 detail surface 已可直接顯示 revision history

3. **Web 測試環境已對齊專案要求**
   - repo 已要求 `.nvmrc = 20.19.0`
   - 本機原先為 `Node v18.19.1`，已透過 `nvm` 安裝並切換到 `Node v20.19.0`
   - `nvm default` 已指向 `20.19.0`
   - 在 `Node v20.19.0` 下，dashboard web 測試與 build 已通過

本次環境與驗證結果如下：

- `node -v`（更新後）=`v20.19.0`
- `npm test`（`skill-0-dashboard/apps/web`）=`18 passed`
- `npm run build`（`skill-0-dashboard/apps/web`）=`passed`
- backend / governance regression 驗證累計=`116 passed`

這代表目前 P0 已不只是設計提案，而是已有實際的 contract、governance、API、frontend、與測試基線收斂成果。

同時，P1 也已啟動第一段語義收斂工作：

- tester 與主要 CLI / API / UI 已開始把主語從 `equivalence` 改為 `fidelity`
- 現有 API 仍保留 `equivalence_*` alias，以避免一次性破壞既有資料與前端相容性
- dashboard web 已改以 `fidelity` 作為主要顯示語言

目前這一段的驗證結果為：

- fidelity wording focused regression=`73 passed`
- dashboard web build（Node `20.19.0`）=`passed`

P1 第二段也已完成外部語義收尾：

- shared terminology 與 mode contract 已明確切分 `fidelity` 與 `strict equivalence`
- governance 規範文件已改為以 `fidelity` 描述當前測試語義，並註明 `equivalence_*` 僅為相容欄位
- dashboard 首頁已加入 `Average Fidelity` 指標卡，讓新語義直接出現在主要 reviewer surface

---

## 3. 改善目標

本改善計劃的最終目標是：

> 把 `skill-0` 從「可運行、可展示、可審查的 prototype」推進到「在 contract、governance、evaluation 上可被信任的基線」。

拆解後有五個明確子目標：

1. 建立單一 authoritative contract
2. 讓治理行為可追溯到具體 artifact revision
3. 讓 equivalence / fidelity 用語與證據強度一致
4. 讓 parser quality 可量測、可比較、可被證偽
5. 在不停止現有 search / deployment 價值的前提下，完成上述收斂

---

## 4. 非目標（Non-Goals）

本計劃**不**以以下事項作為近期 blocking deliverables：

- 一次性重寫整個 parser
- 在 `2.4.x` 尚未收斂前直接推完整 `2.5` manifest-oriented 擴張
- 新增大型 dashboard 功能或更多 reviewer surface
- 引入新的多模型編排或 agent orchestration 層
- 先做完整 production HA / horizontal scaling
- 在尚未建立 benchmark 前宣稱 framework 已可泛化到大多數 Skills

---

## 5. 主要工作流

本計劃建議拆成六條工作流，其中前四條屬於核心矯正，後兩條屬於校準與對外收斂。

### Workstream A：Canonical Contract Recovery

優先級：`P0`

#### 問題陳述

目前 repo 內同時存在多套資料方言：

- live schema 的欄位要求
- `parsed/*.json` 的實際輸出形狀
- parser 的當前輸出
- embedder/search 所讀取的欄位

這不只是文件不一致，而是整個專案理論基底不穩。

#### 目標

建立一個單一 authoritative contract，並讓其他層服從它。

#### 主要工作

1. 產出 schema / parser / parsed / embedder 的 mismatch matrix
2. 決策 authoritative source of truth
3. 修正 parser output 與 parsed dataset 使其符合該 contract
4. 修正 embedder/search 使用同一組欄位
5. 補 CI validation gate，阻止新的 drift 再次出現
6. 清理 README / AGENTS / docs 中的舊數字與舊版本語言

#### 主要交付

- `contract-decision.md` 或 ADR
- schema compatibility note
- parsed dataset validation report
- CI schema validation step

#### 驗收標準

- authoritative dataset 對 authoritative schema 的 validation error = `0`
- embedder/search 不再依賴舊欄位名稱
- README / AGENTS / docs 中的 skill count、schema version、contract wording 一致

---

### Workstream B：Artifact-Centric Governance Redesign

優先級：`P0-P1`

#### 問題陳述

目前 governance 以 skill name 與 mutable row 為中心。這會導致：

- approval 無法精準對應到某一版內容
- scan / test 結果可在同一 skill 名稱下漂移
- audit trail 難以回答「究竟哪一份 artifact 被核准」

#### 目標

把 governance 從 name-centric workflow 改成 revision-centric governance。

#### 主要工作

1. 引入 artifact revision 概念
2. 為 revision 建立 checksum / source_commit / source_path / extracted_at 等欄位
3. 將 `skills` 與 `skill_revisions` 拆分
4. 將 scan / test / approve / reject 綁定到 revision_id
5. 為現有資料設計 backfill / migration
6. 更新 dashboard API 與 UI 的資料語義

#### 主要交付

- governance schema migration design
- revision backfill script
- API contract update note
- audit trail semantics note

#### 驗收標準

- 所有新 approval 都綁定 `revision_id`
- 同一 skill 可對應多個 revisions
- audit log 可回答「哪個 artifact 在何時被誰核准」

---

### Workstream C：Equivalence Reframing And Validation

優先級：`P1`

#### 問題陳述

目前 `equivalence` 一詞使用過重。現行 tester 衡量的是 textual / structural fidelity，不是 strict equivalence。

#### 目標

讓 naming、evidence、實際測試方法對齊。

#### 主要工作

1. 將現行測試重新命名為 `fidelity`、`compatibility` 或等價用語
2. 在 API / DB / dashboard / docs 中收斂這組用語
3. 保留現行 textual tester，但明確降級它的語義地位
4. 另立一份 strict equivalence benchmark design
5. 設計「行為差異」驗證方法，至少先用 fixture-based 人工審查版落地

#### 主要交付

- shared wording update
- tester rename / migration note
- behavior-diff benchmark spec
- canonical vs source comparison rubric

#### 驗收標準

- docs / UI / API 中不再無條件使用 `equivalence` 指涉 similarity score
- 至少有一份正式 benchmark spec 說明什麼情況下才可宣稱 strict equivalence

---

### Workstream D：Parser Evaluation And Failure Corpus

優先級：`P1`

#### 問題陳述

目前 parser 有 heuristic、有測試，但缺 ground truth 與 measured failure taxonomy，因此對外主張很難校準。

#### 目標

讓 parser quality 可被量測，而不是只能靠直覺與個案示範。

#### 主要工作

1. 建立 20-30 個人工標註 gold-set skills
2. 類型分層至少包括：
   - 工具型
   - 工作流程型
   - 指南型
   - 含多檔 supporting files 的 complex skills
3. 建立 30-50 個 failure corpus 樣本
4. 定義 precision / recall / F1 或等價指標
5. 引入 confidence / ambiguity / unresolved 狀態
6. 發布 parser benchmark report

#### 主要交付

- gold dataset
- failure corpus
- parser evaluation report
- ambiguity handling guideline

#### 驗收標準

- 對外文件不再只說「工具型好用 / 指南型 30%」，而是有可追溯 benchmark
- parser failure cases 有明確分類，而不是被統稱為「不夠 parseable」

---

### Workstream E：Search Layer Calibration

優先級：`P2`

#### 問題陳述

在 contract 尚未收斂前，search 的質量討論容易失焦。收斂後仍需回答：

- embedding search 相對 TF-IDF 是否真的有增益
- similarity score 應如何解讀
- 是否需要 domain-specific tuning

#### 目標

把 search 從「看起來合理」推進到「有基準、可比較、可解釋」。

#### 主要工作

1. 定義 retrieval benchmark query set
2. 建立 TF-IDF baseline
3. 量測 top-k relevance
4. 校準 similarity score 語言
5. 決定是否值得做 domain tuning 或維持 generic model

#### 主要交付

- search benchmark report
- scoring interpretation note
- model selection decision note

#### 驗收標準

- search layer 有 baseline comparison，不再只是 demo
- 文件中對 similarity score 的描述與實作一致

---

### Workstream F：External Review Baseline Refresh

優先級：`P0-P1`

#### 問題陳述

目前外部審查文件之間有兩種問題：

- operational maturity 與 conceptual maturity 混在一起
- 部分文件引用舊數字、舊版本、舊判斷

#### 目標

把對外說法收斂成一套可信的外部審查包。

#### 主要工作

1. 區分「可運行基線」與「概念成熟度」兩種判定
2. 刪除或標註過時數字
3. 補入 canonical contract 問題與已知 failure cases
4. 保留 Devil's Advocate 的壓力測試價值，但改成 evidence-calibrated wording
5. 建立 authoritative review bundle index

#### 主要交付

- refreshed external review report
- review bundle index
- outdated doc classification note

#### 驗收標準

- 對外送審文件不再互相矛盾
- 每個重要結論都能追溯到明確 evidence

---

## 6. 執行排序

### 6.1 依賴關係

建議依賴如下：

> A → B → C → F  
> A → D → E

解讀：

- **A** 是所有工作的基底，必須最先做
- **B** 依賴 contract 收斂，否則 revision 設計會建立在漂移資料模型上
- **C** 依賴 B 的治理語義與 A 的 contract 收斂
- **D** 可在 A 完成後並行展開
- **E** 不應早於 A，否則 benchmarking 對象本身不穩
- **F** 需等 A/B/C 至少有初步結果後再定稿

### 6.2 建議分期

#### Phase 0：止血與收斂（1 週）

目標：

- 凍結 contract 漂移
- 明確 source of truth
- 補 CI gate
- 刷新對外數字與 wording

完成條件：

- authoritative contract 決策完成
- parsed validation pipeline 建立
- docs count / version wording 完成第一輪刷新

#### Phase 1：核心重構（2-3 週）

目標：

- revision-centric governance 設計與 migration
- equivalence wording 修正
- gold set / failure corpus 建立

完成條件：

- governance schema design 定稿
- fidelity/equivalence 語言切分完成
- parser benchmark 基線建立

#### Phase 2：驗證與校準（2 週）

目標：

- search benchmark
- parser benchmark 第一輪
- 對外審查包更新

完成條件：

- search baseline report 完成
- parser evaluation report 完成
- refreshed external review bundle 完成

---

## 7. 成功指標

本計劃建議採用以下指標：

### 7.1 Contract 指標

- authoritative dataset schema validation error = `0`
- CI 中 contract drift check = `required`
- repo 主文件中的 schema version / skill count / parsed count 一致

### 7.2 Governance 指標

- 新的 approval / reject / block 100% 綁定 `revision_id`
- revision record 100% 具備 checksum 或同等 artifact identity
- audit log 可追溯 artifact revision

### 7.3 Evaluation 指標

- gold dataset `>= 30`
- failure corpus `>= 30`
- parser benchmark 正式發布
- search baseline 與 embedding benchmark 都有文件化結果

### 7.4 Review 指標

- 對外文件不再無條件使用「equivalence」描述 similarity score
- 對外文件中至少納入 3 個 failure cases
- 對外文件中明確區分 operational maturity 與 conceptual maturity

---

## 8. 風險與對策

### 8.1 改 contract 會打破既有 consumer

對策：

- 明確標示 compatibility window
- 提供 adapter / migration script
- 在一個小版本週期內暫時支援舊輸出

### 8.2 Governance 重構可能拖慢 feature 進度

對策：

- 明確宣告近期不新增大型 dashboard 功能
- 先修語義基礎，再談表面能力

### 8.3 Gold set 建立成本高

對策：

- 先做小型但高品質的人工標註集
- 優先覆蓋高爭議類型，而非追求大數量

### 8.4 團隊再次被 `2.5` 擴張吸走

對策：

- `2.5` 所有新增欄位進入 parking lot
- 未完成 A/B/C 前，不推進正式 schema 擴張

---

## 9. 立即行動清單（未來 10 個工作項目）

1. 決策 authoritative contract 的 source of truth
2. 產出 schema / parser / parsed / embedder mismatch matrix
3. 在 CI 中加入 parsed schema validation
4. 修正 README / AGENTS / docs 中過時的 skill count 與 schema wording
5. 為 governance 設計 revision-centric data model 草案
6. 把現行 `equivalence` wording 降級為 `fidelity` 或等價用語
7. 建立 gold dataset 樣板與標註規則
8. 建立 failure corpus 收集格式
9. 定義 search benchmark query set 與 TF-IDF baseline
10. 重寫外部審查包，使其區分 operational 與 conceptual maturity

---

## 10. 結語

本改善計劃的核心精神很簡單：

> `skill-0` 下一步最重要的工作，不是再多做一層功能，而是把「它到底在宣稱什麼、它到底能證明什麼」這件事收斂清楚。

如果本計劃執行成功，`skill-0` 的價值敘事將會更清楚：

- 它不是「看起來很完整的 prototype」
- 而是「在 contract、governance、evaluation 上有清楚邊界與證據的系統」

這會比再加一頁 dashboard、更能提高它在外部審查中的可信度。
