# Runtime v4 正式環境維運

> 本文件是 [runtime-production-operations.md](runtime-production-operations.md) 的繁體中文參考版本；英文原文為權威版本。

所有 deployment 也必須符合 [`production-security-policy.md`](production-security-policy.md) 的 mandatory controls 與 external evidence requirements。

## 儲存拓樸

Runtime v4 使用三個彼此獨立的 SQLite store；任何一個缺失，都不能宣告 production-ready。

| Store | 正式環境路徑 | 權責 |
|---|---|---|
| 搜尋索引 | `/app/data/skills.db` | Core API 讀寫 |
| 治理資料 | `/app/governance/db/governance.db` | Dashboard API 讀寫；Core API 唯讀 |
| Runtime ledger | `/app/runtime-data/runtime.db` | Core API 讀寫 |

`docker-compose.prod.yml` 為 Runtime ledger 使用獨立 named volume，並把 governance volume 以唯讀方式掛給 Core API。Core API 會等待 Dashboard API health check，之後才執行 fail-closed startup doctor。

Production image 不得內嵌 `governance/db/` 或 operator `governance.db`。新的 governance volume 在 explicit provisioning/restore 前必須保持空白；Docker volume copy-up 不得匯入 repository-local authority state。

## 正式環境必要設定

- `SKILL0_RUNTIME_BINDING_KEY`：至少 32 字元的獨立 secret，不得等於 `JWT_SECRET_KEY`。
- `SKILL0_RUNTIME_DECISION_ACTORS`：明確列出的 JWT subject，逗號分隔。
- `SKILL0_RUNTIME_HITL_TTL_SECONDS`：300–604800；production 預設 86400。
- `SKILL0_RUNTIME_JOURNAL_MODE=WAL`。
- `SKILL0_RUNTIME_DB_PATH=/app/runtime-data/runtime.db`。
- `SKILL0_GOVERNANCE_DB_PATH=/app/governance/db/governance.db`。
- 正常運作時設定 `SKILL0_RUNTIME_ALLOW_INITIALIZE=false`。
- `SKILL0_EMBEDDING_MODEL`：read-only model volume 內 absolute、symlink-free、由 operator materialize 的 model directory。
- `SKILL0_EMBEDDING_MODEL_ARTIFACT_DIGEST`：已核准的 `sha256:<64 lowercase hex>` 完整 tree digest。Startup、production doctor、model loading 與 index identity 都會驗證；production 不允許 remote fallback，也不忽略 model drift。
- `SKILL0_BIND_ADDRESS` 預設為 `127.0.0.1`。只有在明確完成 network boundary review，且前方有 maintained TLS proxy 或 ingress 時，才可覆寫。
- `SKILL0_EXTERNAL_CONTROL_TRUSTED_KEYRING_SHA256`：approved external-control verifier keyring 的 exact SHA-256，由 protected release runner 或同等的 independently administered configuration 注入；evidence submitter 不得控制此值。

Doctor 只回報設定名稱與結構性 finding，不會輸出 secret 值。

## 首次啟動與升級

1. 先把已核准 model 以 symlink-free 形式 materialize 到 model volume。使用 `vector_db.model_artifact` 的 `compute_model_artifact_digest()` 計算 digest、保存 reviewed value，再以 read-only 方式 mount。正常 API service 不得 provision 或更新 model bytes。
2. 接受流量前先還原或提供 `skills.db` 與 `governance.db`。乾淨的公開 checkout 本來就沒有正式環境身份與核准資料。
3. 先啟動 Dashboard API，確認 governance volume 存在且 schema 為目前版本。
4. 只有第一次刻意 provisioning boot 才設定 `SKILL0_RUNTIME_ALLOW_INITIALIZE=true`。若此 flag 為 false 但 Runtime ledger 缺失，startup 必須失敗，不能靜默建立空白 history。
5. 再啟動 Core API。Entrypoint 會初始化或遷移 `runtime.db`，接著執行：

   ```bash
   python /app/scripts/runtime_doctor.py --production --json
   ```

6. 把 `SKILL0_RUNTIME_ALLOW_INITIALIZE` 改回 `false`，重啟 Core API 並再次驗證 doctor。
7. 兩個 API 都 healthy 後才啟動 web。

沒有 `expires_at` 的舊 HITL row 一律視為 expired；沒有 `governance_revision_id` 的舊 execution basis 不可 resume。不要改寫舊 attestation，應針對目前已核准 canonical revision 建立新 run。

## HITL deadline

- 尚未決策的 item，以及已核准但尚未消耗的 action approval，會在 `expires_at` 到期。
- Expired item 不能決策、也不能 claim resume，Dashboard 會在 `expired` queue 顯示。
- 拒絕、確認復原或消耗核准都不會自動發生。
- 修改 TTL 只影響新建 item；已保存的 deadline 不可變。

## 備份與 release gate

服務在線時，以同一批次備份三個 store：

```bash
SKILL0_DB_PATH=/path/to/skills.db \
SKILL0_GOVERNANCE_DB_PATH=/path/to/governance.db \
SKILL0_RUNTIME_DB_PATH=/path/to/runtime.db \
BACKUP_DIR=/secure/skill0-backups \
./scripts/backup_db.sh
```

接著驗證 WAL mode、備份新鮮度、schema、parsed artifact 與安全設定：

```bash
BACKUP_DIR=/secure/skill0-backups ./scripts/check_db_health.sh
python scripts/runtime_doctor.py \
  --production \
  --require-backups \
  --backup-dir /secure/skill0-backups \
  --json
```

若初始化仍開啟，或任何 store、必要欄位、近期備份、parsed corpus、actor allowlist、binding key、TTL 或 production Runtime WAL contract 缺失，release gate 都必須失敗。

## External-control evidence gate

Application doctor 無法觀察 deployment edge、host、backup key separation、
secret manager 或 centralized logging service。Promotion 前，authorized
operator 必須提供符合
[`production-external-control-evidence.schema.json`](../schema/production-external-control-evidence.schema.json)
的 external evidence bundle，並搭配由外部獨立管理、符合
[`production-external-control-keyring.schema.json`](../schema/production-external-control-keyring.schema.json)
的 verifier keyring。不得把真實 bundle、keyring、attachment、credential、
topology export 或 private operator identifier commit 到 repository。

Release runner 必須從 evidence submitter 無法修改的 protected configuration
注入 `SKILL0_EXTERNAL_CONTROL_TRUSTED_KEYRING_SHA256`。Verifier 會 hash supplied
keyring、與此 independent trust anchor 比對，並將 trusted keyring digest 納入
signed release binding；刻意不提供 CLI trust-anchor override。

Signed bundle 必須完整包含 machine-readable production policy 的所有
`required_external_controls`。Bundle 會綁定 clean Git commit/tree、production
trusted keyring digest、Compose/policy file digest、三個 deployed image digest、
approved model artifact digest、named environment、operator identity/role，
以及以 digest 定址的 attachments。Git gate 會拒絕 tracked 與 untracked
non-ignored worktree drift。請使用 dedicated release checkout，並確認 ignored
build inputs 不存在或已被 `.dockerignore` 排除。預設 observation 不得超過 24
小時，signed validity window 不得超過 168 小時。Ed25519 key 必須有唯一識別、
獲准用於該 actor role/environment，且未被 revoked。

請在準備 promotion 的 exact clean checkout 執行 fail-closed verifier：

```powershell
python tools/verify_production_external_controls.py `
  --bundle C:\secure-evidence\production-primary\bundle.json `
  --keyring C:\secure-keyring\skill0-production-keyring.json `
  --evidence-root C:\secure-evidence\production-primary `
  --environment production-primary `
  --image-digest api=sha256:<64-lowercase-hex> `
  --image-digest dashboard=sha256:<64-lowercase-hex> `
  --image-digest web=sha256:<64-lowercase-hex> `
  --model-artifact-digest sha256:<64-lowercase-hex>
```

Protected release runner 必須先提供 trust-anchor environment variable。Exit code
`0` 只證明 bundle integrity、freshness、authorization、exact release
scope 與 attachment digest；不表示 repository 已自行觀察實體 controls。任何
missing、malformed、stale、expired、tampered、revoked、environment/release
不符或 evidence 不完整的情況，都會回傳 `UNKNOWN`、exit `2` 並 block
release。Synthetic test evidence 只證明 verifier 行為，永遠不能當成 production
evidence。

## 還原與重啟演練

只可使用隔離的 project name。若該 project name 已擁有 container、volume 或 network，Helper 會 fail closed；HTTP ports 只綁定 loopback。之後才會建立一次性 volume、初始化演練用 governance store、驗證三個 store、執行線上 SQLite backup/restore 驗證、重啟 Core API，並再次執行 doctor：

```powershell
pwsh -File scripts/rehearse_prod_compose.ps1
```

真實還原流程：

1. 停止三個 store 的 writer。
2. 保留損壞檔案供鑑識，不要覆蓋唯一副本。
3. 還原同一批次的 `skills_*`、`governance_*` 與 `runtime_*` 備份。
4. 依序啟動 Dashboard API、Core API、web。
5. 以 `--require-backups` 執行 production doctor，並驗證 API/web health。
6. 建立新的 governed dry run；除非完整 execution 與 governance basis 仍存在，否則不要 resume 還原前的 approval。

## Binding key 輪替

Runtime binding key 刻意不提供靜默 fallback key ring。

1. 暫停建立新 Runtime run 與 HITL decision。
2. 消化已核准 item，或等待其不可變 deadline 到期。
3. 備份三個 store 並通過 release gate。
4. 在 secret manager 輪替 `SKILL0_RUNTIME_BINDING_KEY`，然後重啟 Core API。
5. 再跑 production doctor 與新的 governed dry run。

舊 key 建立的 approval 將不可 resume。這是 fail-closed 行為，不是資料遺失；decision 與 event evidence 仍保留在 ledger。

## Rollback

Rollback 必須同時還原相符的三庫備份，以及前一版 application image/configuration。不可只降級 Runtime schema、卻保留新版 event data。若舊 image 無法理解目前 governance revision 或 HITL deadline，應停用 Runtime 並保留 store，等待向前修復。
