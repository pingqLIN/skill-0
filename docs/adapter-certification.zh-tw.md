# Adapter Certification

> 本文件是 [adapter-certification.md](adapter-certification.md) 的繁體中文參考版本；英文原文為權威版本。

## 目前判定

`skill0.local-pdf-filesystem` 是目前唯一 certification candidate。隔離的 technical probes 已通過，但 production approval 刻意維持 `pending_human_approval`。

本次 certification 沒有簽發 production approval record。`/api/runs` 仍只接受 simulation adapter 與 `dry_run=true`；本批次沒有暴露真實 adapter，也沒有授權外部寫入。

## 認證範圍

候選只涵蓋 canonical skill `claude__anthropic__pdf`、action `a_006`、operation `create_pdf` 的本機 filesystem side-effect boundary。

| 控制項 | Contract | Technical evidence |
|---|---|---|
| Credential 與最小權限 | 不接受 secret。專用 OS process identity 只能在指定 output root 建檔、寫入 SQLite receipt store，並把自己擁有的 artifact 移至 root 內的 `.del`。禁止 network、subprocess、overwrite、path traversal 與 secret access。 | Constructor 沒有 credential input；path traversal 被拒絕；sandbox 外沒有觀察到副作用。Production OS identity 與 ACL 證據仍是人工核准前置條件。 |
| Idempotency | Runtime ledger 先 claim primary key，再明確傳給 adapter。Adapter 只保存 key 的 SHA-256 digest。同 key、同 request 回傳原結果且不重複產生副作用；同 key、不同 request 直接 conflict。 | Replay 只產生一個 PDF；conflicting replay 不改變原始 digest。 |
| Reconciliation | 唯讀 probe 比較 SQLite claim、root-local receipt marker、resource identity 與 content digest。狀態為 `not_found`、`applied`、`compensated`、`diverged` 或 `unknown`；`unknown` 絕不允許自動 retry。 | 在檔案 commit 後、terminal DB receipt 前注入 timeout，probe 能判定 `applied`、只找到一個 effect，且 retry 次數為零。 |
| Compensation | Adapter 只把自己擁有的 artifact 與 receipt marker 移入 `.del`，不永久刪除；compensation 使用獨立 idempotency key。 | Evidence 含 original resource ID、content digest、quarantine resource ID、compensation-key digest 與完成時間；重複 compensation 回傳原 evidence。 |
| Rate limit | SQLite fixed window，每 60 秒最多兩個新 effect，同時最多一個 call；replay 不占新的 effect slot。 | 第三個新 effect 會被拒絕並回傳 `retry_after_seconds`，Runtime 會把它記為已證明 pre-effect 的 `ACTION_FAILED`，而非 ambiguous outcome；window 後可成功。任何限額異動都會改變 manifest digest，必須重新認證與核准。 |
| Production approval | Default deny。Approval 綁定 adapter ID/version、source artifact digest、manifest digest、certification evidence digest、精確 environment、精確 operations、reviewer 與 expiry。 | 精確簽署 scope 可通過；operation drift 與過期會被拒絕；attestation 會納入 keyed execution basis。 |

## Compensation 邊界

目前 canonical PDF decomposition 沒有獨立的 delete 或 rollback Action。因此 adapter 的 compensation primitive 雖已完成技術認證，Runtime contract 仍必須使用 `human_intervention`。在 reviewed canonical compensation Action 與 cross-reference 出現前，不得把它宣稱為自動 ARD compensation。

## 產生 evidence

在 repo root 執行隔離 probes：

```powershell
python tools\certify_adapter.py --manifest adapters\local-pdf-filesystem\adapter-certification.json --output audit\adapter-certification-local-pdf.json
```

此命令只使用暫存本機目錄，不使用 external credential 與 network。輸出被 Git ignore。即使通過，文件仍會標示 `pending_human_approval`。

## 人工 production approval gate

Approval 是 L3 runtime gate。針對目標 environment 簽發前，operator 必須逐項確認：

1. Certification evidence 為 `passed`，且七類 required probes 全部存在。
2. Live adapter artifact 與 manifest digest 與 evidence 一致。
3. 專用 OS identity 與 filesystem ACL 把 adapter 限制在精確 output/state roots。
4. SQLite receipt store 可持久化、有備份，且只有 runtime identity 與 operator 可寫。
5. Output quota、`.del` retention、monitoring、incident ownership 與 reconciliation escalation 已文件化。
6. Environment、allowed operation、reviewer identity 與 expiry 都是明確的人工作業決定。
7. Approval signing key 與 JWT、Runtime binding key 及其他 application key 分離；只由目標 secret manager 注入，絕不印出、記錄或 commit。

完成 review 後，operator 才可簽發單一 environment-specific record：

```powershell
python tools\adapter_approval.py issue --manifest adapters\local-pdf-filesystem\adapter-certification.json --evidence audit\adapter-certification-local-pdf.json --environment <environment-name> --approved-by <reviewer-id> --expires-at <ISO-8601-timestamp> --output <pre-provisioned-approval-path>
```

執行前，process 必須已從目標 secret manager 取得 `SKILL0_ADAPTER_APPROVAL_KEY`。工具拒絕少於 32 字元的 key，也拒絕覆寫既有 approval file。

以 live manifest 驗證 approval：

```powershell
python tools\adapter_approval.py verify --approval <approval-path> --manifest adapters\local-pdf-filesystem\adapter-certification.json --environment <environment-name>
```

建立簽署的 replacement revocation，且不覆寫原 approval record：

```powershell
python tools\adapter_approval.py revoke --approval <approval-path> --revoked-by <reviewer-id> --output <pre-provisioned-revocation-path>
```

移除 runtime 設定中的 approval path、改為設定簽署的 `revoked` replacement、到期、artifact drift、manifest drift、operation drift 或 environment drift，都必須 fail closed。Rollback 時應保留 receipts 與 `.del` artifacts，避免遺失 reconciliation evidence。

## 尚未跨越的 production 邊界

只有 approval record 不會讓 `/api/runs` 載入此 adapter。後續仍需一個另行核准的 loader batch：配置專用 identity 與 roots、把 approval gate 注入 orchestrator、保留既有 HITL boundary，並驗證 adapter state store 的 backup/restart 行為。在該批次通過前，production execution 仍為 disabled。
