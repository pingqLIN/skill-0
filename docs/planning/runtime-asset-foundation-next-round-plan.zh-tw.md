# Runtime Asset Foundation——下一輪開發計畫

- 狀態：**P0 implementation 已完成；Runtime v4 release authority 仍維持凍結**
- 日期：`2026-07-17`
- 目標基線：P0 plan commit `24c6f0f` 的 `main`
- 規劃里程碑：`P0 Runtime Asset Foundation and Storage Boundary`
- 英文權威版：[`runtime-asset-foundation-next-round-plan.md`](runtime-asset-foundation-next-round-plan.md)

## 1. 決策

下一輪採用「additive、compatibility-first」方式建立 Runtime Asset 基礎，不立即改名實體資料庫、不重寫 Parser、不開放真實 adapter，也不重新設計 Dashboard。

目標架構：

```text
Source
  -> Parser Adapter
  -> Runtime Asset Envelope
  -> Revision-aware Registry Boundary
  -> Derived Search Projection
  -> Governed Runtime Admission
  -> Append-only Runtime Ledger
```

P0 期間 `Skill` 仍是唯一正式支援的 `asset_type`；既有 Skill contract 透過明確相容 adapter 繼續運作。本計畫只提出 V4 closeout 後的新里程碑，不會暗中改寫 [`../README.md`](../README.md) 與 [`../closeout/FINAL_REPORT.md`](../closeout/FINAL_REPORT.md) 所凍結的 Runtime v4 release boundary。

## 2. 輸入與證據狀態

### 使用者提供的提案資料

- `skill-0-runtime-asset-item-replacement-checklist.md`
- `skill-0-runtime-asset-integrated-database-recommendations.md`

兩份文件是設計輸入，不是 repo authority；本計畫只採納與目前程式碼及 closeout 文件核對後仍成立的項目。

### VERIFIED：目前 repo 已確認事實

1. `api/routers/runs_v4.py` 的 Runtime create/resume 仍會掃描 `parsed/*.json` 找 canonical Skill。
2. `api/main.py` 的 search endpoint 雖為 `async`，仍直接執行同步 model 初始化、embedding、SQLite 與 vector search。
3. 管理用 index endpoint 會先清空 store，再做整個目錄的全量 re-index；目前沒有 revision/content/model identity gate。
4. `vector_db/vector_store.py` 仍是 Skill-only schema，search/list SQL 會讀取 `raw_json`，只是 HTTP response 後續才將它投影掉。
5. Governance 以 inline DDL 與 `_ensure_column` 演進；Runtime schema 同時存在於 SQL migration 與 `RuntimeLedger._migrate()`。
6. Runtime admission 的權威是 current governance revision 的狀態與 artifact digest，不是 mutable Skill status；此邊界不可破壞。
7. Runtime v4 是 dry-run-only、single-host pilot；真實 adapter loader 與非 dry-run API 仍有獨立 gate。
8. Windows 收斂後基線已通過 374 個 Python tests、34 個 frontend tests、lint 與 `build:ci`；digest-bound certification artifact 已固定為 LF。

基線 `7257ea1` 的可重現證據錨點：

- [`../closeout/VERIFICATION_MATRIX.md`](../closeout/VERIFICATION_MATRIX.md) 保存 closeout command matrix。
- `api/routers/runs_v4.py` 是 request-time canonical JSON scan 的現行位置。
- `api/main.py`、`vector_db/search.py`、`vector_db/vector_store.py` 是同步 search、full index、payload selection 的現行位置。
- `tools/governance_db.py`、`runtime/ledger.py`、`migrations/001_runtime_ledger.sql` 是目前 schema evolution paths。
- 本計畫撰寫前重新執行 Windows 全套 Python tests（`374 passed`）、frontend lint、frontend tests（`34 passed`）與 `build:ci`；這些結果支援本計畫，但不取代 immutable closeout evidence。

### INFERRED：待實作驗證的設計判斷

1. Runtime Asset envelope 可在不改變 ARD 語義下，泛化 identity 與 revision metadata。
2. Repository interface 可先包住既有 Skill storage，再逐步分離 Registry 與 Index。
3. 一次性 legacy artifact catalog 可先移除 request-time directory scan，不必立刻搬資料庫。
4. 以 revision、content、representation 與 model version 建立 index identity，可支援安全的 incremental indexing。

以上是 architecture hypotheses，在完成實作與測試前不得標記為 VERIFIED。

### UNKNOWN：本輪刻意延後

- 最終實體 topology 應為 `registry.db + index.db + runtime.db`，或 `assets.db + runtime.db`。
- FTS5 對實際 workload 的收益，以及適合的 score fusion。
- Registry/Index 最合適的 PRAGMA 與 durability policy。
- 各 asset type 的 parser accuracy；目前沒有已核准 ground-truth benchmark。
- Workflow 是否應成為第二種 asset type。
- 真實 operator database 的 migration 成本與 rollback 行為。

## 3. P0 目標

1. 以 additive contract 確認 `Runtime Asset`、`asset_id`、`asset_type`、`revision_id`。
2. 建立 Runtime Asset Envelope v1、Skill 相容映射與失敗 fixtures。
3. 用 `SkillParserAdapter` 包裝既有 Parser，不改寫 extraction 行為。
4. 建立小型 SQLite repository、connection、migration 邊界，不做多引擎 abstraction。
5. 移除 Runtime request path 重複掃描 `parsed/*.json`。
6. 以 bounded execution 將同步 search/model 工作移出 API event loop。
7. 讓 search projection 明確化，hot path 不再選取 `raw_json`。
8. 建立可跳過未變更 embedding 的 index identity。
9. 延伸既有 doctor/reporting family，讓 Registry/Index drift 可觀察。
10. 保留全部 Runtime v4 governance、Evidence、HITL、recovery 與 dry-run invariant。

## 4. 非目標

P0 不會：

- 改名或合併 `skills.db`、`governance.db`、`runtime.db`；
- 直接 migration 到 `runtime_assets`／`asset_revisions`；
- 移動或改名 `parsed/`；
- 移除或 deprecate `/api/skills` 或既有 search route；
- 改名 Dashboard component 或重新設計 review UX；
- 在 benchmark 與 scoring decision 前，把 FTS5 ranking 加入 production path；
- 新增 Workflow、Prompt、Agent、Tool、MCP、API、Model、Dataset、Policy parser；
- 修改 ARD ID，或把 Evidence 當成第四種 ARD peer；
- 開放 real adapter 或 `dry_run=false`；
- 導入 PostgreSQL、D1、LMDB、DuckDB、Graph DB 或通用 storage-engine plugin；
- 擴張到 multi-instance、HA、multi-tenant 或 Edge deployment。

## 5. 不可退讓的架構 invariant

1. **ARD 仍是 decomposition ontology。** Runtime Asset 是 catalog/revision envelope，不取代 Action、Rule、Directive。
2. **Governance 仍由 revision 掌權。** Runtime 必須繼續驗證 exact canonical artifact digest 與 approved current revision。
3. **Search Index 是 derived projection。** 它必須可重建，且不能授權執行。
4. **Runtime ledger 繼續分離且 append-only。** Asset migration 不可重寫 Runtime history。
5. **Legacy compatibility 必須明示。** Skill API/schema 透過 adapter；historical migration、event、fixture、audit value 不做全域改名。
6. **新的通用程式碼使用 Asset 命名。** Skill 名稱只保留在 Skill adapter 與 compatibility surface。
7. **失敗必須 fail closed 且可觀察。** Registry/Index identity 過期、canonical identity 模糊、migration checksum drift 或 governance binding 缺失都要分類回報。

## 6. 實作前必須確認的決策

P0-A 文件必須先完成並核准；在此之前，後續批次不得進行任何 storage mutation：

1. **ADR-0007 — Runtime Asset terminology and compatibility**
   - identity 規則；
   - Skill-to-Asset mapping；
   - legacy API/event name 保留原則；
   - 英文文件與 schema 的 authority。
2. **ADR-0008 — Registry, Index, and Runtime storage boundary**
   - 邏輯 authority；
   - derived projection 語義；
   - transaction/outbox 方向；
   - 明確延後實體 DB topology。
3. **Compatibility map**
   - 將每個 `skill_*` 分成 domain-generic、Skill adapter-specific、legacy compatibility、historical/migration、fixture 或 documentation-only；
   - 禁止全域 search-and-replace。

這些 ADR 不授權實體 table rename 或資料搬移。

## 7. 執行批次

### P0-A — Contract、失敗案例與 compatibility map

交付：

- ADR-0007、ADR-0008 及各自 `.zh-tw.md` companion；
- `schema/runtime-asset-envelope.schema.json`；
- Skill-backed valid fixture；
- 缺少 revision identity、unsupported type、digest mismatch、provenance malformed 等 invalid fixtures；
- machine-readable legacy compatibility map；
- schema/document contract tests。

Envelope 最少欄位：

```text
schema_version, asset_id, revision_id, asset_type, name, summary,
payload, content_hash, source_digest, parser_id, parser_version,
provenance, lifecycle
```

驗收：既有 Skill schema 與 Runtime contract 行為不變；所有 invalid fixture 以預期原因失敗；canonical Skill 與 Asset envelope 可 deterministic mapping；新 schema 明載 migration/compatibility statement，滿足 backlog D-07 reopen gate。

Rollback：移除 additive schema、fixture、ADR；沒有資料 migration。

### P0-B — Parser adapter 與 repository boundary

交付：

- 小型 `asset_registry` package，包含 domain model 與 repository protocol；
- 包裝既有 output、但不改 extraction logic 的 `SkillParserAdapter`；
- 每個 corpus snapshot 只建立一次 immutable identity map 的 `LegacySkillAssetRepository`；
- duplicate ID、malformed document、digest drift 診斷；
- Runtime canonical lookup dependency injection。

轉換：

```text
load_canonical_skill() directory scan
  -> AssetRepository.get_revision(asset_id, revision_id?)
  -> P0 期間由 legacy Skill adapter 提供
```

Snapshot lifecycle：

- `snapshot_id` 是 sorted relative paths、各 canonical file digest 與 parser identity 的 SHA-256；
- 在旁建立並驗證 replacement map，拒絕 duplicate/malformed documents 後，才 atomically swap process-local reference；
- 只在 process startup 或 authenticated explicit reload/index action 重建；request 中不得靜默接納 file change；
- doctor 比對 live corpus 與 active map，不一致時回報 `stale_source_snapshot`，直到成功 rebuild；
- P0 每個 worker 各自持有一份 immutable snapshot；cross-worker coordination 延後到 multi-worker 獲准後。

驗收：repository 初始化後，Runtime create/resume request 不再 enumerate directory；duplicate identity 仍回 conflict；governance digest 保持 byte-for-byte；196 份 parsed documents 不改寫、schema-valid，且既有 normalized ARD payload hashes 不變。

Rollback：以單一 dependency binding 切回現有 loader；`parsed/` 不移動。

### P0-C — SQLite connection 與 migration foundation

交付：

- 具名 Registry、Index、Runtime policy 的 SQLite connection factory；
- 新 Registry/Index code 採每 unit-of-work connection；
- 明確 `foreign_keys`、`busy_timeout`、transaction mode、durability 設定；
- 帶 checksum 的 migration runner 與 `schema_migrations` contract；
- read-only migration status/doctor；
- 既有 inline schema 的 baseline adapter。

P0 唯一允許的 DDL：

| Store | 允許的 additive DDL | 觸發條件 |
|---|---|---|
| `skills.db` | 只允許 `schema_migrations`、`asset_index_state` | authenticated index maintenance，且已完成 migration preview 與 backup |
| `governance.db` | operator DB 不變；只在 fixture copies 驗證 schema equivalence | P1 decision |
| `runtime.db` | 不變；現有 Runtime migration 行為保持 authority | 獨立 Runtime migration project |

本計畫中的 **physical topology/data migration** 指 DB filename 改名、store merge/split、跨 store 複製 authority rows 或重寫 Runtime history；P0 禁止。**Additive schema migration** 只指上表兩個 Index tables；它可在明確 gate 後執行，但不代表 topology decision。

限制：不更動 Runtime durability default；不全系統強制 WAL／NORMAL；在 equivalence fixture 通過前不移除 inline migration；API import 不可自動 migration operator DB。執行唯一允許的 Index migration 前，必須記錄 exact target、完成 read-only preview、建立並驗證可復原 backup，且取得正常 L3 runtime-mutation checkpoint。

驗收：fresh/current/legacy fixture DB 收斂到相同 schema；checksum 修改會 fail closed；雙 writer contention 有 bounded、classified 結果；backup/restore fixture 可由新 connection layer 讀取。

Rollback：舊 code 可忽略 additive Index tables 並切回既有 constructor，不需要 down-migration。若 operator DB 必須移除新 table，使用已驗證的 pre-migration backup restore；不得以自動 `DROP` 原地 rollback。Disposable fixture DB 可直接重建；DB filename 不變。

### P0-D — Search boundary、projection 與 incremental identity

交付：

- generic `AssetSearchResult`；
- additive `search_assets(..., asset_types=...)`、`index_assets(...)` service；
- 固定 `asset_type=skill` 的 legacy wrappers；
- bounded threadpool offload；
- hot-path SQL 不選 `raw_json`；
- 包含 asset/revision、parser ID/version、representation version、embedding model ID/version、content hash 的 index state；
- 只 embedding changed/missing representation 的 incremental index。

驗收：相同輸入第二次 index 為 0 new embeddings；version drift 只選中受影響 revisions；timeout/cancellation 不破壞 index；既有 Skill route 保持 response compatibility。Deterministic concurrency fixture 使用 2 workers、queue capacity 4：stub search 阻塞一秒時，10 次中至少 9 次 lightweight health request 在 250 ms 內完成；workers/queue 飽和後，下一個 request 必須在 250 ms 內回傳既定 overload response，且不得寫入 index。

Rollback：wrapper 可切回 full indexer；index-state 是 derived data，可重建。

### P0-E — Drift doctor 與條件式 read-only Asset API

Entry/cut line：doctor 為必要項目。只有 P0-B 至 P0-D focused gates 全部通過，且在中間沒有 corrective code change 的情況下連續兩次 full Python regression PASS，才能開始 Asset API sub-batch；否則全部新 Asset endpoints 延後到 P1。延後 API 不阻擋 P0 storage foundation 完成。

交付：

- `GET /api/assets`；
- `GET /api/assets/{asset_id}`；
- `GET /api/assets/{asset_id}/revisions`；
- `POST /api/assets/search`；
- 由 Skill filter 提供的 legacy `/api/skills` compatibility；
- 從 `tools/report_db_identity_drift.py` 演進的 revision-aware projection drift report；
- pending projection、stale index identity、duplicate canonical identity、model/version drift doctor fields。

本批次延後 evaluations/approvals/relations endpoint、mutation endpoint 與 Dashboard component rename。

驗收：Asset API 預設只回 projection；只有 detail endpoint 明確要求時才可回 payload；任何 Asset endpoint 都不能變更 governance 或 Runtime state；doctor 可區分 healthy、stale-derived-projection、authority-missing、unknown；Asset/Skill routes 皆有 compatibility tests。

Rollback：移除 additive router；legacy route 保持可用。

### P0-F — 整合驗證與 P1 decision packet

必要 gate：

```powershell
.\.venv\Scripts\python.exe -m compileall api asset_registry runtime vector_db tools scripts skill-0-dashboard/apps/api -q
.\.venv\Scripts\python.exe tools\check_doc_status_markers.py
.\.venv\Scripts\python.exe tools\check_shared_docs.py
.\.venv\Scripts\python.exe tools\validate_skill_schema.py parsed
.\.venv\Scripts\python.exe -m pytest tests skill-0-dashboard/apps/api/tests -q --timeout=120
npm run lint
npm test
npm run build:ci
git diff --check
```

附加 evidence：migration equivalence、incremental index changed/unchanged counts、event-loop responsiveness、drift doctor examples、legacy route matrix、secret/DB artifact diff scan。

只有全部 Core gates 通過，且沒有 real adapter、non-dry-run、physical topology/data migration 或 public deployment，才算 P0 完成。明確允許的 additive Index migration 必須單獨報告，且不代表 topology decision。

## 8. API 相容對照

| 既有 surface | P0 行為 | 新 surface |
|---|---|---|
| `GET /api/skills` | 固定 `asset_type=skill` wrapper | 條件式 P0-E `GET /api/assets` |
| `GET /api/skills/{id}` | 透過 Skill compatibility identity | 條件式 P0-E `GET /api/assets/{asset_id}` |
| `POST/GET /api/search` | 保持 request/response | 條件式 P0-E `POST /api/assets/search` |
| `POST /api/index` | 保留 authenticated legacy operation | 內部 `index_assets`；新 public mutation route 延後 |
| Runtime `skill_id` | P0 保持現有 contract | Asset identity 暫不 migration Runtime ledger |

P0 不設定移除期限；deprecation 需 usage evidence、versioned contract 與獨立核准 migration。

## 9. 本輪資料庫策略

| 現有檔案 | P0 邏輯角色 | Authority |
|---|---|---|
| `governance.db` | Legacy Registry/Governance adapter | Revision 與 approval authority |
| `skills.db` | Legacy Search Index adapter | Derived、可重建 projection |
| `runtime.db` | Runtime Ledger | Append-only execution authority |

P0 只允許加入 P0-C 表列的兩個 checksum-migrated Index tables；operator Governance/Runtime stores 不新增 DDL，不得把 governance rows 複製到 `skills.db`、合併 Runtime history，或宣稱最終 physical topology。

P1 DB 決策必須根據 migration/rollback rehearsal、backup unit、writer contention、index rebuild 時間與大小、operator complexity、FTS5/sqlite-vec benchmark。

## 10. 風險與控制

| 風險 | 控制 |
|---|---|
| Generic 命名破壞 Skill semantics | 先做 compatibility classification 與 golden fixtures |
| Repository abstraction 過度泛化 | P0 僅 SQLite protocol，不實作其他 backend |
| Envelope 與 ARD/runtime contract 衝突 | ADR-0004/0006 invariants 與 contract tests |
| Migration 破壞 legacy DB | Fixture copies、checksum gate、no import-time migration、backup/restore test |
| Async offload 變成無界 model work | Bounded worker、timeout/cancellation tests、metrics |
| Incremental index 提供 stale data | Revision/content/model identity 與 doctor-visible drift |
| 無證據決定實體 DB | P0 明確延後，P1 使用 decision packet |
| Scope 膨脹至 Dashboard/parser/real adapter | Non-goals 與每批驗收 gate |

## 11. P1 reopen candidates

P0-F 可提出、但不得實作：

1. `runtime_assets`、`asset_revisions`、representations、relations、evaluations、approvals、index outbox。
2. `registry.db + index.db + runtime.db` 與 `assets.db + runtime.db` 的物理決策。
3. FTS5 + sqlite-vec hybrid retrieval 與 score fusion。
4. Workflow ground-truth corpus 與第二個 parser adapter。
5. Dashboard `AssetShell` 與 type-specific panel。
6. 將 `parsed/` 遷移成 normalized build artifacts。
7. Legacy Skill API deprecation policy。

每一項都需要獨立 evidence 與 approval gate。

## 12. Definition of done

下一輪只有在下列條件全部達成時完成：

- ADR 與 Runtime Asset Envelope 已核准且有測試；
- 既有 Skill 行為由明確 adapter 保留；
- Runtime create/resume 不再逐次掃描 parsed directory；
- search/model 工作不再直接阻塞 API event loop；
- 未變更內容不會重新 embedding；
- search/list SQL 不多讀 raw payload；
- migration checksum 與 connection policy 可測且可觀察；
- drift doctor 能區分 authority failure 與 stale derived state；
- 所有既有與新增 gates 通過；
- 已產生 bounded P1 decision packet，但尚未執行 P1 migration。

## 13. 建議執行順序

每批以獨立、可 review 的 commit series 執行：

```text
P0-A contracts
  -> P0-B repository boundary
  -> P0-C migration/connection foundation
  -> P0-D search/index hardening
  -> P0-E Asset API/doctor
  -> P0-F integrated verification and P1 decision
```

任何 batch acceptance criterion 失敗都會阻擋全部 downstream batches。立即停止後續 mutation，保存第一份失敗 evidence；只進行分類所需的 read-only diagnostics，之後才可考慮 corrective replacement run。

## 14. 執行紀錄

- `P0-A` 已於 `2026-07-17` 完成：新增 ADR-0007/0008、Envelope v1、
  compatibility map、semantic failure fixtures 與 contract tests；focused
  contract/document verification 為 `27 passed`。
- `P0-B` 已於 `2026-07-17` 完成：新增 immutable legacy corpus repository、
  explicit Skill adapter、available/ambiguous identity map、stale snapshot guard，
  並以 Runtime dependency binding 取代 request-time JSON enumeration。Checked-in
  corpus 仍為 `196/196` schema-valid；focused repository、contract 與 Runtime API
  verification 為 `48 passed`。
- `P0-C` 已於 `2026-07-17` 完成 code 與 fixture boundary：新增 named SQLite
  policies、明確的 existing/read-only 與 maintenance modes、checksum-aware
  migrations、classified contention，以及通過 integrity check 的 backup/restore。
  未 migrate 任何 operator database；focused storage 與 Core API verification
  為 `48 passed`。
- `P0-D` 已於 `2026-07-17` 完成：同步 search/index 工作改由 two-worker、
  four-queue bounded executor offload；saturation 會快速失敗，caller cancellation
  不會提前釋放 capacity。Search/list hot paths 不再讀 raw payload，並由
  revision/model/representation identity 驅動 atomic incremental reconciliation。
  第二次 unchanged run 的 embedding 數為零；drift、removal 與 injected-failure
  fixtures 均通過。Focused search/index/API verification 為 `66 passed`。
- `P0-E` 已於 `2026-07-17` 完成：兩次連續完整 Python regression 均為
  `403 passed`，且中間沒有 corrective change，因此通過 conditional API cut
  line。其後新增 read-only Asset list/detail/revision/search surfaces，以及具
  schema version 的 drift doctor。Doctor 以穩定 exit code 區分 healthy、
  stale-derived-projection、authority-missing 與 unknown。目前本機 operator
  evidence 為 `authority-missing`（exit `2`），因為沒有 Governance operator DB
  或已 migrate 的 Asset index；這是觀察狀態，不是 implicit migration request。
- `P0-F` 已於 `2026-07-17` 完成：integrated gates 通過（`414` Python tests、
  `196` parsed schemas、`34` frontend tests、lint、build 與 bundle guard）。P1
  decision packet 對實體 DB 重整、FTS5、第二 Asset Type 與 Dashboard 改名維持
  NO-GO，直到各自 evidence gate 滿足。
