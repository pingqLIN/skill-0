# Runtime Asset P0 驗證與 P1 決策資料包

- 狀態：**P0 implementation 已驗證；未執行 operator migration**
- 日期：`2026-07-17`
- 執行依據：[`../planning/runtime-asset-foundation-next-round-plan.md`](../planning/runtime-asset-foundation-next-round-plan.md)
- 英文權威版：[`runtime-asset-p0-verification-and-p1-decision.md`](runtime-asset-p0-verification-and-p1-decision.md)

## 結果

P0 Runtime Asset Foundation and Storage Boundary 已完成 code、contract、fixture、
API 與 doctor layers。既有 Skill 與 Runtime v4 contracts 仍可使用。沒有任何
實體 DB 被改名、拆分、合併或 migrate；operator `skills.db`、Governance DB 與
Runtime DB 均未變更。

## Commit series

| Batch | Commit | 結果 |
|---|---|---|
| P0-A | `f840a09` | Envelope v1、ADR-0007/0008、failure fixtures、compatibility map |
| P0-B | `e09fc47` | immutable corpus snapshot、Skill adapter、Runtime lookup |
| P0-C | `b9724a3` | SQLite policy、checksum migration、backup/restore fixtures |
| P0-D | `813d097` | bounded async offload、projection、incremental identity |
| P0-E | `b07b194` | read-only Asset API 與 classified drift doctor |

## 整合驗證

- Python compileall、document markers、shared-document contract：通過。
- Parsed schema：`196 passed, 0 failed`。
- 完整 Python regression：`414 passed, 66 warnings`。
- P0-E cut line 前：兩次連續 `403 passed`。
- Frontend lint：通過；frontend tests：`34 passed`。
- Frontend build/bundle guard：通過；最大 JS chunk `336.35 KiB`，低於
  `350 KiB`。
- Diff whitespace check：通過。

兩個 independent read-only completion reviews 在初次 findings 修正並重新審查後
均為 PASS。已關閉項目包括 atomic authenticated reload、production
connection-factory usage、migration checksum doctor visibility、model-weight
identity，以及 shared-operation concurrency。

## Storage、index 與 async evidence

- Fresh/current/legacy fixture DB 可由 ordered migration 收斂。
- Migration checksum 被修改時 fail closed；雙 writer contention 會回
  `sqlite_write_contention`。
- Read-only preview 不建立 table 或 DB artifact；backup 通過
  `integrity_check` 與 restored read。
- Production API Index operations 使用 factory-backed per-unit-of-work
  connections；doctor 會顯示 migration status，checksum drift 以 `unknown`/exit
  `3` fail closed。
- 第二次 unchanged index run 的 embedding 為零；parser drift 只選中一筆；
  representation drift 選中兩筆；source removal 可 prune；injected embedding
  failure 保留既有 projection。
- Local embedding model identity 會涵蓋 weights 在內的全部 model files；remote
  model 必須設定 immutable `SKILL0_EMBEDDING_MODEL_VERSION`。
- Search/list hot paths 不讀 `raw_json`。
- Async capacity 固定為 two workers + four queued calls；event-loop threshold、
  overload 與 cancellation capacity tests 均通過。

## Runtime compatibility 與 doctor

- Runtime create/resume 使用單一 immutable repository，不再逐 request enumerate
  或 parse corpus。
- Snapshot drift 以 `stale_source_snapshot` fail closed。
- Authenticated `POST /api/assets/reload` 會先 off-side 驗證 replacement，再
  atomic swap；stale-to-reloaded recovery fixture 已通過。
- 196 份文件保持 byte-unmodified 且 schema-valid。
- 三份 `claude__skill__java_to_java_upgrade` 保留為明確 ambiguous identity；
  list/revisions 可檢視，single detail 與 Runtime lookup fail closed。
- Legacy numeric `/api/skills/{id}`、pagination、`include_json`、search 與 index
  compatibility tests 維持通過。

目前 doctor 為 `authority-missing`、exit `2`：Registry 196 revisions、Asset index
rows 0、pending 196、duplicate identity 1，且 Governance operator DB 不存在。
這是正確的本機觀察結果，不得用 implicit migration 或 synthetic authority
改成綠燈。

## P1 決策

| Candidate | 決策 | 重新開啟所需 evidence |
|---|---|---|
| 實體 DB 重整 | **NO-GO** | operator copy migration/restore rehearsal、contention、size 與 operating-cost 實測 |
| FTS5/hybrid ranking | **NO-GO** | representative query corpus、ranking metric、fusion 決策與 latency/storage benchmark |
| 第二 Asset Type | **NO-GO** | accepted ground-truth corpus、parser contract、failure taxonomy 與 fidelity 實測 |
| Dashboard Asset 改名 | **NO-GO** | 穩定第二 type 或 operator need、API usage evidence 與 migration/rollback design |

每個 batch 都是獨立 additive commit，可反向 revert。因未執行 operator DDL，
目前不需要 data rollback。未 migrate Index 時 incremental Asset search 維持不可用，
legacy Skill search 仍是 compatibility path。
