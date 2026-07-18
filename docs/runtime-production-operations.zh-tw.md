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

## 正式環境必要設定

- `SKILL0_RUNTIME_BINDING_KEY`：至少 32 字元的獨立 secret，不得等於 `JWT_SECRET_KEY`。
- `SKILL0_RUNTIME_DECISION_ACTORS`：明確列出的 JWT subject，逗號分隔。
- `SKILL0_RUNTIME_HITL_TTL_SECONDS`：300–604800；production 預設 86400。
- `SKILL0_RUNTIME_JOURNAL_MODE=WAL`。
- `SKILL0_RUNTIME_DB_PATH=/app/runtime-data/runtime.db`。
- `SKILL0_GOVERNANCE_DB_PATH=/app/governance/db/governance.db`。
- 正常運作時設定 `SKILL0_RUNTIME_ALLOW_INITIALIZE=false`。

Doctor 只回報設定名稱與結構性 finding，不會輸出 secret 值。

## 首次啟動與升級

1. 接受流量前先還原或提供 `skills.db` 與 `governance.db`。乾淨的公開 checkout 本來就沒有正式環境身份與核准資料。
2. 先啟動 Dashboard API，確認 governance volume 存在且 schema 為目前版本。
3. 只有第一次刻意 provisioning boot 才設定 `SKILL0_RUNTIME_ALLOW_INITIALIZE=true`。若此 flag 為 false 但 Runtime ledger 缺失，startup 必須失敗，不能靜默建立空白 history。
4. 再啟動 Core API。Entrypoint 會初始化或遷移 `runtime.db`，接著執行：

   ```bash
   python /app/scripts/runtime_doctor.py --production --json
   ```

5. 把 `SKILL0_RUNTIME_ALLOW_INITIALIZE` 改回 `false`，重啟 Core API 並再次驗證 doctor。
6. 兩個 API 都 healthy 後才啟動 web。

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

## 還原與重啟演練

只可使用隔離的 project name。Helper 會建立一次性 volume、初始化演練用 governance store、驗證三個 store、執行線上 SQLite backup/restore 驗證、重啟 Core API，並再次執行 doctor：

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
