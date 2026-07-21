# Skill-0 目前狀態

本文件是 Phase 1 Freeze & Handoff Package 的精簡狀態快照；英文版
[CURRENT_STATE.md](CURRENT_STATE.md) 為權威版本。

## 專案識別

- Repository：`pingqLIN/skill-0`
- Release candidate branch：`release/runtime-admission-phase1`
- 快照日期：`2026-07-21`
- Freeze 來源 commit：`71ce496baa3c1076679f244c82700c3bf65d1297`
- Production Admission 實作 commit：`167f23fc5297ca818a64e048f6f2fcb09a7a4fa9`

## 目前階段

- Production Admission Phase 1：`COMPLETE`
- Production Admission Phase 2：`WAITING_FOR_OPERATOR_EVIDENCE`
- Runtime 邊界：僅限 dry-run；未授權任何具有真實外部副作用的 adapter。

## 已完成元件

- Production admission package schema（正式環境准入套件結構描述）。
- Fail-closed verifier（失敗時關閉的驗證器），可檢查精確 release、environment、
  role、signature、freshness 與 evidence binding。
- 直接涵蓋 PASS、FAIL 與失敗路徑的測試。
- Repository-controlled security integration（由 repository 控制的安全整合）。
- 英文權威文件與繁體中文 companion。
- 人工 operator handoff（操作員交接）文件。
- BLOCKED／FAIL recovery（復原）文件。

## 驗證結果

- 完整 Python/API 回歸測試：`571 passed, 76 warnings`。
- Production admission 專項測試：`16 passed`。
- Canonical parsed schema 驗證：`196 passed, 0 failed`。
- Frontend：程式碼檢查通過、`36` 項測試通過、production build 與
  bundle-size guard（套件大小閘門）通過。
- Security review：repository-controlled scope 為 `GO`，該審查閘門沒有
  Critical 或 Warning finding。

上述結果只驗證 repository 行為，不是 production evidence，也不授予正式環境准入。

## 已知限制

- 本套件未執行或核准 production deployment（正式環境部署）。
- Repository 內沒有 operator signature、真實 external-control bundle、trusted
  operator keyring、deployment image digest、正式環境 model artifact digest 或
  physical observation。
- AI Agent 不得建立 `production-admission-package.json`。
- Repository-controlled security `GO` 不能取代 production approval。
- 在授權操作員提供新鮮、綁定精確 release 的證據，且 verifier 回傳
  `VERIFIED` 前，Production 一律維持 fail-closed。

## 建議的下一步

1. 由授權人工操作員在 repository 外的受保護儲存區準備
   [PHASE2_OPERATOR_CHECKLIST.zh-tw.md](PHASE2_OPERATOR_CHECKLIST.zh-tw.md)
   所列項目。
2. 操作員必須將證據綁定至精確且乾淨的 release commit、tree、environment、
   deployed images、核准的 model artifact、policy、Compose file 與 trusted keyring。
3. 由授權的 `production-admission-approver` 審閱並簽署套件。
4. 使用既有 verifier 驗證受保護套件；任何缺漏、過期、不相符、遭竄改或未授權
   的證據都必須維持 blocked。
