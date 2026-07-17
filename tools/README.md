# Skill-0 分析工具

本目錄包含用於路由、分析、驗證與治理 Skills 結構的工具。

## 工具清單

### intent_router.py - Top-down 路由入口

依照目標與任務階段，先決定要走哪一條 Skill-0 工作路徑，再回推建議命令。

目前版本是 table-driven 的 operator starter，目的在於先把既有 search / parse / analyze / govern / compare / validate 路徑收斂成單一入口，而不是宣稱它已經是完整策略引擎。

```bash
# 從自由文字推斷目標
.venv/bin/python tools/intent_router.py --goal compare --phase triage --query "overlapping skills"

# 明確指定治理目標
.venv/bin/python tools/intent_router.py --goal govern --phase review

# 以 JSON 輸出 machine-readable handoff
.venv/bin/python tools/intent_router.py --goal discover --phase intake --query "document processing" --format json
```

**適用場景：**
- 先決定現在應該 search / ingest / analyze / govern / compare / validate 哪條路徑
- 避免從工具清單自下而上反推流程
- 作為 `skill-0` 的 top-down、intent-driven meta-router

### report_db_identity_drift.py - DB identity drift 報告

只讀比對 `parsed/`、`skills.db`、`governance/db/governance.db` 的技能身份投影，協助 release / push 前確認 runtime DB 是否缺失、過期或與 canonical parsed corpus 不一致。

```bash
# Public checkout 或乾淨 clone：允許 runtime DB 缺失，但保留 warning
.venv/bin/python tools/report_db_identity_drift.py --allow-missing-db

# Local runtime / release rehearsal：DB 缺失或 drift 都回傳非 0 exit code
.venv/bin/python tools/report_db_identity_drift.py

# Machine-readable evidence
.venv/bin/python tools/report_db_identity_drift.py --format json --allow-missing-db
```

**適用場景：**
- `skills.db` / `governance.db` 已從 public tracked tree 移除後，確認 missing DB 是預期狀態還是 release blocker
- 檢查 vector DB 的 `raw_json.meta.skill_id` 是否落後於 `parsed/`
- 檢查 governance rows 是否缺 `current_revision_id` 或 current revision checksum
- 在 backup/restore、re-index、release rehearsal 後產生 operator-facing evidence

### runtime_asset_index_maintenance.py - Runtime Asset Index 維護

對既有 derived Index 執行 fail-closed schema preflight、read-only migration
preview、SQLite backup、checksum migration、兩次 incremental index 與 doctor
evidence。它不建立或批准 Governance authority，也不接受只有 `sample` table 的
資料庫作為 Index。

```powershell
# 唯讀預覽
.\.venv\Scripts\python.exe tools\runtime_asset_index_maintenance.py `
  --index-db skills.db preview

# 建立 verified backup 後套用 migration
.\.venv\Scripts\python.exe tools\runtime_asset_index_maintenance.py `
  --index-db skills.db apply --backup backups\skills-pre-p0-1.db

# 執行兩次 incremental index，第二次必須為 no-op
.\.venv\Scripts\python.exe tools\runtime_asset_index_maintenance.py `
  --index-db skills.db --output audit\p0-1\index-evidence.json index `
  --parsed-dir parsed --governance-db governance\db\governance.db `
  --smoke-query "document processing"
```

若 embedding model 不是可雜湊的本機目錄，`index` 必須提供不可變的
`--model-version`。Backup 路徑不得已存在，避免覆寫復原點。
預設 `index` 只有在 doctor 為 `healthy` 時回傳成功；public checkout 若只是建立
derived Index evidence，必須明確加上 `--allow-nonhealthy-evidence`，輸出仍會標記
`accepted=false` 與 `rehearsal_only=true`，不得當成 operator acceptance。

### analyzer.py - 結構統計分析

分析已解析的 skills，產生統計報告。

```bash
# 基本用法
python tools/analyzer.py

# 指定輸入目錄和輸出路徑
python tools/analyzer.py -p parsed -o analysis/report.json

# 同時產生文字報告
python tools/analyzer.py -t
```

**輸出內容：**
- 元素總數統計 (action/rule/directive)
- Action 類型分布
- Directive 類型分布
- 各 Skill 摘要
- 常見執行序列模式

### pattern_extractor.py - 模式提取

從多個 skills 中歸納共通模式，建立模式庫。

```bash
# 基本用法
python tools/pattern_extractor.py

# 指定輸出路徑
python tools/pattern_extractor.py -o analysis/patterns.json
```

**提取的模式類型：**
- `action_combination` - Action 類型的常見組合
- `directive_usage` - Directive 類型的使用模式
- `structure` - 元素比例結構模式
- `keyword` - 描述文字的關鍵字模式

## 輸出檔案

分析結果儲存在 `analysis/` 目錄：

```
analysis/
├── report.json      # 結構統計報告
├── report.txt       # 文字版報告 (可選)
└── patterns.json    # 歸納出的模式庫
```

## 未來擴展

### 階段 2: 語義相似度分析
- 加入向量索引 (sqlite-vec)
- 語義搜尋相似元素
- 自動聚類

### 階段 3: LLM 輔助分析
- 模式歸納
- 新 Skill 生成建議
- 缺口分析
