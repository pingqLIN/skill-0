# 01. Project Concept and Positioning

## 1.1 Project Idea

Skill-0 最初不是從「做一個 dashboard」開始，而是從一個更根本的問題開始：

> 現有的 Claude Skills、MCP Tools、agent workflow 指南，大多以自然語言或半結構化文字存在。這些內容可閱讀，但難以比較、檢索、治理、審核，也難以進一步做自動化分析。

Skill-0 的核心構想，就是把這些原本只有人讀得懂的技能說明，拆成可被機器索引、比較、治理的結構化表示。

## 1.2 Core Problem Statement

這個專案要解的不是單一技術問題，而是一組相互關聯的問題：

1. 技能說明多為非結構化文字，難以建立 inventory。
2. 技能之間常有語義重疊，但靠檔名與目錄無法有效去重。
3. 技能品質、來源、授權、風險與等價性缺少標準化治理流程。
4. 想建立審核、比對、搜尋與知識重用時，沒有共同資料模型。

Skill-0 因此同時具備三個面向：

- schema：把技能拆成標準結構
- search：把技能變成可語義搜尋的知識庫
- governance：把技能納入可審核與可追蹤的工作流

## 1.3 Why the Ternary Model Matters

Skill-0 的概念核心，是三元分類模型：

- Action：原子操作
- Rule：原子判斷
- Directive：描述性陳述

這個模型的重要性在於，它不是只為了「把文字分三類」，而是提供一個足以支撐後續索引、模式分析、比對與治理的最小抽象層。

實際上：

- Action 回答的是「做什麼」
- Rule 回答的是「怎麼判斷」
- Directive 回答的是「依據什麼狀態、知識、原則或限制」

這讓技能不再只是 markdown 說明，而是可被拆解成一組可查詢、可比較、可審核的元素。

## 1.4 What Skill-0 Is Not

為了避免誤解，Skill-0 不應被定義為：

- 單純的 markdown parser
- 直接取代原始 skill authoring 格式的編輯器
- 執行 skill 的 orchestration runtime
- 完整的 agent platform

更準確的說法是：

> Skill-0 是一個把技能與工具說明轉換成可分析、可搜尋、可治理資料層的系統。

## 1.5 Product Positioning

從目前 repo 的實作看，Skill-0 的產品定位已經從「schema proof-of-concept」擴展成：

- 一個 skill decomposition framework
- 一個 local-first semantic search service
- 一個治理與審核後台

因此它的實際角色介於下列幾者之間：

- 規格層：提供 schema 與 decomposition vocabulary
- 平台層：提供 API、搜尋、dashboard、governance workflow
- 知識層：把 skill inventory 變成 queryable asset

## 1.6 Adoption Strategy

專案採取的是相對務實的 sidecar adoption 路徑，而不是強迫全面重寫。

其策略是：

1. 保留原有技能格式不動。
2. 額外生成 Skill-0 JSON 作為 sidecar artifact。
3. 先把搜尋、治理、審查工作流建立起來。
4. 等資料層穩定後，再決定是否反向影響 authoring 規範。

這個策略的優點是：

- 導入成本低
- 不破壞原始內容
- 可以先驗證 search / governance 的價值

代價則是：

- 早期會同時維護兩份 artifact
- decomposition 品質與原文對齊仍需治理

## 1.7 Current Project Shape

截至目前，Skill-0 已經不是純理論框架，而是具備完整產品輪廓：

- schema 與 parsed dataset
- vector search layer
- core search API
- governance DB 與治理工具
- dashboard API
- React dashboard web
- Docker 化與 production-style compose

因此，現在對 Skill-0 最準確的描述是：

> 一個以三元分類模型為基礎、面向技能治理與檢索的結構化知識與審核平台。
