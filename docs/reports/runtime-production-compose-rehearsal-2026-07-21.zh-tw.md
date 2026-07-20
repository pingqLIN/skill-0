# Runtime Production Compose 演練證據 — 2026-07-21

- 日期：`2026-07-21`
- 狀態：**TECHNICAL_REHEARSAL_PASS / PRODUCTION_NO_GO**
- 權威版本：英文版；本文件為繁體中文閱讀參考
- Candidate branch：`codex/skill0-runtime-asset-rc`

## 範圍

本報告記錄加入 approved embedding-model artifact digest gate 後，production
Compose contract 的本機隔離重跑結果。驗證範圍包含 repository-controlled
model provisioning、startup、storage、health、governed dry-run、backup/restore、
restart 與 cleanup。這不是 deployment、public exposure 核准、vulnerability
exception 或 operator production decision。

本次使用 loopback ports `28082`／`23082`、synthetic rehearsal-only
credentials/origins、唯一 Compose project 與 disposable named volumes；沒有讀取
真實 production environment file，也沒有建立 public route。

## Model artifact gate

Application code 現在要求 absolute、symlink-free 的 local model directory，以及
`SKILL0_EMBEDDING_MODEL_ARTIFACT_DIGEST`。Digest 是具版本、length-framed 的
SHA-256 manifest，涵蓋每個 regular file 的 path、size 與 content digest。
Production startup、model loading、index identity 與 production doctor 在
artifact 缺少、格式錯誤、不可讀或不一致時都會 fail closed。Remote model
fallback 已停用，正常 API service 以 read-only 方式 mount model volume。Configured
directory 與 artifact tree 內都禁止 symlink；tree 外的 ancestors 屬於
operator-managed host／volume boundary。

Live Compose rehearsal 刻意使用小型 synthetic artifact。它證明 digest
calculation、startup enforcement、read-only mount、doctor verification 與 restart
stability；**不**代表這些 synthetic bytes 是可用的 SentenceTransformer model，
也不宣稱執行過 real model inference。Focused tests 另外驗證 `SkillEmbedder` 會在
import／load model 前先檢查 digest，並保留非 production remote fallback。

第一次重跑因 non-root API image 無法寫入新 model volume 而安全失敗。演練已修正
為只有一次性的 operator provisioning container 使用 root；正常 API container
仍是 non-root，且使用 read-only mount。失敗 project 的 disposable volume 已在
verified rerun 前清除。

## 已驗證的 rerun

通過的 rerun 使用：

```powershell
pwsh -NoProfile -File scripts\rehearse_prod_compose.ps1 `
  -ProjectName skill0modelgate0721c `
  -ApiPort 28082 `
  -WebPort 23082
```

| Gate | 證據 |
|---|---|
| Compose build/startup | API、Dashboard、Web images 完成 build；services 達到預期 health state |
| Model artifact | Startup 前先計算 disposable artifact digest；production doctor 在 restart 前後皆回報 `embedding_model_artifact.verified=true` |
| Production doctor | `healthy`；三個 SQLite stores 皆通過 `quick_check`；Runtime 使用 WAL；parsed corpus 為 `196` |
| Governed Runtime | Synthetic current revision 完成 approve；dry-run status 為 `succeeded` |
| Evidence projection | 產生 deterministic public Evidence，且未暴露 rehearsal credentials |
| Persistence | API restart 後 Runtime sentinel 仍存在 |
| Backup/restore | Index、Governance、Runtime stores 的 online backup/restore 皆為 `quick_check=ok`；restored Runtime sentinel 相符 |
| Cleanup | 執行後已移除 project containers、volumes 與 network |

Repository verification 結果：

- model／production focused regression：`53 passed`；
- full Python/API regression：`518 passed, 76 warnings`；
- schema validation：`196 passed, 0 failed`；
- Python compile 與 `git diff --check`：通過。

## 最新 image scan

前一次通過的 `skill0modelgate0721b` rerun 執行 Docker Scout `local://` SARIF
scans：

| Image | Critical | High | SARIF SHA-256 |
|---|---:|---:|---|
| API | 1 | 2 | `feeea495903b630cc2e9029927bd80a531cbb91367b60891c4fee85548c9cb84` |
| Dashboard | 1 | 2 | `feeea495903b630cc2e9029927bd80a531cbb91367b60891c4fee85548c9cb84` |
| Web | 1 | 9 | `81d072bb8b6fe1f2de7831f4a5a24e9aa59435d63fdfc7d5448a8e418ae5fb3b` |

外層並行掃描命令達到五分鐘 timeout，但命令結束後，三份 SARIF files 均已完整
寫入、是有效 JSON，並完成獨立解析；數量與前次掃描一致。通過 integrity check
的 copies 保存在 ignored local evidence directory
`.artifacts/security-review/20260721T023719Z/`，不是 release artifacts。
Final `skill0modelgate0721c` rerun 只移除兩個 image-level offline environment
defaults；Docker inspection 已確認兩個 API candidates 的 20 層 RootFS lists 完全
相同。Production Compose 仍設定兩個 offline flags，retained scan 後沒有變更
package filesystem layer。

## 剩餘 production boundary

Repository-controlled model artifact 缺口已關閉，但 production 仍為 `NO_GO`：

- 演練當下三個 images 都未通過 Critical／High 必須為零的 gate；
- external TLS、network ACL、secret-manager、host-volume、encrypted-backup 與
  monitoring evidence 仍在 repository 範圍外；
- 本次沒有執行或授權 deploy、public exposure、production secret 使用或
  vulnerability exception。

明確排除項目不變：不做 FTS5 production integration、Dashboard redesign、new
Asset Type、physical database migration 或 real adapter。

## 演練後 Web image 修補

後續在 `2026-07-21` 將 Web-only runtime base 更新為 official digest-pinned
`nginxinc/nginx-unprivileged:1.31.3-alpine3.24-slim` image。重建後的 final Web
image 以 non-root user `101` 通過 isolated HTTP 200 smoke。Docker Scout 回報
`0 Critical／0 High／0 Medium／0 Low`；零 result SARIF 的 SHA-256 為
`69933e606e8fc010c7d1df52993f413523163ac7ca1c3247fc26bdbc6c946878`。

這只關閉 Web image CVE blocker；上表仍保留 Compose rehearsal 當時的歷史
scan evidence。Production 維持 `NO_GO`，因 API 與 Dashboard 各自仍有
1 Critical／2 High 的 Bookworm Perl 未修補 findings，且上述 external controls
仍需 operator evidence。
