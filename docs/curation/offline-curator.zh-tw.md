# Offline Curator P2

- 狀態：`Experimental / P2 proposal-only boundary`
- 文件權威：`無語系後綴的英文版為權威文件；本文件為繁體中文閱讀版。`

## 用途

Offline Curator 會把已驗證、已去敏的 execution trajectory 與被檢索到的 Skill
revision snapshot，轉換成供人工審查的 draft proposal。它是 Skill-0 P1 策展契約
與未來 P3 governance workflow 之間的橋接層。

流程分成兩個明確步驟：

```text
trajectory + retrieved skill context
  -> 準備 deterministic prompt package
  -> offline/manual Curator 回傳已綁定的 structured decision
  -> 驗證 current revision 與選用的 candidate artifact
  -> 產生 dry draft curation proposal
```

## 已驗證邊界

- CLI 不會呼叫 model provider 或網路服務。
- Curator 不得寫入 `parsed/`、`converted-skills/`、governance data、Schema、
  source package、API 或 dashboard。
- Repository 內只允許寫入已忽略的 `output/curation/`；未指定 `--output` 時，
  JSON 只會輸出到 stdout。
- Output file 僅能新建，不能覆寫既存 artifact。
- 每個 decision 都必須綁定完全相同的 prompt package checksum。
- Prompt 準備後若 target revision 已改變，update/delete 必須 fail closed。
- Insert/update 必須提供 UTF-8 candidate artifact；delete 禁止提供。
- Trajectory、context、decision 或 candidate 含敏感內容時必須拒絕。
- 產生的 proposal 一律保持 `governance.state = draft`。

## 契約與資源

| 用途 | 路徑 |
|---|---|
| Retrieved revision snapshot | `schema/offline-curator-context.schema.json` |
| Structured Curator decision | `schema/offline-curator-decision.schema.json` |
| Draft proposal output | `schema/curation-proposal.schema.json` |
| 固定設定 | `curation/manifests/offline-curator-v1.json` |
| Prompt template | `curation/prompts/offline-curator-v1.md` |

Manifest 固定 prompt checksum、operation set、Schema、fail-closed checks 與
`dry_proposal_only` output mode。Prompt package 在計算雜湊前會正規化換行，因此
Windows 與 POSIX checkout 能得到穩定識別。

## 準備 Prompt Package

```powershell
python tools/offline_curator.py prepare `
  --trajectory tests/fixtures/curation_contracts/valid/execution-trajectory.json `
  --skill-context tests/fixtures/offline_curator/skill-context.json `
  --model-id local-offline-model `
  --output output/curation/prompt-package.json
```

Skill context 必須與 trajectory 中 retrieved skill 的順序及 revision ID 完全一致；
命令會先驗證兩份輸入，再產生 package。

## 建立 Dry Proposal

Offline 或人工 Curator 回傳符合 `offline-curator-decision.schema.json` 的 JSON。
其中 `prompt_package_checksum` 必須等於已準備 package 的 checksum。Insert/update
另以獨立本機檔案提供 candidate artifact。

```powershell
python tools/offline_curator.py propose `
  --prompt-package output/curation/prompt-package.json `
  --decision path/to/offline-decision.json `
  --current-context path/to/current-skill-context.json `
  --candidate-artifact path/to/candidate/SKILL.md `
  --output output/curation/draft-proposal.json
```

Delete decision 不提供 `--candidate-artifact`。P2 不覆寫既存檔案，因此每次執行
都要使用新的 output filename。

## 未知與延後項目

P2 不呼叫 LLM、不判定 proposal 品質、不執行 candidate ARD analysis、不掃描完整
repository 的 duplicate/conflict、不保存 proposal、不要求 approval、不建立 revision，
也不修改 SkillRepo。因此 ARD、duplicate、conflict validation 維持 `not_run`。

上述能力屬於後續 review gate；任何 P2 artifact 都不得被解讀為已核准或已 promotion。
