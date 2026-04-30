# Skill-0 Conversation Memo
**Date:** 2026-04-30  
**User:** Project Maintainer  
**Topic:** `agent-skills` / `skill-0` / `UniText` 比較，聚焦 `using-agent-skills`、`Meta-skill`、`skill discovery`，並保存下次重啟專案時的提醒

---

## Raw Archive

- Raw conversation archive:
  `C:\Users\miles\.agents\.little_talks\2026-04-30_skill-0-agent-skills-meta-skill-discovery.md`

---

## 背景

這次對話先比較了 `addyosmani/agent-skills`、`skill-0`、`UniText` 三者的定位與合作方式，之後再把焦點縮到 `skill-0` repo 本身，專門釐清以下三個概念：

1. `using-agent-skills`
2. `Meta-skill`
3. `skill discovery`

使用者另外明確要求：

- 遇到疑問、缺資訊時，一定要先詢問
- 如果擔心長程序一開始就停住，可以用倒數計時方式給緩衝

---

## 對話重點整理

### 1. 三個概念不是同一層

- `skill discovery` 是「找到該用哪個 skill」的能力或機制
- `Meta-skill` 是「管理其他 skill 如何被選用」的 skill 類型
- `using-agent-skills` 是 `agent-skills` repo 裡那個實際存在的 meta-skill 實作

一句話：

- `skill discovery` = 機制 / 目的
- `Meta-skill` = 類別 / 角色
- `using-agent-skills` = 實際檔案 / 實例

### 2. `using-agent-skills` 的本質

它不是普通技能，而是總入口 skill，用來：

- 根據任務階段選 skill
- 阻止 agent 跳過 skill 直接硬做
- 把工作映射到生命週期，例如 spec / plan / build / test / review / ship

因此它的價值不在領域知識，而在：

- workflow discipline
- intent routing
- skill orchestration

### 3. `Meta-skill` 的本質

Meta-skill 不直接處理 UI、API、測試、部署本身，而是處理：

- 什麼時候該用 skill
- 該用哪個 skill
- 何時切換 skill
- 何時先澄清需求
- 何時先 spec / plan / verify

所以 meta-skill 是 skill system 的「調度層」，不是「執行層」。

### 4. `skill discovery` 在兩個系統裡不是同一件事

在 `agent-skills`：

- discovery 偏向 task-time routing
- 問的是「這個任務現在該載入哪個 skill」

在 `skill-0`：

- discovery 偏向 corpus-time search / analysis / governance
- 問的是「整個 skill corpus 裡有哪些可搜尋、可比較、可治理的關係」

對 `skill-0` 目前比較準確的描述是：

- semantic search
- vector embeddings
- pattern discovery
- clustering
- deduplication
- governance review

也就是：`skill-0` 已經有強 discovery，但主要是知識搜尋與治理層，不是 session 開場的 workflow router。

### 5. 對 `skill-0` 的直接結論

`skill-0` 缺的不是 discovery 本身，而是：

- 缺少一個類似 `using-agent-skills` 的 meta-router
- 缺少任務進來後，先決定該走 search / parse / analyze / govern / compare 哪條工作路徑的入口 skill

因此最合理的方向不是把 `using-agent-skills` 原封搬進 `skill-0`，而是：

- 依照 `skill-0` 本身的能力模型，做一個 `skill-0` 專用 meta-skill

---

## 關於三者比較的保留結論

這次對話前半段的高層結論保留如下：

- `UniText` 適合當 canonical registry + runtime + governance backbone
- `agent-skills` 適合當 execution/workflow design pattern source
- `skill-0` 適合當 decomposition / primitive extraction / search / governance sidecar pipeline

因此不是三選一，而是分層合作。

---

## 建議方向

### A. 為 `skill-0` 製作一個專用 meta-skill

建議讓它負責入口判斷，例如：

- 想找既有 skill：走 semantic search
- 想匯入新 corpus：走 parse / normalize / validate
- 想看重複與共通 pattern：走 analyzer / pattern extractor
- 想做治理審查：走 governance workflow
- 想比較兩套 skill 生態：走 comparison / dossier flow

### B. 不要直接複製 `using-agent-skills`

可吸收的是：

- workflow routing 思想
- 先選 skill 再做事的 discipline
- meta-skill 作為總入口的設計

不應直接照搬的是：

- 以軟體開發生命週期為核心的 phase map

因為 `skill-0` 的主要工作型態不是一般 coding task，而是：

- parse
- classify
- index
- search
- compare
- govern

### C. 後續可產出的正式成果

本次 memo 導出的候選正式產物：

1. `skill-0` 專用 `using-agent-skills` / meta-router 草案
2. `skill-0` 任務入口 decision tree
3. `skill-0` 與 `agent-skills` 的合作 / 吸收設計說明
4. 若要與 `UniText` 協作，則補一份分層整合說明

---

## 未解問題

目前還沒有正式定稿的部分：

- `skill-0` 的 meta-router 要放在 repo root `SKILL.md`、新增獨立 skill、還是只先寫成設計文
- task routing 要不要直接映射到現有 CLI / API / dashboard 功能
- 是否要把「遇到疑問一定先詢問」寫進 `skill-0` 的常駐入口規則

---

## 下次重啟專案時提醒

下次重啟 `skill-0` 時，先提醒以下事項：

1. 這次已經確認 `skill-0` 的強項是 semantic search / governance / decomposition，不是現成的 workflow meta-skill。
2. 若下一步要延伸 `agent-skills` 的設計，目標不是直接搬運 `using-agent-skills`，而是做 `skill-0` 版本的 meta-router。
3. 先問清楚本輪要做的是哪一種：
   - 說明概念
   - 撰寫設計稿
   - 直接實作 router / meta-skill
   - 整合到既有 `SKILL.md` / `AGENTS.md`
4. 若遇到資訊不足或方向不清，必須先詢問；必要時可用倒數緩衝，不要直接假設。

建議下次開工時可以直接用這句作為啟動確認：

> 本次要延續的是「`skill-0` 專用 meta-skill / using-agent-skills router」方向，還是只做比較與文件整理？

---

## Repo State Note

建立此 memo 時，repo worktree 不是完全乾淨，存在未追蹤檔：

- `agent-governance-resolution.json`
- `agent-governance-resolution.json:Zone.Identifier`
- `agent-governance-resolution.md`
- `agent-governance-resolution.md:Zone.Identifier`

此次 memo 為使用者明確同意後寫入，不視為清理或覆寫既有未追蹤內容。
