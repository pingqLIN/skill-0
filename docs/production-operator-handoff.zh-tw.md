# 正式環境準入操作人員交接說明

本文件是 Runtime Asset Production Admission v1 的人工交接說明。英文版
[`production-operator-handoff.md`](production-operator-handoff.md) 具規範效力；
本文件是繁體中文對照版本。權威契約請見
[`runtime-production-admission-v1.md`](contracts/runtime-production-admission-v1.md)。

目前狀態：

- Repository Gate：`GO`
- Production Admission：`WAITING_FOR_OPERATOR_EVIDENCE`

程式庫提供 schema 與 fail-closed verifier。正式環境操作人員必須提供實際
部署環境身分、觀察結果與簽章；AI agent 無法生成或替代這些事實。

## 必須由人員提供的資料

操作人員必須從權威的正式環境或發行系統取得下列全部項目：

1. 符合
   [`production-external-control-keyring.schema.json`](../schema/production-external-control-keyring.schema.json)
   的獨立管理 trusted keyring。
2. 該 keyring 的精確 SHA-256，由證據提交者無法修改的 protected runner 或
   同等控制，以 `SKILL0_EXTERNAL_CONTROL_TRUSTED_KEYRING_SHA256` 注入。
3. 真實的 signed external-control bundle，以及
   [`production-external-control-evidence.schema.json`](../schema/production-external-control-evidence.schema.json)
   要求的每一份摘要定址附件。
4. 實際正式環境的穩定身分。
5. `api`、`dashboard`、`web` 各自不可變的已部署 registry/content digest；
   tag 與 local image ID 不符合要求。
6. 針對正式環境 read-only model mount 實際觀察並核准的 complete-tree
   model artifact digest。
7. 仍在有效期限內的安全掃描、回歸測試與正式環境演練產物；每份都必須有
   真實摘要值、觀察時間與到期時間。
8. Key 已獲該環境授權，且具備精確 `production-admission-approver` 角色的
   正式環境準入操作人員，以及該人員對最終套件產生的 Ed25519 簽章。只有
   external-control 權限的角色不符合要求。
9. 安全與發行核准，以及可實際執行的回復路徑；它必須涵蓋前一版應用程式
   映像檔、設定與相符的三儲存區備份組。

請勿把 private keys、credentials、cookies、tokens、secret-manager output、
私人拓樸匯出、含私人資料的原始記錄，或真實 keyring 傳給 AI agent。也不得
把套件、keyring、bundle、附件、私人操作人員 ID 或 trust-anchor
configuration 提交到程式庫。

## 建立受保護的套件

請在受保護的證據位置建立 `production-admission-package.json`，不得放進 Git
檢出目錄。只有在 release commit、已部署摘要值、模型摘要值、證據產物與
環境身分全部固定後，才能填入套件。其結構必須通過
[`production-admission-package.schema.json`](../schema/production-admission-package.schema.json)
驗證。

根層級 `signature` 使用 Ed25519。簽署內容是移除整個根層級 `signature`
property 後的 UTF-8 標準化 JSON 套件；keys 必須排序，separators 必須使用
`,` 與 `:`，不得加入額外空白。請把產生的 base64 signature、key ID、
操作人員 metadata、核准時間與到期時間寫入最終套件。Private key 只能由
受控簽署服務或操作人員持有的 key 管理；程式庫刻意不提供接觸 private key
的命令。

既有 external-control bundle 依其 schema 獨立簽署。其 release binding
必須與套件的 release binding 完全相同，包括 Git commit/tree、
Compose/policy/keyring、model 與所有 image digests。

## 執行準入關卡

請使用指向待準入精確 commit 的專用乾淨檢出目錄。目前的開發檢出目錄、
dirty worktree，或含未追蹤發行輸入的檢出目錄，都會以 fail closed 方式
拒絕。

```powershell
$env:SKILL0_EXTERNAL_CONTROL_TRUSTED_KEYRING_SHA256 = '<protected-runner-value>'

python tools/runtime_admission_check.py `
  C:\secure-evidence\production-primary\production-admission-package.json `
  --keyring C:\secure-keyring\skill0-production-keyring.json `
  --evidence-root C:\secure-evidence\production-primary `
  --repo-root C:\release-checkouts\skill-0
```

請透過 protected runner 的機密或設定管理功能設定環境變數；不得把真實值
貼到對話、原始碼、記錄或 shell history。命令只會輸出一個機器可讀的 JSON
物件。

- Exit `0`、`status: PASS`：提供的套件通過密碼學與結構檢查，可在既有
  dry-run-only Runtime 邊界內進入準入。
- Exit `2`、`status: FAIL`、`release_gate: BLOCKED`：不得準入，也不得重用
  套件；請依
  [`production-admission-recovery.zh-tw.md`](production-admission-recovery.zh-tw.md)
  處理。

請把套件、引用證據、trusted keyring revision/digest、驗證器輸出、runner
身分與決策封存到操作人員控制的稽核系統。對外呈現版本可以遮蔽敏感資訊，
但原始已簽署位元組必須依保存期限與存取 policy 留存。

## AI agent 無法提供的項目

AI agent 無法據實提供或製造：

- 操作人員簽章或 private signing key；
- trusted keyring 或其受保護的 trust-anchor configuration；
- 真實正式環境身分；
- 從正式環境 registry/runtime 實際觀察的已部署 image digest；
- 從正式環境實際觀察的已掛載 model artifact digest；
- 實體安全控制已存在的證明；
- 人工安全或發行核准。

Synthetic signatures 與 digests 只能存在於隔離的自動化測試，絕不得作為
正式環境準入證據。
