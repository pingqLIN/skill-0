# Runtime Asset P0.1 操作就緒證據

- 狀態：**Derived Index 已可操作；刻意不宣稱 Governance acceptance**
- 日期：`2026-07-18`
- 計畫：[`../planning/runtime-asset-p0-1-operational-readiness-plan.md`](../planning/runtime-asset-p0-1-operational-readiness-plan.md)
- 英文權威版本：[`runtime-asset-p0-1-operational-readiness.md`](runtime-asset-p0-1-operational-readiness.md)

## 結果

Checked-in corpus 現在可解析成 196 個唯一 canonical Asset IDs。三份 Java
upgrade payload 保留位元相同的 legacy Skill payload 與一個 ambiguous legacy
alias；Runtime 與 Governance 則接收唯一 canonical Asset IDs。真正的 canonical、
derived 或 alias namespace collision 仍一律 fail closed。

Audited maintenance CLI 會執行既有 Index schema preflight、read-only checksum
migration preview、不覆寫的 SQLite backup、核准的 Index migration、兩次
incremental index 與 doctor evidence。Strict mode 會在 authority／canonical／
checksum／unknown failure 存在時於 indexing 前阻擋，且 post-index doctor 必須
healthy 才成功。

## Local Index 演練

原 root `skills.db` 只有 sample table，並不是 Index。替換前已保留兩種可復原
形式：原檔位於 `.del/skills.sample.20260717T170129Z.db`；SQLite backup 位於
`backups/skills.sample-pre-p0-1.20260717T170129Z.db`。

Disposable valid Index 通過 preview、backup、migration、index 與 restore
演練後，相同 guard 流程才建立 local derived `skills.db`。Pre-migration backup
為 `backups/skills.pre-asset-migration.20260717T170129Z.db`，49,152 bytes，
SHA-256 `d590d3b0cc86ca978f8e57439d87334e005280003e16bcd9db6c668502789077`；
還原到獨立 DB 後得到相同 hash 與有效的 pending-migration preview。

## Index 證據

- `001_asset_index_state` checksum migration 已套用；integrity 為 `ok`。
- 第一次 incremental run：196 changed。
- 第二次：0 changed、196 unchanged、0 removed。
- Index rows 196；pending、stale、duplicate canonical 與 model drift 都是 0。
- 一個 ambiguous legacy alias 刻意保留，legacy detail lookup 仍 fail closed。
- `document processing` search smoke 回傳 PDF／Docx 相關結果。
- Search projection 與完整 local model identity 記錄在
  `audit/p0-1/operator-index-search-20260717T170129Z.json`。

Ignored local evidence 位於 `audit/p0-1/operator-*-20260717T170129Z.json` 與
`.artifacts/p0-1/20260717T170129Z/`。

## Governance 邊界

Public checkout 沒有 `governance/db/governance.db`。P0.1 沒有複製無關的 root
sample DB、沒有合成 binding，也沒有批准任何 revision。因此 local index 只以
明確的 `--allow-nonhealthy-evidence` 執行，並正確記錄 `accepted=false`、
`rehearsal_only=true`、doctor `authority-missing`／exit 2，唯一原因是
`governance_database_missing`。

這是真實 authority 邊界，不是 Index failure。只有真實 reviewed Governance
revisions 存在後，才能通過 strict operator acceptance。

## Rollback

先停止 Index writers、驗證選定 backup，再還原 verified pre-migration backup；
不得原地 drop migration tables。Governance 與 Runtime store 均未修改。
