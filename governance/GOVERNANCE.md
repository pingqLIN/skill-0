# Skill Governance System

> skill-0 的 Skill 治理系統規範
> 
> 版本：1.0.0
> 建立日期：2026-01-27

## 1. 系統架構概覽

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Skill Governance System                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌────────────┐  │
│  │   Intake    │ → │  Security   │ → │  Equivalence│ → │  Registry  │  │
│  │   Layer     │   │   Scanner   │   │   Tester    │   │  Manager   │  │
│  └─────────────┘   └─────────────┘   └─────────────┘   └────────────┘  │
│        │                 │                  │                 │         │
│        ▼                 ▼                  ▼                 ▼         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                     Metadata Store (SQLite)                      │   │
│  │  - Provenance tracking    - Risk scores                          │   │
│  │  - License compliance     - Test results                         │   │
│  │  - Version history        - Audit logs                           │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## 2. Skill 元資料規範 (Provenance Schema)

### 2.1 必要欄位

```json
{
  "governance": {
    "skill_id": "string (UUID)",
    "name": "string",
    "version": "semver string",
    
    "provenance": {
      "source_type": "enum: github | local | url | manual",
      "source_url": "string (原始來源 URL)",
      "source_commit": "string (Git commit hash, if applicable)",
      "original_format": "enum: instructions.md | skill.md | custom",
      "original_path": "string (原始檔案路徑)",
      "fetched_at": "ISO8601 timestamp"
    },
    
    "author": {
      "name": "string",
      "email": "string (optional)",
      "url": "string (optional)",
      "organization": "string (optional)"
    },
    
    "license": {
      "spdx_id": "string (e.g., MIT, Apache-2.0, UNLICENSED)",
      "url": "string (授權文件 URL)",
      "requires_attribution": "boolean",
      "commercial_use_allowed": "boolean",
      "modification_allowed": "boolean"
    },
    
    "conversion": {
      "converted_at": "ISO8601 timestamp",
      "converter_version": "string",
      "target_format": "string",
      "modifications": ["array of modification descriptions"]
    },
    
    "security": {
      "scanned_at": "ISO8601 timestamp",
      "scanner_version": "string",
      "risk_level": "enum: safe | low | medium | high | critical | blocked",
      "risk_score": "number 0-100",
      "findings": ["array of security findings"],
      "approved_by": "string (reviewer ID, if manually approved)",
      "approved_at": "ISO8601 timestamp"
    },
    
    "equivalence": {
      "tested_at": "ISO8601 timestamp",
      "semantic_similarity": "number 0-1",
      "structure_preserved": "boolean",
      "runtime_validated": "boolean",
      "test_results": {}
    }
  }
}
```

### 2.2 風險等級定義

| Level | Score | 意義 | 動作 |
|-------|-------|------|------|
| `safe` | 0-10 | 無已知風險 | 自動核准 |
| `low` | 11-30 | 輕微疑慮，可能誤判 | 自動核准，記錄 |
| `medium` | 31-50 | 需要人工審查 | 標記待審 |
| `high` | 51-80 | 明確風險存在 | 阻擋，需核准 |
| `critical` | 81-99 | 嚴重安全威脅 | 阻擋，禁止核准 |
| `blocked` | 100 | 黑名單/已知惡意 | 永久阻擋 |

## 3. 安全風險偵測規則

### 3.1 惡意指令模式 (Patterns)

```yaml
security_patterns:
  # === HIGH RISK: 直接命令執行 ===
  - id: SEC001
    name: "Shell Command Injection"
    severity: critical
    patterns:
      - "run.*`[^`]+`"
      - "execute.*shell"
      - "system\\s*\\("
      - "subprocess\\.call"
      - "os\\.system"
      - "eval\\s*\\("
      - "exec\\s*\\("
    description: "偵測嘗試執行 shell 命令的指令"

  # === HIGH RISK: 檔案系統操作 ===
  - id: SEC002
    name: "Dangerous File Operations"
    severity: high
    patterns:
      - "rm\\s+-rf"
      - "del\\s+/[fqs]"
      - "format\\s+[a-z]:"
      - "mkfs\\."
      - "dd\\s+if="
      - "> /dev/"
      - "truncate\\s+-s\\s*0"
    description: "偵測危險的檔案刪除或覆寫操作"

  # === MEDIUM RISK: 敏感資料存取 ===
  - id: SEC003
    name: "Credential/Secret Access"
    severity: medium
    patterns:
      - "password"
      - "api[_-]?key"
      - "secret[_-]?key"
      - "private[_-]?key"
      - "access[_-]?token"
      - "\\.env"
      - "credentials"
      - "ssh[_-]?key"
    description: "偵測嘗試存取敏感資訊的指令"
    
  # === MEDIUM RISK: 網路操作 ===
  - id: SEC004
    name: "Suspicious Network Operations"
    severity: medium
    patterns:
      - "curl.*\\|.*sh"
      - "wget.*\\|.*bash"
      - "nc\\s+-[el]"
      - "reverse.*shell"
      - "bind.*shell"
      - "/dev/tcp/"
    description: "偵測可疑的網路下載或連線"

  # === LOW RISK: Prompt Injection ===
  - id: SEC005
    name: "Prompt Injection Attempt"
    severity: medium
    patterns:
      - "ignore.*previous.*instructions"
      - "disregard.*above"
      - "forget.*everything"
      - "new.*persona"
      - "you.*are.*now"
      - "act.*as.*if"
      - "jailbreak"
      - "DAN\\s*mode"
    description: "偵測 prompt injection 攻擊模式"

  # === LOW RISK: 權限提升 ===
  - id: SEC006
    name: "Privilege Escalation"
    severity: high
    patterns:
      - "sudo\\s+"
      - "su\\s+-"
      - "runas\\s+/user"
      - "chmod\\s+[0-7]*777"
      - "chmod\\s+\\+s"
      - "setuid"
    description: "偵測權限提升嘗試"

  # === INFO: 資料外洩風險 ===
  - id: SEC007
    name: "Data Exfiltration Risk"
    severity: low
    patterns:
      - "upload.*to"
      - "send.*to.*server"
      - "post.*data"
      - "exfil"
      - "base64.*encode.*send"
    description: "偵測可能的資料外洩行為"
```

### 3.2 黑名單來源

```yaml
blocked_sources:
  - pattern: "*.malware.example.com"
    reason: "Known malicious domain"
  - pattern: "user/malicious-repo"
    reason: "Reported malicious repository"
```

### 3.3 授權白名單

```yaml
allowed_licenses:
  permissive:
    - MIT
    - Apache-2.0
    - BSD-2-Clause
    - BSD-3-Clause
    - ISC
    - Unlicense
    - CC0-1.0
    - WTFPL
  
  copyleft_weak:
    - LGPL-2.1
    - LGPL-3.0
    - MPL-2.0
  
  copyleft_strong:  # 需額外審查
    - GPL-2.0
    - GPL-3.0
    - AGPL-3.0
  
  restricted:  # 禁止使用
    - BUSL-1.1
    - CC-BY-NC-*
    - Proprietary
```

## 4. 等價性測試框架

### 4.1 測試維度

| 維度 | 測試方法 | 通過標準 |
|------|----------|----------|
| **Metadata 完整性** | Schema validation | 必要欄位 100% 存在 |
| **語意相似度** | Embedding cosine similarity | ≥ 0.85 |
| **結構保留** | AST/Heading 結構比對 | ≥ 0.90 |
| **關鍵字保留** | TF-IDF 關鍵字比對 | ≥ 0.80 |
| **Runtime 行為** | Trigger 測試 | 相同輸入觸發相同 skill |

### 4.2 語意相似度計算

```python
def compute_semantic_similarity(original: str, converted: str) -> float:
    """
    使用 sentence-transformers 計算語意相似度
    """
    from sentence_transformers import SentenceTransformer
    import numpy as np
    
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    emb_original = model.encode(original, normalize_embeddings=True)
    emb_converted = model.encode(converted, normalize_embeddings=True)
    
    similarity = np.dot(emb_original, emb_converted)
    return float(similarity)
```

### 4.3 Runtime 測試

```python
def test_runtime_equivalence(skill_name: str, test_prompts: list[str]) -> dict:
    """
    測試轉換前後 skill 在相同 prompt 下的觸發行為
    
    Returns:
        {
            "prompts_tested": int,
            "triggers_matched": int,
            "match_rate": float,
            "failures": [...]
        }
    """
    pass  # Implementation in skill_tester.py
```

## 5. 審計日誌 (Audit Trail)

所有操作都應記錄：

```json
{
  "audit_log": {
    "event_id": "UUID",
    "timestamp": "ISO8601",
    "event_type": "enum: import | convert | scan | approve | reject | install | uninstall",
    "skill_id": "string",
    "actor": "string (user or system)",
    "details": {},
    "previous_state": {},
    "new_state": {}
  }
}
```

## 6. 工作流程

### 6.1 Skill 導入流程

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  Import  │ ──▶ │  Scan    │ ──▶ │  Convert │ ──▶ │  Test    │
│  Source  │     │  Security│     │  Format  │     │ Equiv.   │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
                      │                                  │
                      ▼                                  ▼
                 ┌──────────┐                     ┌──────────┐
                 │  BLOCK   │                     │  PASS?   │
                 │ (if risk)│                     │          │
                 └──────────┘                     └────┬─────┘
                                                      │
                      ┌───────────────────────────────┼───────────────────┐
                      ▼                               ▼                   ▼
                 ┌──────────┐                   ┌──────────┐        ┌──────────┐
                 │  REVIEW  │                   │ REGISTER │        │  REJECT  │
                 │ (if med) │                   │ (if pass)│        │ (if fail)│
                 └──────────┘                   └──────────┘        └──────────┘
```

### 6.2 CLI 命令

```bash
# 完整導入流程
skill-0 import <source> [--auto-approve] [--skip-tests]

# 僅掃描安全
skill-0 scan <skill_path>

# 僅測試等價性
skill-0 test <original_path> <converted_path>

# 審查待核准
skill-0 review list
skill-0 review approve <skill_id> --reason "..."
skill-0 review reject <skill_id> --reason "..."

# 查詢元資料
skill-0 info <skill_name>
skill-0 audit <skill_name>
```

## 7. 檔案結構

```
skill-0/
├── governance/
│   ├── schema/
│   │   ├── governance.schema.json     # 元資料 JSON Schema
│   │   └── security-rules.yaml        # 安全規則定義
│   ├── db/
│   │   └── governance.db              # SQLite 資料庫
│   └── config/
│       ├── allowed-licenses.yaml      # 授權白名單
│       └── blocked-sources.yaml       # 黑名單
├── tools/
│   ├── skill_converter.py             # 格式轉換 (已存在)
│   ├── skill_installer.py             # 安裝管理 (已存在)
│   ├── skill_scanner.py               # 安全掃描 (新增)
│   ├── skill_tester.py                # 等價測試 (新增)
│   └── skill_governance.py            # 治理主程式 (新增)
└── tests/
    └── governance/
        ├── test_scanner.py
        └── test_equivalence.py
```

## 8. 版本紀錄

| 版本 | 日期 | 變更 |
|------|------|------|
| 1.0.0 | 2026-01-27 | 初始規範 |
