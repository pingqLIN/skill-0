# 規劃：新增 20 個 Skills 測試分析

Status note:
- This is a historical expansion-plan document written for the earlier `11 -> 31 skills` validation phase.
- It should be treated as gated backlog, not as the current execution baseline for the `v2.4.0` contract/governance work.
- Current sequencing and gates are maintained in [executable-dev-plan-2026-03-31.zh-TW.md](<repo-root>/docs/planning/executable-dev-plan-2026-03-31.zh-TW.md).

## 📋 目標
- 從 GitHub awesome-claude-skills 倉庫選取 20 個不同類型的 skills
- 擴大測試集合（當前 11 個 → 31 個）
- 驗證框架 v2.0 對於多元 skills 的覆蓋率
- 評估分析器效能表現

---

## 🎯 技術目標

### 覆蓋率指標
- 目前: 92% 整體覆蓋率（11 skills）
- 目標: ≥ 90% 整體覆蓋率（31 skills）
- Action 類型覆蓋: 100%
- Directive 類型覆蓋: ≥ 85%

### 效能目標
- 分析器性能: ≤ 1.5s（31 skills）
- 每個 skill 平均: ≤ 50ms
- 可擴展性測試: 驗證線性時間複雜度

---

## 📂 Skills 選擇策略 - 20 個新增 Skills

### 分類分佈（按類型）

#### 📄 文件處理 (5 個)
已有: pdf, xlsx, docx, pptx
新增:
1. **document-skills** - 通用文件處理
2. **changelog-generator** - 變更日誌自動生成
3. **invoice-organizer** - 發票組織管理
4. **tailored-resume-generator** - 客製化履歷產生
5. **video-downloader** - 影片下載工具

#### 💻 開發工具 (5 個)
已有: mcp-builder, webapp-testing, skill-creator, code-review
新增:
6. **langsmith-fetch** - LangSmith 資料取得
7. **connect-apps** - 應用連接
8. **connect** - 通用連接工具
9. **competitive-ads-extractor** - 競爭廣告提取
10. **developer-growth-analysis** - 開發者成長分析

#### 🎨 創意設計 (3 個)
已有: canvas-design
新增:
11. **brand-guidelines** - 品牌指南管理
12. **theme-factory** - 主題工廠
13. **slack-gif-creator** - Slack GIF 建立

#### 📊 業務分析 (4 個)
14. **content-research-writer** - 內容研究寫手
15. **lead-research-assistant** - 潛客研究助手
16. **meeting-insights-analyzer** - 會議洞察分析
17. **twitter-algorithm-optimizer** - Twitter 演算法優化
18. **domain-name-brainstormer** - 域名腦力激盪

#### 🔧 工具/其他 (3 個)
已有: file-organizer, image-enhancer, internal-comms
新增:
19. **raffle-winner-picker** - 抽獎贏家選擇
20. **skill-share** - Skill 分享平台
21. **connect-apps-plugin** - 應用連接插件

---

## 📊 現有 Skills 統計

| 類型 | 數量 | Skills |
|------|------|--------|
| 📄 文件處理 | 4 | pdf, xlsx, docx, pptx |
| 💻 開發工具 | 4 | mcp-builder, webapp-testing, skill-creator, code-review* |
| 🎨 創意設計 | 1 | canvas-design |
| 🔧 工具/其他 | 3 | file-organizer, image-enhancer, internal-comms |
| **小計** | **11** | |

*code-review 非原始 11 個，此為誤差修正

---

## 📈 預期結果

### 數量預測（31 個 skills 總計）

基於 11 個 skills 的比率：
- **Actions**: 11 × (63/11) = 63 個 → 預期 155-170 個（20 個新）
- **Rules**: 11 × (28/11) = 28 個 → 預期 70-80 個
- **Directives**: 11 × (30/11) = 30 個 → 預期 75-85 個

### 模式發現

新 skills 可能識別的新模式：
- 商業流程模式（內容、行銷、分析）
- 連接/整合模式（connect, plugin）
- 生成/最佳化模式（優化器、產生器）

### 性能指標

預期分析時間：
```
Analyzer:    0.263s × (31/11) ≈ 0.74s
Extractor:   0.257s × (31/11) ≈ 0.72s
Total:                      ≈ 1.46s
```

---

## ✅ 工作計畫

### 階段 1: 準備 (1-2 小時)
- [ ] 確認 20 個 skills 來源
- [ ] 取得每個 skill 的完整定義
- [ ] 分類整理（按 skills 類型）

### 階段 2: 解析 (2-4 小時)
- [ ] 運行 batch_parse.py 解析 20 個 skills
- [ ] 轉換為 v2.0 JSON 格式
- [ ] 驗證每個解析結果

### 階段 3: 分析 (1-2 小時)
- [ ] 執行 analyzer.py（31 個 skills）
- [ ] 執行 pattern_extractor.py
- [ ] 執行 evaluate.py 評估覆蓋率

### 階段 4: 評估 (1 小時)
- [ ] 檢查覆蓋率是否 ≥ 90%
- [ ] 比較性能指標
- [ ] 識別新的模式和趨勢
- [ ] 產出評估報告

### 階段 5: 提交 (30 分鐘)
- [ ] 整理所有解析文件
- [ ] 更新分析結果
- [ ] Git commit
- [ ] 更新 README

---

## 🔍 質量檢查清單

- [ ] 所有 20 個 skills 都有有效的 SKILL.md 或等效文件
- [ ] 解析率 ≥ 95%
- [ ] 沒有重複的 skill 定義
- [ ] action/rule/directive 分類符合 v2.0 規範
- [ ] 性能無顯著退化

---

## 💾 輸出成果物

1. **parsed/** 目錄
   - 20 個新 skills 的 JSON 文件

2. **analysis/** 報告
   - 更新的 report.json（31 skills）
   - 更新的 patterns.json
   - 更新的 evaluation_report.json

3. **統計摘要**
   - action/rule/directive 分佈
   - 按類型的覆蓋率
   - 性能基準測試

4. **Git 提交**
   - Commit 訊息：`feat: Add 20 new skills for framework v2.0 validation`

---

## 📌 備註

### 已識別的可選 skills
如果 20 個不足或有些無法取得，備選清單：
- algorithmic-art
- artifacts-builder
- frontier-research-assistant
- aws-cost-optimizer
- github-action-creator
- kubernetes-debugger

### 框架限制
- 某些 skills 可能為指南型（覆蓋率低）- 預期並記錄
- MCP tools 可能有不同的分解方式 - 需特別注意

### 下一步（Stage 2）
- 向量化 31 個 skills 數據集
- 評估語義相似度聚類
- 識別可能的 skills 衍生機會
