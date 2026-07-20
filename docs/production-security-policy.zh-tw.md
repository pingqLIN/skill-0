# Production Security Policy v1

- 狀態：**已接受，適用 Runtime Architecture v1 stable foundation**
- 版本：`1.5.0`
- 生效日期：`2026-07-21`
- Machine-readable policy：[`contracts/production-security-policy-v1.json`](contracts/production-security-policy-v1.json)
- Operations：[`runtime-production-operations.md`](runtime-production-operations.md)
- Authority lifecycle：[`governance-authority-lifecycle.md`](governance-authority-lifecycle.md)
- 英文權威文件：[`production-security-policy.md`](production-security-policy.md)

## 1. Scope 與 security objective

本 policy 定義 stable foundation 的 minimum production controls：single-host Docker Compose、Core API、Governance/Dashboard API、web、分離的 `skills.db`／`governance.db`／`runtime.db`、僅 `asset_type=skill`，以及使用 simulation adapter 的 dry-run-only Runtime API。

目標是維持 exact Governance authority、防止 unauthorized Runtime decisions、contain untrusted Asset/Knowledge/Evaluation data、保護 credentials 與 operator stores，並保存 auditable recovery evidence。

本 policy 不把現有 Compose file 視為 internet edge。TLS、firewalling、secret management、host encryption 與 access logging 是 repository 外部必須提供的 deployment controls。

## 2. Evidence state

### VERIFIED application/repository controls

- Production startup 會拒絕 development JWT secret、missing API credentials、localhost/wildcard CORS、Runtime binding-key placeholder 或 key reuse、missing decision actors、invalid HITL TTL，以及 non-WAL Runtime mode。
- Production config 關閉 API docs/OpenAPI。
- Login/general API 有 rate limit；credential comparison 使用 fixed-length constant-time digests。
- 只有 explicit enable proxy trust 且 peer 位於 trusted proxy CIDRs 時，才接受 forwarded client-IP headers。
- Runtime create/resume/recovery request models 要求 `dry_run: Literal[True]`；public Runtime route 只接受 test adapters，simulation adapter 拒絕 real execution。
- Core API 以 read-only mount 使用 `governance.db`；Governance service 擁有 write。Runtime decisions/evidence 使用獨立 Runtime store。
- Production startup 與 production doctor 都會拒絕 `SKILL0_RUNTIME_ALLOW_INITIALIZE=true`。缺少 Runtime ledger 時必須經 verified recovery workflow restore；production boot 不得初始化它。
- Public `/health` 只回傳 liveness status。`/api/health/detail` 需要 JWT authentication，且不回傳 database path、storage size、model name、version metadata。
- Runtime doctor 可要求三個 stores 都有 current/readable backup，且只回報 configuration names，不回報 secret values。
- HITL decision 需要 authenticated JWT subject 出現在 `SKILL0_RUNTIME_DECISION_ACTORS`，並受 immutable item deadline 限制。
- Production 要求 absolute、symlink-free、由 operator materialize 的 model directory，並設定 `SKILL0_EMBEDDING_MODEL_ARTIFACT_DIGEST`。Startup、model loading、index identity 與 production doctor 都會計算具版本的完整 tree digest；artifact 缺少、格式錯誤、不可讀或 digest 不一致時一律 fail closed。Model volume 為 read-only，remote fallback 維持停用；錯誤只回傳穩定 reason code，不顯示 path 或 digest value。

### REQUIRED deployment controls（application 未強制）

- 使用 maintained reverse proxy/ingress 終止 modern TLS；不得把 Compose HTTP ports 直接暴露給 untrusted network。
- 以 network ACL 限制 Core API、metrics、health 與 administrative routes；Dashboard API 應留在 internal service network。
- 以 secret manager 或同等 protected injection 保存 JWT、API、Runtime binding credentials；不得把 real values 寫入 repository `.env`、image layer、log、backup manifest 或 shell history。
- JWT、API password、Runtime binding secret 必須各自 unique/high-entropy。Application 會檢查 binding-key length/independence，但不檢查所有 credentials 的 entropy。
- Host volumes/backups 必須 encrypted at rest、限制 ownership/mode，且 backup decryption keys 與 media 分離。
- Host/container administration、Docker socket、backup paths、model cache writes 只允許 named operator roles。
- Provision read-only model volume 前，必須先核准 exact model artifact digest。即使 application 會驗證 mounted bytes，host／volume administrator 仍屬 application trust boundary 之外。
- 集中保存 logs，設定 retention/access control，並保留 request、Governance revision、Runtime run、event correlation。
- 將 public liveness 與 metrics routes 限制於 trusted network boundary；authentication 可降低暴露，但不能取代 network containment。

缺少任一 required deployment control 時，即使 application doctor 通過，也不符合本 policy。

## 3. Identity、authentication、authorization

1. 設定 `SKILL0_ENV=production` 與 `SKILL0_ENABLE_DOCS=false`。
2. 使用 exact HTTPS `CORS_ORIGINS`；production 禁止 wildcard、localhost、loopback origins。
3. 替換所有 `CHANGE_ME`。`JWT_SECRET_KEY` 與 `SKILL0_RUNTIME_BINDING_KEY` 必須獨立；後者至少 32 characters。
4. 設定 non-empty `API_USERNAME`/`API_PASSWORD`，只經 TLS 傳送，疑似暴露後立即 rotate。
5. `SKILL0_RUNTIME_DECISION_ACTORS` 必須是 explicit authenticated subjects，不得使用 placeholder 或 request-body actor。
6. JWT lifetime 必須 bounded。現有 token 透過 secret rotation 失效；foundation 沒有獨立 token-revocation service。
7. Governance revision approval 與 Runtime HITL approval 是不同 authority；任一 actor role 都不隱含另一個 role。

## 4. Network 與 proxy boundary

- Edge 只 publish intended web origin；API traffic 經 trusted proxy，不得讓 host-mapped API port 普遍可達。
- 除非 direct peers 都是 controlled proxy 且 `SKILL0_TRUSTED_PROXY_CIDRS` 只包含這些 peers，否則保持 proxy-header trust disabled。
- `/metrics`、health detail、authentication、index maintenance、Governance mutation、Runtime decision、backup interfaces 必須限制在 minimum principals/networks。
- CORS 不是 authentication 或 firewall。
- External tunnel、public route、DNS、certificate、ingress change 都需要獨立 explicit approval 與 exposure review。

## 5. Runtime 與 authority controls

- Production policy 僅允許 dry-run。任何 `dry_run=false`、non-test public adapter 或 real compensation 都必須失敗。
- Admission 必須驗證 exact current Governance revision、Asset identity、version、artifact digest、approver、approval timestamp。
- Search、Knowledge context、Agent Evaluation report、Dashboard state、mutable `skills.status`、prior run result 永遠不是 authority。
- Unknown effect、risk、rule evaluator、authority、source freshness、adapter outcome 都 fail closed；ambiguous outcome 進入 reconciliation。
- Runtime HITL actor allowlist/immutable deadline 是 mandatory；approval 只記錄 decision，不自動 execute/resume/recover。
- Approve/reject/scan/test write 與 immutable Dashboard action-job target 已實作 current-target enforcement。Rejected current revision 不能 direct approve；fresh reapproval 必須 new exact-bound revision、post-binding scan/test evidence，以及同 transaction 的 review/decision audit artifacts。Approval expiry、quorum、dedicated revocation、cryptographic audit chain 與 database-level tamper resistance 仍是 gaps。

## 6. Data、SQLite、backup、restore

| Store | Security role | Required access |
|---|---|---|
| `skills.db` | Derived/rebuildable Index | Core API read/write；不是 authority |
| `governance.db` | Revision/approval authority | Governance service read/write；Core API read-only |
| `runtime.db` | Append-only event ledger/Runtime projections | Core API read/write |

- 維持 separate stores/named volumes；本 policy 不授權 physical DB migration、rename、merge、split。
- Normal operation 保持 `SKILL0_RUNTIME_ALLOW_INITIALIZE=false`；缺少 Runtime history 必須 startup fail。
- Runtime 要求 WAL 與 configured HITL TTL；沒有獨立證據前不得全域改其他 SQLite durability policy。
- 建立包含三個 stores、operationally matched 且 integrity-checked 的 backup set。現有 sequential SQLite backups 不是 cross-store atomic snapshot；incident 或 release 需要單一 logical point-in-time 時，必須 freeze relevant decisions/writers。Backup set 依 operator policy encryption/access-control/retention/test。
- Restore rehearsal 使用 isolated volumes。不得覆寫唯一 damaged copy；保留供 forensic analysis。
- Restore matching three-store set 後執行 doctor、identity/authority drift，並在 reopening 前建立 fresh governed dry run。
- 不得編輯 append-only events、approval provenance、historical revisions 來隱藏 incident。

## 7. Untrusted content、logs、privacy

- Skill payload、Knowledge content、benchmark input/candidate、external document、adapter response 都是 untrusted data。
- 不得 evaluate Skill/Knowledge contract 的 expression/code，也不得依 retrieved instruction 擴張 access 或 bypass approval。
- 未來啟用 Knowledge resolver 前，必須執行 classification、authorization、digest、budget、redaction、prompt-injection controls。
- Agent Evaluation report 的 candidate provenance 維持 `unverified`；不得把 private prompts/responses/traces 公開為 evidence。
- Logs/public Evidence 不得包含 secrets、credentials、raw authorization headers、private payload、非必要 recovery parameters；使用 stable IDs、reason codes、digests、counts、redacted summaries。
- Public health/error response 不得暴露 filesystem layout、SQL text、stack trace 或非必要 config values。Public health route 僅回傳 status；authenticated detail route 不回傳 database path、storage size、model name、version metadata。

## 8. Supply chain 與 build policy

- 從 reviewed commit 與 pinned/bounded dependency inputs build；promotion 前跑 dependency/security review 與全部 release tests。
- 不得關閉 TLS verification 或加入 trusted-host bypass。Build CA 使用既有 ephemeral secret mount 並移除。
- Image 不得包含 operator DB、real `.env`、credential、backup、private benchmark artifact。
- 每個 release candidate 記錄 source commit、image digest、dependency lock digest、test results、vulnerability-scan state。
- SBOM、image signing、provenance attestation、continuous image scanning 是 recommended controls，但 repository 尚未強制；沒有 external evidence 不得宣稱。

## 9. Production release gate

以下 evidence 缺一即 block release：

1. full Python regression 保留採用時的 459-test baseline，且所有新增 focused tests 通過；
2. 若發布 frontend artifacts，frontend lint/tests/`build:ci` 通過；
3. placeholder/missing credential 與 unsafe CORS 會 fail closed；
4. Runtime 維持 dry-run-only 且只走 simulation/test adapter；
5. initialization disabled、three valid stores、Runtime WAL、actor allowlist、TTL、current backups 與 exact approved local model artifact digest 均成立時 doctor healthy；
6. restore/restart rehearsal 與 fresh governed dry run 通過；
7. secret/artifact diff scan 沒有 credential、operator DB、backup、private benchmark material；
8. independent review 無 unresolved Critical/Warning；
9. external TLS、network ACL、secret-manager、host-volume、backup-encryption、monitoring 有 operator evidence。

Unavailable check 是 `UNKNOWN` 並阻擋其 claim。Timeout、acknowledgement-only review 或 passed application doctor 都不是 external deployment control 的證據。

## 10. Incident response 與 rotation

1. Contain exposure：移除 public access、disable new Runtime decisions；安全時保留 services/stores 供 evidence。
2. 保存 correlated logs、images、configuration names、three-store backups、Governance audit、Runtime watermarks；不要複製 secret values 到 incident report。
3. 分類 affected authority、Asset revisions、runs、HITL items、credentials、backups、external data。
4. 經 secret manager rotate API/JWT/Runtime secrets；binding-key rotation 會刻意讓 prior keyed execution bases 與 unconsumed Runtime resume approvals non-resumable，但不刪除 Governance history。
5. Integrity 有疑慮時只從 verified matching backup set restore。
6. Reopening 前重跑 release gates 並建立 fresh authority/run evidence。
7. 記錄 residual uncertainty，透過 approved private channels 通知 affected parties。

## 11. Prohibited production states

- real adapter 或 non-dry-run execution；
- wildcard/localhost CORS 或 direct untrusted HTTP exposure；
- default、placeholder、shared、logged、committed、image-baked credentials；
- empty decision allowlist 或 invalid/unbounded HITL deadline；
- normal operation 啟用 Runtime initialization；
- Core API writable Governance mount；
- missing/corrupt/stale three-store backup evidence；
- public metrics/admin routes 無 network controls；
- 本 baseline 下整合 FTS5；
- 新 Runtime Asset type；
- 把 Dashboard redesign 當成 security dependency；
- 未經獨立核准 migration program 的 physical DB migration。
