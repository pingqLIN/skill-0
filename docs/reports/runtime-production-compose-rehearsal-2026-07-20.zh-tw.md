# Runtime Production Compose 演練證據

- 日期：`2026-07-20`
- 狀態：**TECHNICAL_REHEARSAL_PASS / PRODUCTION_NO_GO**
- 權威版本：英文版；本文件為繁體中文閱讀參考
- 修正 commit：`0b3acbb`

## 範圍

本報告記錄 production Compose contract 的本機隔離執行，驗證 repository-controlled startup、storage、health、governed dry-run、backup/restore、restart 與 cleanup 行為。這不是 deployment、public exposure 核准、vulnerability exception 或 operator production decision。

演練使用唯一 Compose project、未占用的 loopback ports `28080`／`23080`、synthetic rehearsal-only credentials/origins 與 disposable named volumes；沒有讀取真實 production environment file，也沒有建立 public route。

## 發現的 image boundary 缺陷

第一次 live run 在建立 disposable Governance volume 的 seed 時失敗，原因是 Dashboard image 含有 repository-local `governance/db/governance.db`。Docker volume copy-up 把該 operator state 匯入新的 named volume，造成 rehearsal seed 與既有 canonical identity 衝突。

Commit `0b3acbb` 已從 `Dockerfile.dashboard` 移除 `COPY governance/`、從 Docker build context 排除 `governance/db/`、加入 regression guard，並記錄 empty-volume provisioning boundary。沒有變更任何 database content 或 schema。

## 已驗證的 clean rerun

Clean rerun 使用：

```powershell
pwsh -NoProfile -File scripts\rehearse_prod_compose.ps1 `
  -ProjectName skill0-rehearsal-20260720-1913 `
  -ApiPort 28080 `
  -WebPort 23080
```

| Gate | 證據 |
|---|---|
| Compose build/startup | API、Dashboard、Web images 完成 build；services 達到預期 health state |
| Production doctor | `healthy`；三個 SQLite stores 皆通過 `quick_check`；Runtime 使用 WAL；parsed corpus 為 `196` |
| Governed Runtime | Synthetic current revision 完成 approve；dry-run status 為 `succeeded` |
| Evidence projection | 兩次讀取 byte-identical；public Evidence/events 沒有 rehearsal password、JWT secret、Runtime binding key 或 bearer token |
| Persistence | API restart 後 Runtime sentinel 仍存在 |
| Backup/restore | Index、Governance、Runtime stores 的 online backup/restore 皆為 `quick_check=ok`；restored Runtime sentinel 相符 |
| Cleanup | `down --volumes --remove-orphans` 後，project containers、volumes、networks 數量皆為 `0` |

修正後的 repository verification：

- focused production contract tests：`7 passed`；
- full Python/API regression：`508 passed, 76 warnings`；
- schema validation：`196 passed, 0 failed`；
- changed-scope audit：沒有 forbidden path、added DDL 或 secret-like finding。

## 剩餘 production boundary

本演練已滿足 production policy 中 repository-controlled technical rehearsal 的部分，但 production 仍為 `NO_GO`：

- 目前 dependency report 記錄 API base image 有一個 Critical 與兩個 High findings，且 Bookworm 沒有 fixed version；
- 所有 production image stages 完成 digest-pin 後，offline `local://` scans 驗證 Dashboard 為 1 Critical／2 High、Web 為 1 Critical／9 High；
- external TLS、network ACL、secret-manager、host-volume、encrypted-backup 與 monitoring evidence 不在本演練範圍；
- 未授權 public push、release、deploy、production secret 使用或 risk exception。

明確排除項目不變：不做 FTS5 production integration、Dashboard redesign、new Asset Type 或 physical database migration。
