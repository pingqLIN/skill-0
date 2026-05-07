# Skill-0 Governance Hardening Plan

更新日期：2026-05-07

## 目的

本計畫將 issue-log 中的治理與安全問題轉成可執行的強化項目，聚焦於風險可追溯、人類審查、事件回饋與授權不確定性。

## 核心風險

| 風險 | 現況問題 | 強化方向 |
|---|---|---|
| Regex scan 覆蓋不足 | 只能捕捉表層字串風險 | 增加語義風險分類與人工審查提示 |
| 自動核准過早 | risk score 可能被當成最終判定 | 高風險項目必須進 review queue |
| 授權不確定 | Skill 衍生作品邊界不清 | 保存來源、license、review note |
| 事件無法回流 | 部署後問題不會更新規則 | 建立 incident-to-rule feedback |
| mutable row 風險 | skill rows 不應是治理 source of truth | 保持 revision-aware governance |

## 強化項目

### G1：語義風險分類

新增或明確化下列風險類別：

- Indirect prompt injection。
- Sensitive data exfiltration instruction。
- Unsafe tool permission escalation。
- Ambiguous destructive operation。
- License or provenance uncertainty。
- Cross-runtime dependency ambiguity。

驗收：

- 每個類別有定義、例子、review action。
- scanner 或 reviewer UI 至少能保存該風險分類。

### G2：人類審查門檻

規則：

- 高風險或不確定授權的 Skill 不可自動核准。
- risk score 只能作為 triage signal，不是最終治理決策。
- reviewer 必須能記錄 reason 與後續 action。

驗收：

- review 記錄能追到 skill revision。
- 自動 scan 結果與人工判定可並存。

### G3：事件回饋

建立事件回饋欄位或流程：

1. 事件來源：runtime incident、review finding、benchmark failure、user report。
2. 對應 Skill revision。
3. 對應 risk rule 或 parser failure 類別。
4. 修復狀態：open、triaged、patched、verified。

驗收：

- 至少一個事件可連回 governance revision 與後續修復 commit。

### G4：授權與來源紀錄

對 imported corpus 補強：

- source URL 或來源路徑。
- license 或 unknown 狀態。
- 是否允許 redistribution。
- 是否只可做 local analysis。

驗收：

- unknown license 不被描述為 production-ready。
- 文件與 dashboard 不把 imported corpus 授權狀態過度宣稱。

## 實作順序

1. 文件先定義 risk taxonomy 與 review gate。
2. 補 API/schema 層的欄位前，先確認 dashboard consumption path。
3. 為 scanner 補最低限度 regression fixtures。
4. 將 incident feedback 接到治理 revision，而不是 mutable skill row。

## 驗證入口

文件階段：

```bash
git diff --check
.venv/bin/python tools/check_doc_status_markers.py
.venv/bin/python tools/check_shared_docs.py
```

實作階段：

```bash
.venv/bin/python -m pytest tests/test_api_security.py tests/test_doc_checks.py -q
.venv/bin/python -m pytest skill-0-dashboard/apps/api/tests -q
```

若任何命令缺少必要 program 或 dependency，依 Test Stage Guard 暫停並回報。
