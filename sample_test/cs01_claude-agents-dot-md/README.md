# Sample: Claude Agents.md Format + Test Suite Example

> 範例：Claude Agents.md 格式 + 測試套件示例

這個目錄包含了 skill-0 專案中關於 Claude Agents.md 格式和自動化測試套件的完整範例。

This directory contains complete examples from the skill-0 project regarding Claude Agents.md format and automated test suite.

## 📁 目錄結構 Directory Structure

```
cs01_claude-agents-dot-md/
├── README.md                      # 本檔案 This file
├── AGENTS.md                      # Claude Agents.md 格式範例
├── pyproject.toml                 # Pytest 配置
├── helper.py                      # 輔助工具腳本
├── test-equivalence-report.md     # 測試等效報告
└── tests/                         # 測試套件目錄
    ├── __init__.py
    ├── README.md                  # 測試文檔
    ├── test_helper.py             # 32 個自動化測試
    └── fixtures/                  # 測試固件
        ├── valid_skill.json
        ├── invalid_skill.json
        └── sample.md
```

## 📚 內容說明 Contents Description

### 1. AGENTS.md
- 遵循 https://agents.md 格式標準
- 為 AI 代理提供專案指南
- 包含開發環境提示、編碼規範、常見任務

Follows https://agents.md format standard. Provides project guidelines for AI agents including development environment tips, coding conventions, and common tasks.

### 2. Test Suite (tests/)
- **32 個自動化測試** (100% 通過率)
- 測試類別：
  - 工具等效測試 Tool Equivalence (8 tests)
  - 程式碼等價測試 Code Equivalence (7 tests)
  - 執行路徑測試 Execution Testing (6 tests)
  - 模板生成測試 Template Generation (4 tests)
  - 整合測試 Integration (4 tests)
  - 錯誤處理 Error Handling (3 tests)

### 3. pyproject.toml
- Pytest 配置檔案
- 定義測試路徑、選項、覆蓋率設定

Pytest configuration file defining test paths, options, and coverage settings.

### 4. helper.py
- 輔助工具腳本
- 提供驗證、轉換、測試功能
- 包含 SkillValidator、SkillConverter、SkillTester 類別

Helper utility script providing validation, conversion, and testing capabilities.

### 5. test-equivalence-report.md
- 完整的測試報告（中英雙語）
- 詳細的測試結果和分析
- 包含執行範例和品質指標

Comprehensive bilingual test report with detailed results, examples, and quality metrics.

## 🚀 如何使用 How to Use

### 運行測試 Run Tests

```bash
# 安裝依賴 Install dependencies
pip install pytest

# 運行所有測試 Run all tests
python3 -m pytest tests/ -v

# 運行特定測試 Run specific tests
python3 -m pytest tests/test_helper.py::TestSkillValidator -v
```

### 使用輔助工具 Use Helper Utilities

```bash
# 生成模板 Generate template
python3 helper.py template -o template.json

# 驗證技能 Validate skill
python3 helper.py validate skill.json

# 測試執行路徑 Test execution paths
python3 helper.py test skill.json --analyze
```

## 📊 測試結果 Test Results

```
✅ 總測試數 Total Tests: 32
✅ 通過率 Pass Rate: 100% (32/32)
✅ 執行時間 Execution Time: 0.09 seconds
✅ 覆蓋率 Coverage: 100% of helper.py
```

### 測試類別分布 Test Distribution

| 測試類別 Test Category | 數量 Count | 狀態 Status |
|----------------------|-----------|-----------|
| TestSkillValidator | 8 | ✅ PASSED |
| TestSkillConverter | 7 | ✅ PASSED |
| TestSkillTester | 6 | ✅ PASSED |
| TestTemplateGeneration | 4 | ✅ PASSED |
| TestIntegrationWorkflows | 4 | ✅ PASSED |
| TestErrorHandling | 3 | ✅ PASSED |

## 🎯 關鍵特性 Key Features

### 工具等效性驗證 Tool Equivalence
- 驗證器一致性測試
- 多個實例產生相同結果
- 模板生成總是有效

Validator consistency tests verify multiple instances produce identical results. Template generation is always valid.

### 程式碼等價性驗證 Code Equivalence
- 轉換器確定性測試
- 相同輸入產生相同輸出
- 工作流程可重現

Converter determinism tests verify same input produces same output. Workflows are reproducible.

## 📖 文檔參考 Documentation References

- **AGENTS.md**: AI 代理開發指南
- **tests/README.md**: 測試套件完整文檔
- **test-equivalence-report.md**: 詳細測試報告

## 💡 使用案例 Use Cases

1. **學習參考 Learning Reference**
   - 了解如何編寫 AGENTS.md
   - 學習自動化測試最佳實踐
   - 參考測試結構和模式

2. **專案模板 Project Template**
   - 作為新專案的起點
   - 複製測試基礎設施
   - 採用文檔格式標準

3. **品質保證 Quality Assurance**
   - 驗證工具等效性
   - 確保程式碼等價性
   - 實施自動化測試

## 🔗 相關資源 Related Resources

- agents.md 格式標準: https://agents.md
- skill-0 專案: https://github.com/pingqLIN/skill-0
- Pytest 文檔: https://docs.pytest.org/

---

**建立日期 Created**: 2026-01-28  
**版本 Version**: v2.3.0  
**狀態 Status**: ✅ Complete with 100% test coverage
