# Runtime Asset 安全與相依性審核

**日期：** 2026-07-18

**更新：** 2026-07-20

**範圍：** P0 Runtime Asset Foundation and Storage Boundary

**權限：** 僅作為本機開發與 Runtime dry-run 證據，不是 production security clearance。

## 決策

**LOCAL_GO / PRODUCTION_NO_GO_PENDING_BASE_CVE_FIX。** 本次相依性修補可供本機 P0／P1 開發使用。已宣告的 Python 與 Web dependency graph 中，沒有已驗證的 Critical 或未處理 High finding。Runtime Asset index 在 provenance 觸發完整重建後維持 healthy。

Final API 與 Dashboard image 各含 Debian Bookworm essential Perl runtime 的 **1 個 Critical 與 2 個 High** finding，Bookworm 目前都沒有 fixed version。Pinned Web runtime image 含 **1 個 Critical 與 9 個 High** Alpine findings。處置方式是明確禁止 production，而不是接受風險：這些 images 都不具備 production、release、deploy 或 public exposure clearance。

## 證據

- 初始本機 Python 環境：79 個相依套件；`pydantic-settings`、`setuptools`、`torch`、`transformers` 共 7 個 advisory。
- 修補後本機 Python 環境：82 筆 dependency record；其中 81 筆可稽核套件沒有 known vulnerability。CPU build `torch==2.13.0+cpu` 因 PyPI 沒有該 local-version identifier 而被 `pip-audit` 跳過；其實際安裝版本與 upstream fixed-version boundary 已另行核對。
- Legacy partial `requirements.lock`：修補後 15 個 pin 沒有 known vulnerability；檔案已明確標示為非權威且不完整。
- Web lockfile：480 個相依套件，npm audit 為 0；production web image 執行 `npm ci` 時同樣回報 0 vulnerability。
- GitHub Dependabot API：擷取時為 0 個 open alert。
- 升級後 embedding stack probe：196 個 Asset document vector 與 5 個固定 query vector 全部 bitwise equal，5 組 top-10 排序也完全相同。
- 升級後 strict indexing：第一輪因 stack provenance 改變而重建 196/196；第二輪為 196/196 unchanged；drift doctor 為 `healthy`、exit code 0。
- Container build：API、Dashboard API、Web 三個 image 皆成功。API image 直接驗證 `sentence-transformers 5.6.0`、`transformers 5.14.1`、`torch 2.13.0+cpu`、`setuptools 83.0.0`，`asset_registry`／`VectorStore` import 成功，`pip check` clean。
- Container CVE scan：先前 Debian Trixie API image 有 1 個 Critical 與 11 個 High finding。改 pin 最新 Bookworm image digest 後，所有 glibc／OpenSSL finding 已移除；final API image 完整掃描只留下 1 個 Critical 與 2 個 High Perl finding，application layer 沒有新增 Critical／High。
- `2026-07-20` follow-up offline `local://` scans 驗證 pinned Dashboard candidate 為 1 Critical／2 High，pinned Web candidate 為 1 Critical／9 High。Web base 從 digest `806f6d3e...` 更新為 `08c2bc9344...` 後，觀察結果由 2 Critical／14 High 降低，但仍未通過 Critical／High 必須為零的 gate。
- `2026-07-21` fresh rebuild 與 `local://` scan 再次得到 API 1 Critical／2 High、Dashboard 1 Critical／2 High、Web 1 Critical／9 High。同一次演練也驗證新的 approved local model artifact digest gate；詳見 [`runtime-production-compose-rehearsal-2026-07-21.zh-tw.md`](runtime-production-compose-rehearsal-2026-07-21.zh-tw.md)。
- 所有 production Dockerfile stages 現在都已 digest-pin。所有 remote GitHub Actions references 也已 pin 到完整 commit SHA，並以註解保留預期 major version。Static regression tests 會在 Docker stage 或 action reference 可變時 fail。使用 pinned images 的第二次 isolated Compose rehearsal 已通過 build、health、production doctor、governed dry-run、deterministic Evidence、three-store backup/restore、restart persistence 與 zero-resource cleanup。
- Regression：451 個 Python test、34 個 Web test 通過；frontend production build 與 Python compile check 通過。
- Follow-up hardening regression：508 個 Python/API tests、36 個 frontend tests 通過；frontend lint/build 與 schema validation 196/196 通過。

忽略追蹤的本機證據位於 `.artifacts/security-review/20260717T214200Z/`，包含 resolver report、audit JSON、vector comparison 與 strict indexing evidence。

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

### Production blocker：Debian Perl 弱點尚無 Bookworm fix

完成的 final-image Scout report 包含：

| Advisory | Severity | 觸發面 | Bookworm fixed version | 處置 |
|---|---|---|---|---|
| `CVE-2026-12087` | Critical | Perl `Socket::pack_ip_mreq_source` 接收攻擊者控制的短 source value | 尚無 | 禁止 production |
| `CVE-2026-48959` | High | Perl `IO::Uncompress::Unzip` 處理攻擊者控制的 ZIP | 尚無 | 禁止 production |
| `CVE-2026-48962` | High | Perl `IO::Compress::File::GlobMapper` 接收攻擊者控制的 output glob | 尚無 | 禁止 production |

Skill-0 API 以 non-root user 執行 Python；已檢查的 application path 不會呼叫 Perl，也沒有暴露上述 Perl API。這降低本機 dry-run 的已觀察可達性，但不會消除 essential package 的弱點，也不構成 production 授權。Debian 目前仍將 Bookworm 的相關 source package 列為 vulnerable：[`CVE-2026-12087`](https://security-tracker.debian.org/tracker/CVE-2026-12087)、[`CVE-2026-48962`](https://security-tracker.debian.org/tracker/CVE-2026-48962)。

Owner：Runtime maintainers。重新驗證期限：**2026-07-25**。須以已修補的官方 base digest 重建後執行：

```powershell
docker scout cves --only-severity critical,high --format sarif --output api-cves.sarif local://skill-0-api:<review-tag>
```

除非結果為零 Critical／High，或人類針對 fresh reachability review 另行核准有期限的 production exception，否則 production 維持 blocked。

## 剩餘 Warnings／Blockers

1. **Dashboard／Web container CVE inventory — VERIFIED production blockers。** Dashboard Bookworm image 與 API 相同，含尚無修正版的 Perl 1 Critical／2 High。Web image 含 OpenSSL 1 Critical／8 High，加上 musl 1 High；Scout 回報 fixed boundaries 為 `openssl>=3.5.7-r0` 與 `musl>=1.2.5-r23`，但目前官方 image digest 仍含較舊套件。Build environment 的 TLS trust gate 阻止安全 package refresh，且本次沒有使用 trusted-host 或 force-missing-repository bypass。必須以更新的官方 digest 或 approved CA-enabled rebuild 重驗；gate 仍要求 Critical／High 為零。
2. **Legacy lock 不完整 — Warning。** `requirements.lock` 未被 CI 或 container 使用，也不是具有 hash 的完整 transitive lock。現在僅保留為已標示的 legacy snapshot；後續應改成按環境拆分、hash-verified lock，或依 repository 的 recoverable deletion workflow 移除。
3. **Model approval boundary — application control 已解決，deployment evidence 仍為必要。** Production 現在要求 absolute、symlink-free 的 local model directory，以及 operator-approved complete-tree digest。Startup、`SkillEmbedder`、index identity 與 production doctor 在 artifact 缺少、格式錯誤、不可讀或 digest 不一致時都會 fail closed；remote fallback 只保留在非 production，Compose model volume 則是 read-only。因 host 與 volume administration 仍在 application trust boundary 之外，實際 deployment 仍須提供 reviewed artifact、approved digest 與 operator evidence。

上述 warnings 與 blockers 交由 Runtime maintainers 在第一個 production-hardening batch 處理。關閉前，本審核只支援本機 Runtime dry-run 與 P1 Search evidence。
