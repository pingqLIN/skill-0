# Runtime Asset 安全與相依性審核

**日期：** 2026-07-18

**更新：** 2026-07-21

**範圍：** P0 Runtime Asset Foundation and Storage Boundary

**權限：** 僅作為本機開發與 Runtime dry-run 證據，不是 production security clearance。

## 決策

**LOCAL_GO / REPOSITORY_SECURITY_GATE_GO / PRODUCTION_NO_GO_PENDING_EXTERNAL_OPERATOR_EVIDENCE。** 本次 dependency 與 image remediation 可供 repository-controlled Runtime foundation 使用。Final API、Dashboard、Web image 都是 0 Critical／0 High；Runtime Asset index 維持 healthy，且 API base migration 的受測 embedding vectors 逐 bit 相同。

API 改用 same-release Ubuntu 24.04 multi-stage image，因 PyTorch CPU wheels 需要 glibc-compatible runtime。All-severity inventory 仍有 Ubuntu 15 Medium／5 Low，以下列為 residual risk；依 scanner/vendor classification，沒有 Critical／High。Dashboard 可獨立遷移到 Python Alpine 3.24，並在升級 image 的 build/runtime `pip` 後達到所有 severity 都為零。Web 同樣維持所有 severity 為零。Production、deploy 與 public exposure 仍 blocked，因 required external controls 的真實 signed operator evidence 尚未提供或驗證。

## 證據

- 初始本機 Python 環境：79 個相依套件；`pydantic-settings`、`setuptools`、`torch`、`transformers` 共 7 個 advisory。
- 修補後本機 Python 環境：82 筆 dependency record；其中 81 筆可稽核套件沒有 known vulnerability。CPU build `torch==2.13.0+cpu` 因 PyPI 沒有該 local-version identifier 而被 `pip-audit` 跳過；其實際安裝版本與 upstream fixed-version boundary 已另行核對。
- 已移除 legacy `requirements.lock`：這份 15-package partial snapshot 從未被 CI 或 containers 使用，卻可能被誤認為 authoritative lock。可復原的本機 copy 保留在已忽略的 `.del/`；在另行審查並導入 hash-complete lock workflow 前，active environment inputs 仍是各自 scoped `requirements-*.txt` files。
- Web lockfile：480 個相依套件，npm audit 為 0；production web image 執行 `npm ci` 時同樣回報 0 vulnerability。
- GitHub Dependabot API：擷取時為 0 個 open alert。
- 升級後 embedding stack probe：196 個 Asset document vector 與 5 個固定 query vector 全部 bitwise equal，5 組 top-10 排序也完全相同。
- 升級後 strict indexing：第一輪因 stack provenance 改變而重建 196/196；第二輪為 196/196 unchanged；drift doctor 為 `healthy`、exit code 0。
- Container build：API、Dashboard API、Web 三個 image 皆成功。API image 直接驗證 `sentence-transformers 5.6.0`、`transformers 5.14.1`、`torch 2.13.0+cpu`、`setuptools 83.0.0`，`asset_registry`／`VectorStore` import 成功，`pip check` clean。
- Container CVE scan：先前 Debian Trixie API image 有 1 個 Critical 與 11 個 High finding。改 pin 最新 Bookworm image digest 後，所有 glibc／OpenSSL finding 已移除；final API image 完整掃描只留下 1 個 Critical 與 2 個 High Perl finding，application layer 沒有新增 Critical／High。
- `2026-07-20` follow-up offline `local://` scans 驗證 pinned Dashboard candidate 為 1 Critical／2 High，pinned Web candidate 為 1 Critical／9 High。Web base 從 digest `806f6d3e...` 更新為 `08c2bc9344...` 後，觀察結果由 2 Critical／14 High 降低，但仍未通過 Critical／High 必須為零的 gate。
- `2026-07-21` fresh rebuild 與 `local://` scan 再次得到 API 1 Critical／2 High、Dashboard 1 Critical／2 High、Web 1 Critical／9 High。同一次演練也驗證新的 approved local model artifact digest gate；詳見 [`runtime-production-compose-rehearsal-2026-07-21.zh-tw.md`](runtime-production-compose-rehearsal-2026-07-21.zh-tw.md)。
- 後續在 `2026-07-21` 進行 Web-only remediation，改用 official multi-architecture digest `sha256:90d82b3358df5758b3c57d20f2565082ce6f744906e7dc09afd0096c1b8eb2b5`。重建後的 final Web image（`sha256:f604964103605aae8e96fafd642a0bc3a937596638252bd9291aa9f74aec29fc`）經 Docker Scout 掃描為 `0 Critical／0 High／0 Medium／0 Low`；SARIF 為零 results，SHA-256 是 `69933e606e8fc010c7d1df52993f413523163ac7ca1c3247fc26bdbc6c946878`。Isolated bridge-network smoke 在 container user `101` 下回傳 HTTP 200。
- Final API remediation 使用 digest-pinned `ubuntu:24.04@sha256:4fbb8e6a8395de5a7550b33509421a2bafbc0aab6c06ba2cef9ebffbc7092d90` 的 same-release multi-stage build。Image `sha256:dc7ac417bcfb3ebf49eefaffb3b1834bfd34a5b4e3e0984b4f06d5af4111c088` 通過 imports、`pip check`、HTTP 200、UID 65532、build CA absence，以及與舊 Bookworm control 的 10-vector bitwise comparison。Critical/High SARIF 是零 results，SHA-256 為 `69933e606e8fc010c7d1df52993f413523163ac7ca1c3247fc26bdbc6c946878`；all-severity SARIF 有 15 Medium／5 Low，SHA-256 為 `bdf53c8f2785d151e3bebcd7c1c95e01e87257e2a3d8d5642cf946f2e3999330`。
- Final Dashboard remediation 使用 digest-pinned `python:3.12-alpine3.24@sha256:f7fd610959cae736251523b54eb26cecb74f60ffa60bf39d9faccf128b526ab8` 與 bounded `pip>=26.1.2,<27`。Image `sha256:be736191417bcbed79406dde15aa70b585aff2d17daf82d0473232bcaa666bd3` 通過 imports、`pip check`、HTTP 200 與 non-root user checks；all-severity SARIF 是零 results，SHA-256 為 `69933e606e8fc010c7d1df52993f413523163ac7ca1c3247fc26bdbc6c946878`。
- 新增 fail-closed Ed25519 external-control verifier，可驗證 schema、protected-runner keyring SHA-256 trust anchor、key revocation、actor role/environment authorization、freshness/expiry、exact Git/tree/keyring/Compose/policy/model/image binding、完整八項 policy control set、path-contained attachments 與 attachment digests，並拒絕 tracked 或 untracked non-ignored source drift。Missing、stale、malformed、tampered、wrong-scope、unauthorized 或 incomplete evidence 會回傳 `UNKNOWN` 並 exit 2。Verifier 只證明 integrity/scope，不代表 physical control truth；真實 bundles/keyrings 保持 external 且不 commit。
- 所有 production Dockerfile stages 現在都已 digest-pin。所有 remote GitHub Actions references 也已 pin 到完整 commit SHA，並以註解保留預期 major version。Static regression tests 會在 Docker stage 或 action reference 可變時 fail。使用 pinned images 的第二次 isolated Compose rehearsal 已通過 build、health、production doctor、governed dry-run、deterministic Evidence、three-store backup/restore、restart persistence 與 zero-resource cleanup。
- Regression：451 個 Python test、34 個 Web test 通過；frontend production build 與 Python compile check 通過。
- Follow-up hardening regression：508 個 Python/API tests、36 個 frontend tests 通過；frontend lint/build 與 schema validation 196/196 通過。
- Final Item 3 regression：555 個 Python/API tests 通過；frontend lint、36 tests、production build 與 bundle-size gate 通過；schema validation 維持 196/196。Fresh isolated Compose rehearsal 通過原有全部 gates，並確認沒有殘留 container、volume 或 network。
- Independent read-only review 首輪因 caller-selectable keyring trust 與 untracked-source blind spot 兩個 Warning 而回傳 `NO_GO`。Protected-runner keyring digest anchor、signed keyring binding、all-untracked Git check 與 regression tests 關閉兩項 finding；第二輪對 repository-controlled Item 3 回傳 `GO`，沒有 Critical／Warning。Production 因缺少真實 external evidence，仍獨立維持 `NO_GO`。

忽略追蹤的本機證據位於 `.artifacts/security-review/20260717T214200Z/` 與 `.artifacts/security-review/20260721-item3-final/`，包含 resolver report、audit JSON、vector comparison、strict indexing evidence 與 final-image SARIF；這些是 local evidence，不是 publishable release artifacts。

## Findings 與處置

### 已解決 High：Transformers 4.x 弱點邊界

原本的 `transformers<5` 會解析為 4.57.6，受到多個不安全 model／config deserialization 路徑影響；相關修補門檻分別位於 5.0、5.3、5.5。現在限制為 `transformers>=5.14.1,<6`，並搭配 `sentence-transformers>=5.6,<6`、`torch>=2.13,<3`。

此 major upgrade 並非只依賴 resolver 結果。本機以 offline `all-MiniLM-L6-v2` 比對，確認受測 corpus／queries 的 vector bitwise identical 且 ranking 穩定。這是有限範圍的相容性證據，不代表 Transformers 支援的所有 model 都等價。

主要參考：[GHSA-fgcw-684q-jj6r](https://github.com/advisories/GHSA-fgcw-684q-jj6r)、[GHSA-69w3-r845-3855](https://github.com/advisories/GHSA-69w3-r845-3855)、[GHSA-29pf-2h5f-8g72](https://github.com/advisories/GHSA-29pf-2h5f-8g72)、[CVE-2025-14929](https://nvd.nist.gov/vuln/detail/CVE-2025-14929)。

### 已解決 High：index identity 未涵蓋 embedding stack drift

先前 incremental index 只辨識 model artifact／version，因此 dependency upgrade 可能在未證明相容性時沿用舊 vector。現在 index identity 會納入已安裝 `sentence-transformers`、`transformers`、`torch` 版本的 SHA-256 digest。新增測試證明 stack version 改變會強制重建，而未改變時保持 no-op。

### 已解決：Packaging 與 settings advisories

- `torch` 從 2.12.1 升至 2.13.0，符合既有 advisory 的 fixed boundary。
- `setuptools` 從 81.0.0 升至 83.0.0；API Dockerfile 不再於安裝 application dependencies 後將它降版。
- `pydantic-settings` 從 2.14.1 升至 2.14.2。
- `PyJWT`、`pytest` 的 minimum，以及 legacy snapshot pin，皆提高到目前已稽核邊界。

主要參考：[PyTorch advisory](https://github.com/advisories/GHSA-rrmf-rvhw-rf47)、[pydantic-settings advisory](https://github.com/advisories/GHSA-4xgf-cpjx-pc3j)、[PyPA pip-audit](https://pypi.org/project/pip-audit/)。

### 已解決：API container 漏掉 Runtime Asset code

第一次 dependency-reviewed API image 在 import `VectorStore` 時失敗，原因是 image 未複製 `asset_registry/`。Dockerfile 已補上該 package，final image import probe 通過。

### 已解決 production blocker：Bookworm Critical／High Perl findings

歷史 Bookworm final-image Scout report 包含：

| Advisory | Severity | 觸發面 | Bookworm fixed version | 處置 |
|---|---|---|---|---|
| `CVE-2026-12087` | Critical | Perl `Socket::pack_ip_mreq_source` 接收攻擊者控制的短 source value | 尚無 | 禁止 production |
| `CVE-2026-48959` | High | Perl `IO::Uncompress::Unzip` 處理攻擊者控制的 ZIP | 尚無 | 禁止 production |
| `CVE-2026-48962` | High | Perl `IO::Compress::File::GlobMapper` 接收攻擊者控制的 output glob | 尚無 | 禁止 production |

API 已移到 reviewed、digest-pinned Ubuntu 24.04 same-release multi-stage design；Dashboard 則獨立移到 Python Alpine 3.24。Final scanned images 是 0 Critical／0 High，因此不需 cross-release package surgery、finding suppression、TLS bypass 或 vulnerability exception，即可關閉舊 Bookworm deny。API 仍包含 Ubuntu `perl-base` 與其他 OS packages，共 15 Medium／5 Low；報告保留其存在與 vendor severity，不宣稱 Perl 不存在。

持續使用的 revalidation command 為：

```powershell
docker scout cves --only-severity critical,high --format sarif --output api-cves.sarif local://skill-0-api:<review-tag>
```

目前已達成 0 Critical／High。未來任何 image 變更都必須重跑此命令，並使目前 image-bound evidence 失效。

## 剩餘 Warnings／Blockers

1. **API lower-severity inventory — VERIFIED residual risk，不是 Critical／High exception。** Ubuntu API image 在 13 個 OS packages 中有 15 Medium／5 Low；完整結果保留在 all-severity SARIF，base/package 每次更新都必須重新評估。Vendor severity 不代表可隱藏 findings，也不得把 image 描述為 vulnerability-free。
2. **External-control operator evidence — UNKNOWN 且會 block release。** Repository 現在有 signed、exact-release-bound verifier，但未提供真實 bundle、external trusted keyring、attachment set 或 physical observation。因此 TLS termination、network ACL、secret management、unique credential quality、volume protection、encrypted separated backups、host/container administration 與 centralized log controls 仍是 `UNKNOWN`。Synthetic fixture 或 application doctor 通過都不能關閉此 gate。
3. **Model approval boundary — application control 已解決，deployment evidence 仍為必要。** Production 要求 absolute、symlink-free local model directory 與 operator-approved complete-tree digest。Startup、`SkillEmbedder`、index identity、production doctor 在 artifact 缺少、格式錯誤、不可讀或不一致時都會 fail closed；remote fallback 只保留在非 production，Compose model volume 是 read-only。因 host/volume administration 仍在 application trust boundary 外，真實 deployment bundle 必須綁定 reviewed model digest。
4. **Source-to-image 與 SARIF target binding — Advisory。** Release verifier 會拒絕 tracked 與 untracked non-ignored source drift，runbook 也要求 dedicated release checkout；但 retained SARIF 不會自行記錄 scanned local image ID。Policy v1.6.0 仍把 OCI provenance、image signing、digest-stamped scan envelope 與 continuous scanning 列為 recommended、非 enforced。若要宣稱 cryptographic source-to-image provenance，必須先把此 Advisory 提升為 required control。

Repository-controlled security work 已可進入 RC branch。Production 維持 `NO_GO`，直到 authorized operator 針對 exact clean commit、policy、Compose file、deployed image digests、model digest 與 named environment 提供 fresh signed evidence bundle，且 verifier 回傳 `VERIFIED`。本次沒有 deploy、public exposure、real credential 使用或 exception。
