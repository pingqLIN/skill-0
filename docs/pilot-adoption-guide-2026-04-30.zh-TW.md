# Skill-0 Pilot Adoption Guide

日期：`2026-04-30`
Repo：`<repo-root>`
狀態：`current pilot guide`

---

## 1. 目的

本文件提供一條 30 分鐘內可完成的 Skill-0 pilot 路徑，讓 skill registry maintainer、AI ops reviewer、或 agent platform team 可以在不承諾 production deployment 的前提下驗證三件事：

1. `parsed/` sidecar contract 是否能被 schema 驗證。
2. runtime DB 是否存在、缺失或與 parsed corpus 發生 identity drift。
3. operator 是否能從 goal-first router 取得下一步命令，而不是從工具清單反推流程。

這不是 strict equivalence benchmark，也不是 production release rehearsal。它是導入前的低風險證據包。

---

## 2. 前置條件

```bash
source .venv/bin/activate
.venv/bin/python --version
nvm use || nvm install 20.19.0
```

Public checkout 預期不包含 `skills.db` 與 `governance/db/governance.db`。若這兩個 DB 缺失，pilot 的第一步應先確認這是預期狀態，而不是直接把 SQLite error 當成專案故障。

---

## 3. Phase A：乾淨 Checkout 驗證

```bash
.venv/bin/python tools/validate_skill_schema.py parsed
.venv/bin/python tools/report_db_identity_drift.py --allow-missing-db --format json
.venv/bin/python tools/intent_router.py --goal validate --phase review --format json
```

接受條件：

1. Schema validation 顯示 `196 passed, 0 failed`。
2. DB identity drift report 在 public checkout 顯示 `status=warning`，並明確列出 missing runtime DB。
3. Intent router 的 `validate/review` 路徑包含 schema validation、DB identity drift report、focused regression 與 evaluation command。

---

## 4. Phase B：建立 Local Runtime 搜尋 DB

只有需要展示 semantic search 時才執行本階段。

```bash
.venv/bin/python -m vector_db.search --db skills.db --parsed-dir parsed index
.venv/bin/python tools/report_db_identity_drift.py --skills-db skills.db --allow-missing-db
.venv/bin/python -m vector_db.search --db skills.db stats
.venv/bin/python -m vector_db.search --db skills.db search "document processing"
```

接受條件：

1. `skills.db` 能由 `parsed/` 重建，不需要 tracked DB artifact。
2. Drift report 不應列出 vector rows with missing `raw_json.meta.skill_id`。
3. Search command 能回傳與 query 相關的 skill list。

若本機 embedding model 尚未下載，這一步可能受網路與模型 cache 影響；不要把 cold-start 下載時間當成 parser 品質指標。

---

## 5. Phase C：Governance Pilot

只有需要展示 reviewer workflow 時才執行本階段。

```bash
.venv/bin/python tools/skill_governance.py list
.venv/bin/python tools/batch_security_scan.py
.venv/bin/python tools/skill_governance.py review list
.venv/bin/python tools/report_db_identity_drift.py
```

接受條件：

1. Governance command 使用 `governance/db/governance.db` 的 revision-aware storage。
2. Drift report 不應列出 missing current revision；若列出，pilot 報告要把它列為治理資料初始化或 migration 缺口。
3. Reviewer-facing 狀態應能看到 pending / approved / rejected / blocked 等 workflow state。

---

## 6. Pilot Handoff Evidence

Pilot 結束時至少保留以下 evidence：

```bash
.venv/bin/python tools/validate_skill_schema.py parsed
.venv/bin/python tools/report_db_identity_drift.py --allow-missing-db --format json
.venv/bin/python tools/intent_router.py --goal validate --phase review --format json
.venv/bin/python -m pytest tests/test_intent_router.py tests/test_db_identity_drift_report.py -q
git status --short
```

若建立了 local runtime DB，另外附上：

```bash
.venv/bin/python -m vector_db.search --db skills.db stats
.venv/bin/python tools/report_db_identity_drift.py --skills-db skills.db --allow-missing-db --format json
```

---

## 7. 不做事項

本 pilot 不做：

1. 大量新增 skill corpus。
2. production compose up。
3. secret rotation。
4. strict equivalence 宣稱。
5. 將 local generated DB 加回 git tracked tree。

