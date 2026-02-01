# MiniMe Agent 使用指南

## 概述

**MiniMe Agent** 是一個全域 GitHub 檔案系統操作代理，可在任何 GitHub repository 中被召喚執行檔案操作任務。

### 核心特性

- ✅ **全域可用**：不限定於特定專案，可在任何 GitHub repository 中使用
- ✅ **完整權限**：建立 repository、刪除檔案、審查任務
- ✅ **明確啟動**：必須透過訊息或 email 明確指令啟動
- ✅ **自動關閉**：完成任務後自動釋放資源
- ✅ **內容保護**：不審查或修改檔案內容（除非程序問題）
- ✅ **跨 Repository**：可存取和操作任何有權限的 repository
- ✅ **安全優先**：多層驗證和安全檢查

## 技能分類

基於 skill-0 三元分類系統：

### Actions (20 個)

| ID | 名稱 | 類型 | 說明 |
|----|------|------|------|
| a_001 | Create New Repository | external_call | 在 GitHub 上建立新 repository |
| a_002 | Delete File | io_write | 刪除指定檔案 |
| a_003 | Delete Directory | io_write | 遞迴刪除目錄 |
| a_004 | Move File or Directory | io_write | 移動或重新命名 |
| a_005 | Copy File or Directory | io_write | 複製檔案或目錄 |
| a_006 | List Directory Contents | io_read | 列出目錄內容 |
| a_007 | Get File Metadata | io_read | 讀取檔案元資料 |
| a_008 | Create Directory | io_write | 建立新目錄 |
| a_009 | Set File Permissions | state_change | 修改檔案權限 |
| a_010 | Review Task Assignment | io_read | 審查原始任務 |
| a_011 | Verify Activation Signal | await_input | 驗證啟動指令 |
| a_012 | Read File Content for Diagnosis | io_read | 診斷性讀取檔案 |
| a_013 | Fix Procedural Issue | io_write | 修正程序問題 |
| a_014 | Shutdown Agent | state_change | 關閉代理 |
| a_015 | Clone Repository | external_call | Clone GitHub repository |
| a_016 | Access Cross-Repository | external_call | 跨 repository 存取 |
| a_017 | Commit and Push Changes | external_call | Commit 並 push 變更 |
| a_018 | Create Branch | external_call | 建立新分支 |
| a_019 | Delete Branch | external_call | 刪除分支 |
| a_020 | Respond to GitHub Webhook | await_input | 處理 webhook 事件 |

### Rules (12 個)

| ID | 名稱 | 類型 | 說明 |
|----|------|------|------|
| r_001 | Check Activation Signal Valid | validation | 驗證啟動令牌 |
| r_002 | Check File Exists | existence_check | 檢查檔案存在 |
| r_003 | Check Write Permission | permission_check | 檢查寫入權限 |
| r_004 | Check Delete Safety | validation | 刪除安全驗證 |
| r_005 | Check Repository Name Valid | validation | 驗證 repository 名稱 |
| r_006 | Detect Procedural Issue | state_check | 偵測程序問題 |
| r_007 | Check Task Complete | state_check | 確認任務完成 |
| r_008 | Validate Path Safety | validation | 路徑安全驗證 |
| r_009 | Check Disk Space Available | threshold_check | 檢查磁碟空間 |
| r_010 | Verify GitHub Token Valid | permission_check | 驗證 GitHub token |
| r_011 | Check Repository Access | permission_check | 檢查 repository 權限 |
| r_012 | Validate Repository Exists | existence_check | 驗證 repository 存在 |

### Directives (14 個)

| ID | 名稱 | 類型 | 說明 |
|----|------|------|------|
| d_001 | Agent Activation Protocol | principle | 啟動協定 |
| d_002 | File Content Non-Interference | constraint | 內容不干預原則 |
| d_003 | File System Operations Focus | principle | 檔案系統操作焦點 |
| d_004 | Auto-Shutdown on Completion | principle | 自動關閉原則 |
| d_005 | Full File Operation Permissions | knowledge | 完整權限說明 |
| d_006 | Safety Checks Required | constraint | 安全檢查要求 |
| d_007 | Task Review Capability | completion | 任務審查能力 |
| d_008 | Repository Creation Complete | completion | Repository 建立完成 |
| d_009 | File Deletion Complete | completion | 檔案刪除完成 |
| d_010 | Global GitHub Availability | principle | 全域可用性 |
| d_011 | Cross-Repository Operations | knowledge | 跨 repository 操作 |
| d_012 | GitHub API Integration | knowledge | GitHub API 整合 |
| d_013 | Authentication and Authorization | constraint | 認證授權要求 |
| d_014 | Webhook-Triggered Activation | strategy | Webhook 觸發策略 |

## 執行路徑範例

### 1. 標準啟動流程
```
a_011 (驗證啟動信號) → r_001 (檢查授權) → a_010 (審查任務)
```

### 2. 建立 Repository
```
r_005 (驗證名稱) → r_009 (檢查空間) → a_001 (建立 repository)
```

### 3. 安全刪除檔案
```
r_002 (檢查存在) → r_004 (安全驗證) → r_008 (路徑驗證) → 
r_003 (權限檢查) → a_002 (執行刪除)
```

### 4. 跨 Repository 存取
```
r_010 (驗證 token) → r_011 (檢查權限) → r_012 (驗證存在) → 
a_016 (執行存取)
```

### 5. Clone 並操作
```
r_010 (驗證 token) → r_011 (檢查權限) → a_015 (clone) → 
a_006 (列出檔案) → a_002 (刪除檔案)
```

### 6. Webhook 觸發操作
```
a_020 (接收 webhook) → r_001 (驗證授權) → a_016 (跨 repo 存取) → 
a_002 (刪除檔案) → a_017 (commit/push)
```

## 使用場景

### 場景 1：清理舊檔案

**需求**：在多個 repository 中刪除過期的測試檔案

**流程**：
1. 透過 email 發送啟動指令給 minime-agent
2. Agent 驗證授權後啟動
3. 遍歷指定的 repositories
4. 檢查並刪除符合條件的檔案
5. Commit 變更並 push
6. 自動關閉

### 場景 2：批次建立 Repositories

**需求**：為新專案建立多個相關 repositories

**流程**：
1. 發送包含 repository 清單的訊息
2. Agent 驗證並解析任務
3. 對每個 repository：
   - 驗證名稱可用性
   - 建立 repository
   - 初始化預設檔案
4. 回報完成狀態
5. 自動關閉

### 場景 3：程序性修正

**需求**：修正導致 CI 失敗的格式問題

**流程**：
1. GitHub webhook 觸發 (CI 失敗)
2. Agent 接收事件並驗證
3. Clone 失敗的 repository
4. 偵測程序問題 (例如：缺少換行符)
5. 修正檔案
6. Commit 並 push 修正
7. 自動關閉

### 場景 4：跨 Repository 重構

**需求**：在多個 repositories 中統一檔案結構

**流程**：
1. 發送重構指令
2. Agent 驗證並啟動
3. 對每個目標 repository：
   - 檢查存取權限
   - 讀取現有結構
   - 執行移動/重新命名操作
   - Commit 變更
4. 生成重構報告
5. 自動關閉

## 安全考量

### 必要檢查

所有操作前都會執行：

1. **啟動驗證** (r_001)：確保來自授權來源
2. **路徑安全** (r_008)：防止目錄遍歷攻擊
3. **權限檢查** (r_003, r_011)：確認操作權限
4. **刪除安全** (r_004)：避免誤刪系統檔案

### 資源要求

- **GitHub API**: 需要有效的 Personal Access Token
- **權限範圍**: 根據操作需求配置 token 權限
  - `repo`: 完整 repository 存取
  - `delete_repo`: 刪除 repository (可選)
  - `admin:org`: 組織層級操作 (可選)
- **網路連線**: 存取 GitHub API
- **本地儲存**: Clone/操作時需要磁碟空間

## 限制

1. **內容不干預**：除非程序問題，否則不修改檔案內容
2. **明確啟動**：不會自動啟動或回應未授權請求
3. **權限邊界**：僅能操作有權限的 repositories
4. **一次性執行**：完成任務後立即關閉

## 技術規格

- **Schema 版本**: 2.2.0
- **Skill ID**: `github__global__minime_agent`
- **Skill Layer**: `claude_skill`
- **動作總數**: 20
- **規則總數**: 12
- **指示總數**: 14
- **執行路徑**: 10

## 相關文件

- [Skill Definition](../data/parsed/minime-agent-skill.json) - 完整 JSON 定義
- [Schema](../schema/skill-decomposition.schema.json) - skill-0 schema v2.2.0
- [Project README](../README.md) - skill-0 專案說明

## 授權

MIT License

---

**Note**: MiniMe Agent 是基於 skill-0 框架設計的概念性 skill definition，展示了如何使用三元分類系統（Actions/Rules/Directives）來分解複雜的自主代理行為。
