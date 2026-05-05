# Skill-0 深度研究建議開發計畫與執行紀錄

**日期：** 2026-05-04  
**來源文件：** `deep-research-report (1).md`  
**範圍：** 本文件只擷取並執行 `skill-0` repo 本體可落地項目；`skill-0-GUI` 相關建議列為跨 repo 後續。

## 擷取建議

深度研究報告對 `skill-0` 本體提出兩個低風險、高價值的短期修補：

1. `api/main.py` 登入驗證應避免直接使用一般字串相等比較，改用 constant-time credential comparison。
2. `vector_db/vector_store.py` 的 `insert_skills_batch()` 不應逐筆呼叫會 commit 的 `insert_skill()`，應改為單一 transaction，避免索引重建時出現不必要的 commit 成本與 partial write 風險。

報告中的 `/api/llm-settings`、remote import timeout/size cap、draft persistence、GUI coverage gate、GUI repo 命名等項目屬於 `skill-0-GUI` 或跨 repo 工作，本輪不直接修改。

## 決策點

| 決策 | 結論 | 理由 | 審查 |
|---|---|---|---|
| 本輪是否修改 GUI runtime hardening | 不修改 | 目前 workspace 是 `skill-0`，直接修改 GUI repo 會跨出本輪 repo 邊界 | 列為後續 |
| 登入比較作法 | 以 SHA-256 固定長度 digest 後使用 `hmac.compare_digest` | 避免一般字串比較與長度差異造成的 timing surface；同時保留既有 env-based auth 介面 | 外部 `codex exec` review：no blocking findings |
| Batch insert transaction 作法 | 抽出不 commit 的 `_upsert_skill()`，由 public insert methods 管理 transaction | 單筆 insert 維持既有語意；批次 insert 可原子 commit/rollback | 外部 `codex exec` review：no blocking findings |

## 已完成項目

- `api/main.py`
  - 新增固定長度 digest helper。
  - `validate_login_credentials()` 會分別比較 username 與 password，再合併結果，避免 short-circuit 跳過 password 比較。
- `vector_db/vector_store.py`
  - 新增 `_upsert_skill()` 作為不 commit 的內部 upsert。
  - `insert_skill()` 改為單筆 transaction。
  - `insert_skills_batch()` 改為單一 transaction，並檢查 skills/embeddings 長度一致。
  - 新增 embedding shape validation，讓錯誤輸入在寫入前失敗。
- 測試
  - 補 `validate_login_credentials()` 的 constant-time comparison 行為測試。
  - 補 batch insert 成功、輸入長度不一致、壞 embedding rollback、單筆 rollback、embedding row 存在等 regression 測試。

## 驗證

- `.venv/bin/python -m pytest tests/test_api_security.py tests/integration/test_auth_flow.py tests/test_vector_store.py tests/test_vector_store_transactions.py -q`
  - 41 passed
- `.venv/bin/python -m pytest tests skill-0-dashboard/apps/api/tests -q`
  - 236 passed
- `.venv/bin/python -m flake8 api/main.py vector_db/vector_store.py tests/test_api_security.py tests/test_vector_store.py tests/test_vector_store_transactions.py --count --select=E9,F63,F7,F82 --show-source --statistics`
  - 0
- `git diff --check` for tracked edits and no-index checks for new test files
  - passed

## 外部審查

使用本機非互動外部代理路徑：

```bash
codex exec --ephemeral -s read-only -C /home/miles/dev2/projects/skill-0 "External read-only code review..."
```

審查結論：

- Blocking findings: none.
- 變更符合報告中 `skill-0` 本體建議。
- 測試覆蓋主要 regression 風險。
- 外部審查代理自己的 read-only sandbox 無可寫 temp directory，因此它無法自行啟動 pytest；主執行環境已完成上述測試。

## 後續待辦

- 在 `skill-0-GUI` repo 實作 runtime config endpoint auth、remote import timeout/size cap、draft persistence privacy controls。
- 補正式 deployment profile matrix、draft retention policy、shared contract versioning policy。
- 規劃 vector index rebuild benchmark，以量化 batch transaction 的實際收益。
