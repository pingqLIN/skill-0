# 正式環境準入 `BLOCKED` 復原流程

本操作手冊定義 Runtime Asset Production Admission v1 嘗試回傳 `FAIL` /
`BLOCKED` 後的重新進入流程。英文版
[`production-admission-recovery.md`](production-admission-recovery.md) 具規範
效力；本文件是繁體中文對照版本。

`BLOCKED` 是單次準入嘗試的安全終止決策。它不是降低驗證器強度、重用過期
證據、修改已簽署套件或強制部署的指令。

## 立即處置

1. 不得部署、推進，或繼續使用遭封鎖的套件。
2. 保留精確的套件位元組、引用證據、驗證器 JSON 結果、keyring
   revision/digest、runner 身分與時間戳記。
3. 在操作人員稽核系統記錄失敗的 `admission_id`、`release_id`、reason
   codes 與決策。
4. 若已經部署，請停止後續推進，並執行已核准的回復或圍堵程序。不得刪除
   受影響的儲存區或唯一的鑑識副本。

## 分類封鎖原因

| 檢查或原因類別 | 必要處置 |
|---|---|
| `schema_validation`, `input_loading` | 依權威來源記錄重建套件；不得原地修改已簽署套件。 |
| `keyring_trust_anchor`, `operator_signature`, `revocation_state` | 聯絡 keyring 或簽署權限管理者，經受保護流程更換或重新授權；不得繞過或覆寫信任。 |
| `operator_authorization` | 改由 keyring 中具備精確 `production-admission-approver` 角色，且獲目標環境授權的操作人員重新簽署。 |
| `commit_binding`, `release_binding` | 回到精確、乾淨的發行版本檢出目錄。若觀察到的版本不同，必須從預定 commit 重新建置與部署。 |
| `image_digest_binding`, `model_artifact_binding` | 重新觀察已部署的不可變映像檔或 complete-tree 模型摘要值；修正部署，或建立新的發行套件。 |
| `evidence_references`, `evidence_freshness` | 從權威 scanner、測試或演練系統收集新產物，計算摘要值，並填入真實觀察與到期時間。 |
| `external_control_evidence` | 由獲授權操作人員針對精確發行版本與環境，建立最新且完整的 external-control bundle 與附件。 |
| `verifier_execution` | 將結果視為不確定。修復驗證器環境後重新執行，不得推論成功。 |

驗證身分、授權、權限、policy 或 protected-runner 失敗，必須交由負責的人員
處理；不得以降低控制強度的方式重試。

## 重新進入程序

1. 從實際觀察該證據的系統，收集每一份缺少或替代證據。
2. 確認預定的 Git commit/tree、正式環境身分、已部署的
   `api`/`dashboard`/`web` digests、model digest、Compose/policy digests
   與 trusted keyring digest。
3. 對缺少、已到期、遭撤銷或綁定到不同發行版本的證據，重新執行基礎安全
   掃描、回歸測試、演練、external control 與程式庫關卡。
4. 使用新的 `admission_id` 建立新套件。不得編輯、覆寫或重用遭封鎖套件。
5. 只有在所有替代證據都已固定且仍在有效期限內後，才能取得新的操作人員
   核准與簽章。
6. 從精確、乾淨的發行版本檢出目錄執行
   `tools/runtime_admission_check.py`。
7. 把新的驗證器結果記錄為獨立的準入嘗試。
8. 只有 exit `0`、`status: PASS` 且沒有失敗或不確定的檢查時才能準入。
   否則必須記錄拒絕；只有在原因改變後，才能從步驟 1 重試。

僅有收件確認、逾時、缺少輸出、不完整輸出或無法取得審查，都不是核准。

## 稽核歷史

每次嘗試都必須保留僅附加的歷史鏈：

- admission 與 release IDs；
- source commit/tree 與所有發行摘要值；
- 套件摘要值與 signature/key ID；
- evidence IDs、paths 或受保護物件 IDs，以及摘要值；
- keyring revision/digest 與撤銷狀態；
- verifier version/commit、輸出、exit code 與執行時間戳記；
- 依適用隱私 policy 保存的操作人員決策、原因與 actor identity；
- 替代或回復與較早嘗試的關係。

不得刪除或改寫遭拒絕的嘗試，讓後續嘗試看起來像原始核准。遮蔽敏感資訊
後的報告副本，仍必須可追溯至所保存的已簽署位元組。

## 遭封鎖版本已部署時的回復

請使用
[`runtime-production-operations.md`](runtime-production-operations.md) 定義的
操作人員核准回復程序：

1. 停止三個儲存區的寫入程序；
2. 保留損壞或可疑檔案，以供鑑識復原；
3. 還原一組相符的 `skills.db`、`governance.db` 與 `runtime.db` 備份；
4. 還原相符的前一版應用程式映像檔與設定；
5. 依文件順序啟動 Dashboard API、Core API 與 web；
6. 使用目前的備份要求重新執行 production doctor；
7. 在重新開放準入邊界前，建立新的受治理 dry run。

不得只降級 Runtime schema，卻保留較新的 event data。若回復版本無法解讀
目前的 governance revisions 或 HITL deadlines，Runtime 必須保持停用，並
保留儲存區以進行向前復原。
