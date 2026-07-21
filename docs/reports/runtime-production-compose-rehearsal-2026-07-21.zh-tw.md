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

這在當時只關閉 Web image CVE blocker。上表保留為歷史 scan evidence；目前
Item 3 image 與 rehearsal gate 由以下 final rerun 取代。

## Final Item 3 image remediation 與 rerun

API 從 Python Bookworm 改為 digest-pinned、same-release Ubuntu 24.04
multi-stage image。Final runtime 使用 distro Python 3.12 interpreter、複製
builder 產生的 virtual environment、以 UID 65532 執行，並保留 ephemeral
BuildKit CA secret boundary。PyTorch CPU 沒有 musllinux wheel，因此 API 未改用
Alpine。Dashboard image 則獨立移到 digest-pinned Python Alpine 3.24，並限制
`pip>=26.1.2,<27`。

Final local image evidence：

| Image | Local image ID | Critical | High | Medium | Low |
|---|---|---:|---:|---:|---:|
| API | `sha256:dc7ac417bcfb3ebf49eefaffb3b1834bfd34a5b4e3e0984b4f06d5af4111c088` | 0 | 0 | 15 | 5 |
| Dashboard | `sha256:be736191417bcbed79406dde15aa70b585aff2d17daf82d0473232bcaa666bd3` | 0 | 0 | 0 | 0 |
| Web | `sha256:f604964103605aae8e96fafd642a0bc3a937596638252bd9291aa9f74aec29fc` | 0 | 0 | 0 | 0 |

三個 images 的 zero-result Critical/High SARIF SHA-256 都是
`69933e606e8fc010c7d1df52993f413523163ac7ca1c3247fc26bdbc6c946878`。
API all-severity SARIF SHA-256 是
`bdf53c8f2785d151e3bebcd7c1c95e01e87257e2a3d8d5642cf946f2e3999330`。
API residuals 都是 Ubuntu vendor-classified Medium／Low；報告保留這些
residual risk，不會宣稱不存在。Dashboard／Web 所有 severity 都是零。

Final API 與舊 Bookworm control 解析出相同版本的 NumPy、PyTorch、
SentenceTransformers 與 Transformers。五個固定 queries 加五個 parsed
documents 產生十個 normalized 384-dimensional vectors；每一個 vector 的
SHA-256 都相同。API／Dashboard standalone smoke 都以 non-root user 回傳 HTTP
200，且兩個 images 都通過 `pip check`。

Fresh isolated rehearsal 使用：

```powershell
pwsh -NoProfile -File scripts\rehearse_prod_compose.ps1 `
  -ProjectName skill0-item3-gate-0721b `
  -ApiPort 18184 `
  -WebPort 13184 `
  -BuildCaFile .artifacts\build-ca\gateway-ca.crt
```

結果通過 Compose config/build、service health、0 errors/warnings 的 production
doctor、governed dry run/deterministic Evidence、three-store online
backup/restore、API restart persistence 與 cleanup。Compose-built images 與另行
scan 的 final tags 有相同 RootFS layer lists。Cleanup 後 project-scoped
container、volume、network 數量都是零。Repository gates 也通過 555 個
Python/API tests、36 個 frontend tests、frontend lint/build/bundle checks，以及
196/196 schema validation。

Repository-controlled Critical/High 與 technical-rehearsal gates 已關閉。
Production 維持 `NO_GO`，因尚未提供真實 signed external-control bundle、trusted
operator keyring、attachments 或 physical observations。新 verifier 對 missing、
stale、tampered、revoked、wrong-environment、wrong-release 或 incomplete evidence
一律 fail closed，並將未來 bundle 綁定 exact clean Git commit/tree、policy、
Compose file、deployed image digests、model digest 與 environment。本次沒有
production deploy、public exposure、real credentials 或 vulnerability exception。

Independent read-only review 在兩個初始 Warning 完成修補與重驗後，對
repository-controlled Item 3 回傳 `GO`：keyring 現在由 protected-runner digest
驗證，且該 digest 納入 signed release binding；Git status 也包含 untracked
non-ignored files。Reviewer 將 source-to-image provenance 與 SARIF target binding
保留為 Advisory，因 policy v1.6.0 尚未強制 image signing、provenance
attestation 或 digest-stamped scan envelope。Production 因上述 external-evidence
原因仍維持 `NO_GO`。
