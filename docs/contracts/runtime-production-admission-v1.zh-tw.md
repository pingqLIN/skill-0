# Runtime Asset 正式環境準入 v1

狀態：`ACTIVE CONTRACT`

本文件是 Runtime Asset 支援範圍內，正式環境準入清單與契約的權威說明。
英文版
[`runtime-production-admission-v1.md`](runtime-production-admission-v1.md)
具規範效力；本文件是繁體中文對照版本。

本契約讓正式環境準入流程具備確定性與可稽核性。它不會部署發行版本、不會
獨立觀察主機、不會授權真實 adapter，也不會擴張既有 dry-run-only、單一
主機 Docker Compose 的 Runtime 邊界。

## 準入證據鏈

一份準入套件必須證明同一條不可變鏈結：

```text
Git commit 與 tree
  -> 正式環境 Compose 與 policy
  -> 已部署的 api/dashboard/web image digests
  -> 已核准的 model artifact digest
  -> 安全掃描、回歸測試與演練證據
  -> 已簽署的 external-control evidence
  -> 已簽署的操作人員核准
  -> 正式環境準入結果
```

套件是一份證據清單。`PASS` 只證明所提供的簽署聲明可信、仍在有效期限內、
未遭撤銷，且與受檢發行版本完整綁定；它不取代操作人員對實際部署環境的
觀察。

## 標準套件

`production-admission-package.json` 必須通過
[`production-admission-package.schema.json`](../../schema/production-admission-package.schema.json)
驗證。真實套件及其引用的證據必須放在程式庫外、具存取控制的受保護位置。

套件必須包含：

- 唯一 `admission_id`、可供人員辨識的發行版本 ID、建立時間，以及精確的
  正式環境身分；
- 乾淨工作樹的 Git commit 與 tree、正式環境 Compose 摘要值、正式環境
  policy 摘要值、獨立受信任的 keyring 摘要值、已核准的 model artifact
  digest，以及 `api`、`dashboard`、`web` 三個已部署 image digests；
- 以摘要值定址的安全掃描、回歸測試與正式環境演練證據；
- 既有 signed external-control bundle 的 ID、`path` 與摘要值；
- 操作人員身分、獲授權的 `role`、核准與到期時間，以及指向根層級
  Ed25519 `signature` 的 reference；
- 以標準化 JSON 套件為內容，排除根層級 `signature` 欄位後產生的 Ed25519
  簽章。

套件內的 `path` 必須是相對於單一受保護證據根目錄的 POSIX-style 路徑。
絕對路徑、路徑跳脫、檔案不存在、摘要值不符，或讓同一份檔案或相同內容
重複充當多個必要證據類別，都必須以 fail closed 方式拒絕。

## 證據與核准權限

證據產生者可以是 CI 工作、security scanner、建置系統、演練操作人員或
部署操作人員，但只能建立其實際觀察到的證據。程式庫內的檢查不得宣稱已
觀察 external TLS、network ACL、secret manager、主機、備份或集中式記錄
狀態。

External-control evidence 必須由受獨立管理的 trusted keyring 中，已獲指定
環境授權的 actor 與 key 簽署。最終套件必須由同一 keyring 中，具備精確
`production-admission-approver` 角色的操作人員簽署；只有 external-control
權限的角色不能核准準入。Keyring trust-anchor digest 必須由證據提交者無法
修改的 protected runner configuration 提供。

v1 verifier 會驗證授權與簽章，但不宣稱具備多人核准。若組織 policy 要求
獨立審查，應把證據產生與最終核准分派給不同人員。

## 必要證據與時效

所有時間一律以 UTC 評估。缺少時區、格式錯誤、來自未來、已到期或其他
不確定的時間戳記，都必須以 fail closed 方式拒絕。

| 證據 | 必要規則 |
|---|---|
| 安全掃描 | 至少一份以摘要值定址的結果；驗證時距觀察時間不得超過 168 小時；尚未到期；有效期間不得超過 168 小時。 |
| 回歸測試 | 採用相同的 168 小時時效與有效期間；結果必須涵蓋與發行版本綁定的測試範圍。 |
| 正式環境演練 | 採用相同的 168 小時時效與有效期間；必須對應指定的正式環境拓樸與發行版本。 |
| 外部控制 | 適用既有 external-control schema 與 verifier；觀察時間不得超過 24 小時，簽署有效期間不得超過 168 小時。 |
| 操作人員核准 | 驗證時距核准時間不得超過 24 小時，不得早於發行版本建立時間，尚未到期，且有效期間不得超過 168 小時。 |

每份證據的觀察時間都必須早於最終操作人員核准。證據到期、核准到期、
發行版本或環境發生偏移、摘要值改變，或出現新的 Git commit 時，都必須
建立新的準入嘗試與簽章。

## 驗證與決策

請從準備準入的精確、乾淨檢出目錄執行
[`runtime_admission_check.py`](../../tools/runtime_admission_check.py)。驗證器
會：

1. 驗證套件與 keyring schemas；
2. 透過 `SKILL0_EXTERNAL_CONTROL_TRUSTED_KEYRING_SHA256` 驗證 keyring；
3. 驗證核准時效、`production-admission-approver` 角色、操作人員授權、套件
   簽章與撤銷狀態；
4. 重新計算目前 Git、Compose 與 policy 綁定；
5. 解析並計算每一份引用證據的摘要值；
6. 要求套件與 external bundle 的 Git、images、model、environment 與
   evidence ID 完全相同；
7. 呼叫既有 external-control verifier，檢查其簽章、control set、
   attachments、時效、授權與撤銷狀態。

只有完整通過才回傳 JSON `status: PASS` 與 exit code `0`。任何缺漏、無效、
過期、遭撤銷、不相符、無法取得或不確定的檢查，都會回傳
`status: FAIL`、`release_gate: BLOCKED` 與 exit code `2`。

## 撤銷

Trusted keyring 是目前的撤銷權限來源。Admission package IDs 與 external
evidence IDs 共用 keyring 的 `revoked_evidence_ids` namespace。操作人員撤回
核准或 evidence bundle 時，必須加入受影響的 ID。撤銷 signing key 會讓
依賴該 key 的所有套件或 bundle 失效。之後必須透過獨立管理的 runner
流程更新受保護的 trust-anchor digest。

撤銷不得編輯或刪除原始套件。必須以僅附加的稽核歷史保留套件、驗證器
結果、原因、keyring revision/digest 與替代嘗試。

## 準入檢查清單

- [ ] 發行版本檢出目錄為乾淨狀態，且指向預定的 commit 與 tree。
- [ ] 三個值都是不可變的已部署 image digests，而非可變 tag 或 local image ID。
- [ ] Model digest 是已核准的 complete-tree artifact digest。
- [ ] 安全掃描、回歸測試、演練與 external-control evidence 都是真實、在有效期限內、可存取且以摘要值定址。
- [ ] Environment identity 描述真正的正式環境目標。
- [ ] Keyring trust anchor 由獨立來源注入；程式庫或 runner output 皆不含 private key。
- [ ] 操作人員具備精確的 `production-admission-approver` 角色。
- [ ] 操作人員在所有證據固定後，才簽署最終標準化套件。
- [ ] 驗證器回傳 `PASS`，且沒有失敗或不確定的檢查。
- [ ] 套件、驗證器報告與引用證據均依操作人員稽核 policy 留存。

## 回復與重新進入

準入必須具備經操作人員核准的 rollback path，涵蓋前一版應用程式映像檔、
設定與相符的三儲存區備份組。回復不得只降級 Runtime schema，卻保留較新
的 event data。若前一版發行版本無法解讀目前的權限或事件狀態，Runtime
必須維持停用，並保留儲存區以進行向前復原。

`BLOCKED` 結果不得被覆寫。請依
[`production-admission-recovery.zh-tw.md`](../production-admission-recovery.zh-tw.md)
收集替代證據、建立新的 `admission_id`、重新執行所有關卡，並保留完整的
嘗試歷史。
