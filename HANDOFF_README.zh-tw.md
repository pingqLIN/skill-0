# Skill-0 Phase 1 Freeze & Handoff Guide

本文件是 Phase 1 Freeze & Handoff Package 的權威入口；英文版
[HANDOFF_README.md](HANDOFF_README.md) 為權威版本。

## 專案目前進度

Production Admission Phase 1 已在 freeze 來源 commit
`71ce496baa3c1076679f244c82700c3bf65d1297` 達到 `COMPLETE`。Repository 已包含
有效的 admission contract、schema、fail-closed verifier、直接測試、security
integration、雙語 operator handoff 與 recovery 文件。

Production Admission Phase 2 為 `WAITING_FOR_OPERATOR_EVIDENCE`。本套件未准許
任何 production environment 進入正式環境。

## 建議閱讀順序

1. [CURRENT_STATE.zh-tw.md](CURRENT_STATE.zh-tw.md)：精簡的目前狀態與限制。
2. [PHASE1_FREEZE_RECORD.zh-tw.md](PHASE1_FREEZE_RECORD.zh-tw.md)：凍結範圍與
   驗證紀錄。
3. [PHASE2_OPERATOR_CHECKLIST.zh-tw.md](PHASE2_OPERATOR_CHECKLIST.zh-tw.md)：
   下一個閘門需要的人工項目。
4. [Runtime Production Admission v1](docs/contracts/runtime-production-admission-v1.zh-tw.md)：
   權威 admission contract。
5. [Production Operator Handoff](docs/production-operator-handoff.zh-tw.md) 與
   [Recovery Runbook](docs/production-admission-recovery.zh-tw.md)：受保護證據流程與
   fail-closed 重新進入程序。

## 下一個 Agent 不得修改的項目

不得以本次 handoff 為由修改 verifier logic、schema、security model、production
admission contract、Runtime authority boundary 或 ARD／Evidence semantics。不得新增
real adapter、啟用非 dry-run execution、部署、公開 route 或建立 production package。

未來任何功能變更都需要獨立界定範圍並完成審查，不屬於 Phase 1 freeze package。

## 下一個 Agent 可以進行的工作

- 使用連結的權威文件說明或驗證 frozen repository state。
- 重新執行 repository tests 與 schema validation，但不得捏造證據。
- 協助授權操作員理解 Phase 2 checklist。
- 只有在操作員透過核准的受保護流程提供 artifact 後，才能驗證其結構。
- 依精確來源與 evidence state 記錄真實驗證結果。

## 需要人工介入的工作

- 識別 production environment。
- 提供由獨立角色控制的 trusted keyring location。
- 觀察並提供精確 deployed image 與 mounted model digests。
- 提供最新 security、regression、rehearsal 與 external-control evidence。
- 由授權的 `production-admission-approver` 審閱並簽署。
- 決定通過驗證的 package 是否授權 deployment 或 promotion。

AI Agent 不是 production approver，不得簽署或捏造上述任何項目。

## 驗證命令

在 Windows 的 repository root 執行：

```powershell
.\.venv\Scripts\python.exe -m pytest tests skill-0-dashboard\apps\api\tests -q --timeout=120
.\.venv\Scripts\python.exe -m pytest tests\test_runtime_admission_check.py -q --timeout=120
.\.venv\Scripts\python.exe tools\validate_skill_schema.py parsed
git diff --check
```

Frontend 驗證需在 `skill-0-dashboard/apps/web` 執行：

```powershell
npm.cmd run lint
npm.cmd test
npm.cmd run build:ci
```

上述命令只驗證 repository behavior，不能產生或取代 production evidence。

## 停止條件

只要缺少任何人工證據，就必須停止並回報 `WAITING_FOR_OPERATOR_EVIDENCE`。過期、
不相符、遭竄改、已撤銷、environment 錯誤、release 錯誤、synthetic 或未授權的
證據都必須視為 blocked。絕對不可將 unknown result 提升為 `VERIFIED`。
