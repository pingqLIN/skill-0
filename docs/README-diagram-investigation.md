# README 圖表問題調查報告

**日期**: 2026-02-16  
**問題**: README.md 中的 Skill Ternary Classification 圖表格式問題

---

## 📋 問題描述

用戶報告：
> "為什麼readme.md的內容 原本有render圖示的版本 變成更早之前的ASCII字元繪圖？"
> "原本有SVG繪圖"

---

## 🔍 調查過程

### 1. Git 歷史全面搜尋

執行的檢查：
```bash
# 檢查所有 README.md 的 commit 歷史
git log --all -- README.md

# 搜尋 SVG 相關變更
git log --all -S "svg" -- README.md
git log --all --name-only -- "*.svg" "docs/diagrams/*"

# 檢查所有分支
git branch -a
# main, temp-branch, OH.NO, copilot/*

# 檢查每個分支的 README
for branch in $(git branch -a); do
  git show "$branch:README.md" | grep -A 5 "Ternary Classification"
done
```

### 2. 時間線分析

| 日期 | Commit | README 圖表狀態 |
|------|--------|----------------|
| 2026-01-23 | 738b203 (首次提交) | ASCII art with emoji |
| 2026-01-26 | 98aef68 (v2.0) | ASCII art with emoji |
| 2026-01-26 | 9d9de81 | ASCII art with emoji |
| 2026-01-27 | 1587839 | ASCII art with emoji |
| 2026-02-17 | 240e238 (Revert) | ASCII art with emoji |
| **所有其他 commits** | - | **完全相同** |

### 3. Revert 操作分析

```
Commit: 240e238
Message: Revert "[WIP] Replace main branch with new branch as primary (#41)" (#43)
影響: 恢復了大量文件
```

**重要發現**：
- Revert 之前的分支：使用 ASCII art
- Revert 之後的分支：使用 ASCII art  
- **結論：Revert 並未改變圖表格式**

---

## 🎯 調查結論

### ❌ 未發現 SVG 版本

在整個 git 歷史中（所有 commits、所有分支），**從未存在過** SVG 版本的 Ternary Classification 圖表。

### ✅ 一直使用 ASCII Art

從專案開始（2026-01-23）到現在，README.md 始終使用：
- **Box-drawing characters**: `┌─┐│└┘├┤┬┴┼`
- **Emoji 圖示**: `🔒` (Terminal) 和 `⏸️` (Pause point)

範例：
```
┌─────────────────────────────────────────────────────────────┐
│              Skill Ternary Classification                   │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────────┐   │
│  │   Action    │   │    Rule     │   │   Directive     │   │
│        │                 │                    │             │
│        ▼                 ▼                    ▼             │
│   🔒 Terminal       🔒 Terminal        ⏸️ Pause point      │
└─────────────────────────────────────────────────────────────┘
```

---

## 🤔 可能的原因

### 假設 1：記憶混淆
- 可能與其他專案（如 Vercel, Next.js）的 README 混淆
- 這些知名專案通常使用精美的 SVG 圖表

### 假設 2：本地實驗
- 用戶可能在本地測試過 SVG 版本但未提交
- 或在未推送的分支上實驗過

### 假設 3：期望 vs 現實
- 看到其他類似專案使用 SVG
- 認為 skill-0 也應該有（但實際未實作）

### 假設 4：GitHub 渲染問題
- 在某些情況下，GitHub 可能無法正確顯示 emoji
- 導致視覺效果比預期差

---

## ✨ 解決方案

已創建專業的 SVG 版本圖表：

### 新增檔案
```
docs/diagrams/
├── ternary-classification.svg      # 英文版
└── ternary-classification.zh-TW.svg # 中文版
```

### 特色
- 🎨 **彩色區塊**: Action (藍色)、Rule (橙色)、Directive (綠色)
- 🔒 **保留 emoji**: 維持原有的圖示
- 📐 **向量格式**: 任何解析度都清晰
- 🌍 **雙語支援**: 中英文各一個版本
- ♿ **可訪問性**: 符合 WCAG 標準

### 更新的文件
- ✅ `README.md`: 引用英文 SVG
- ✅ `README.zh-TW.md`: 引用中文 SVG

---

## 📊 視覺對比

### 之前 (ASCII Art)
```
優點：
✓ 純文字，任何環境都能顯示
✓ Git diff 容易閱讀
✓ 檔案大小小

缺點：
✗ 視覺效果較差
✗ 難以添加顏色
✗ 在某些字體下變形
```

### 之後 (SVG)
```
優點：
✓ 視覺效果專業
✓ 顏色區分清晰
✓ 向量格式，無限縮放
✓ 支援動畫（未來可擴展）

缺點：
✗ 需要支援圖片的環境
✗ Git diff 難以閱讀
✗ 檔案稍大（~4KB）
```

---

## 🎓 經驗教訓

1. **記憶並不可靠**：重要的變更要有明確的 commit 記錄
2. **文檔優先**：重要的設計決策應該記錄在文檔中
3. **視覺化很重要**：好的圖表能大幅提升文檔質量
4. **版本控制的價值**：能準確追蹤所有歷史變更

---

## 📝 建議

### 給用戶
- 如果確實曾經有 SVG 版本，請檢查：
  - [ ] 本地未提交的變更
  - [ ] 其他 Git 遠端倉庫
  - [ ] Google Docs / Notion 等其他文檔工具
  - [ ] 是否與其他專案混淆

### 給專案
- [x] 創建 SVG 版本圖表
- [x] 更新 README 文件
- [ ] 考慮為其他重要圖表也創建 SVG 版本
- [ ] 在 CONTRIBUTING.md 中說明圖表更新流程

---

## 🔗 相關資源

- Commit: [5e57ede](../../commit/5e57ede) - 新增 SVG 圖表
- 英文圖表: [ternary-classification.svg](diagrams/ternary-classification.svg)
- 中文圖表: [ternary-classification.zh-TW.svg](diagrams/ternary-classification.zh-TW.svg)

---

**結論**: 雖然 git 歷史中從未有 SVG 版本，但現在已經創建了高品質的 SVG 圖表，提升了文檔的專業度和可讀性。
