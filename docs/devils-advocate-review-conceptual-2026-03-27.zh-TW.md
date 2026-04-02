# Skill-0 Devil's Advocate 審查報告

日期：`2026-03-27`

範圍：
- `skill-0` 的概念定位 / 理論定位
- canonical contract 穩定性
- governance 模型有效性
- equivalence 宣稱強度

本文件刻意採取反方、挑戰性視角。目的不是讚揚目前架構，而是檢驗專案目前的主張，哪些地方其實已經超過現有證據所能支撐的範圍。

## 摘要結論

目前結論：

> Skill-0 作為 local-first search/review prototype 是成立的。  
> 但作為一個在 decomposition + governance + equivalence 上具有嚴格理論基礎的 framework，目前還不成立。

目前最大的問題不是 UI、測試數量、也不是容器化，而是 repo 內尚未收斂出單一穩定的 canonical contract。live schema、`parsed/*.json`、parser output、以及 embedding/search layer 彼此未對齊。這直接破壞了專案自己的核心理論：也就是「共享的結構化表示」應該是 search、comparison、governance 的共同基底。

## 審查環境

我建立了 repo-local virtual environment：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install \
  pytest pytest-cov pytest-timeout \
  fastapi uvicorn pydantic PyJWT prometheus_client structlog httpx rich \
  pydantic-settings numpy scikit-learn sqlite-vec markdown-it-py jsonschema
```

說明：
- 我刻意沒有完成 `requirements-dev.txt` 的完整安裝，因為它會沿著 `sentence-transformers` 拉進 CUDA 版 `torch`，對這次 review 並不必要，而且在 CPU review host 上成本過高。
- 目前這套環境已足夠支撐 parser/API/rate-limit 測試、schema validation 與靜態審查。

## 已執行驗證

### 1. 目標測試

命令：

```bash
.venv/bin/python -m pytest \
  tests/test_complex_skill_parser.py \
  tests/test_api_security.py \
  tests/integration/test_auth_flow.py \
  tests/integration/test_rate_limiting.py -q
```

結果：
- `44 passed in 1.26s`

解讀：
- 本地 review 環境是可用的。
- 現有 safety net 主要覆蓋 parser shape、auth、rate limiting。
- 它**不能**證明 decomposition model 在語義上是健全的。

### 2. 用 live schema 驗證現有 generated artifacts

驗證結果：

- `parsed/docx-skill.json`：`12` 個 schema errors
- `parsed/webapp-testing-skill.json`：`9` 個 schema errors
- 整個 `parsed/` 目錄：`178` 個 invalid files

代表性錯誤：

```text
parsed/docx-skill.json
- decomposition/directives/0: 'name' is a required property
- decomposition/rules/0: 'name' is a required property
- decomposition/rules/0: 'condition_type' is a required property
- decomposition/rules/0: 'returns' is a required property

parsed/*.json sample failures
- 'claude__a11y' does not match '^(claude|mcp)__[a-z_]+__[a-z_]+$'
```

解讀：
- repo 所宣稱的「live schema」目前並不是 repo 自己產出的 parsed dataset 真正遵守的契約。

## 主要問題

### 問題 1：目前不存在單一 canonical data contract

嚴重度：`High`

專案的核心主張是：

- 把自然語言技能轉成共享結構
- 再用這個共享結構支撐 search、comparison、governance

但 repo 目前同時存在多套不相容的資料方言：

- `schema/skill-decomposition.schema.json` 要求 `rule.name`、`condition_type`、`returns`，以及 `directive.name`
- `parsed/*.json` 仍輸出 `description`、`condition`、`output`，而 directive 沒有 `name`
- `tools/batch_parse.py` 仍標示自己是 `v2.1`
- `vector_db/embedder.py` 讀的是另一套欄位：`type`、`mode`、`content`

代表性證據：

- `schema/skill-decomposition.schema.json:305`
- `schema/skill-decomposition.schema.json:372`
- `schema/skill-decomposition.schema.json:594`
- `parsed/docx-skill.json:72`
- `parsed/docx-skill.json:92`
- `tools/batch_parse.py:3`
- `tools/batch_parse.py:266`
- `vector_db/embedder.py:103`
- `vector_db/embedder.py:115`
- `vector_db/embedder.py:126`

這不是單純的 implementation drift，而是直接打斷了專案自己的理論前提：如果共享資料層本身不穩，search 與 governance 就沒有穩定基底。

### 問題 2：governance model 實際上治理的是可變名稱，不是不可變 artifact

嚴重度：`High`

文件中的治理邏輯是：

1. 註冊 skill
2. 記錄 provenance / author / license
3. security scan
4. equivalence test
5. approve / reject / block
6. 保留 audit trail

但目前 persistence model 沒有把這些決策綁在不可變 artifact 上：

- `tools/governance_db.py` 使用 `name TEXT NOT NULL UNIQUE`
- `skill_id` 是動態生成 UUID，不是 content-addressed artifact identity
- 沒有 checksum / artifact revision table
- `create_skill()` 直接忽略 `**kwargs`，因此 version/source metadata 在註冊當下沒有被穩定記錄
- `update_skill()` 會直接原地覆寫同一列

代表性證據：

- `docs/dossier/04-core-logic-and-governance.md:74`
- `docs/dossier/04-core-logic-and-governance.md:96`
- `tools/governance_db.py:148`
- `tools/governance_db.py:308`
- `tools/governance_db.py:372`

實際後果：

同一個 skill name 底下，approval、risk score、equivalence result 都可能隨內容變動而漂移。也就是說，系統更接近「針對 mutable records 做 workflow」，而不是「針對可追溯 artifact 做 governance」。

### 問題 3：目前的「equivalence」其實是加權相似度，不是等價性

嚴重度：`Medium-High`

`tools/skill_tester.py` 目前計算的是：

- body semantic similarity
- headings / code blocks 的 structure similarity
- keyword 或 TF-IDF similarity
- metadata completeness

接著再用固定權重與門檻判定 pass/fail，並把結果存進 `equivalence_tests`。

代表性證據：

- `tools/skill_tester.py:103`
- `tools/skill_tester.py:112`
- `tools/skill_tester.py:450`
- `tools/skill_tester.py:567`

這比較像 fidelity / resemblance score，而不是 behavioral equivalence 或 semantic equivalence 的證明。

更關鍵的是，repo 自己的 shared contract 其實更嚴格：

- `docs/shared/02-mode-and-equivalence-contract.md:30`
- `docs/shared/02-mode-and-equivalence-contract.md:39`

該文件已明確指出，strict equivalence claim 需要：

- named fixtures
- expected canonical outputs
- repeatable comparison rules
- documented pass/fail results

目前 tester 還沒有達到這個門檻。

### 問題 4：ternary ontology 約束不足，實作上容易塌縮成「Directive 大水桶」

嚴重度：`Medium-High`

理論上：

- `Action` = 原子操作
- `Rule` = 原子判斷
- `Directive` = 描述性陳述

但實作上，`Directive` 被定義成「可分解，但此層選擇不分解」，這使它實際上變成 residual bucket。schema 只要求很少的欄位，而且 provenance 還是 optional。

代表性證據：

- `README.md:42`
- `README.md:59`
- `schema/skill-decomposition.schema.json:372`
- `schema/skill-decomposition.schema.json:422`

parser implementation 則暴露了這個問題：

- action/rule/directive 的分類高度依賴 keyword bag
- directive type 猜不到就預設成 `knowledge`
- 長句或 directive-like section 很容易直接被吸進 directives

代表性證據：

- `scripts/auto_parse.py:65`
- `scripts/auto_parse.py:102`
- `scripts/auto_parse.py:212`
- `scripts/auto_parse.py:224`

從反方角度看，這表示模糊或困難內容不是被迫面對可驗證分類，而是被系統收容進最寬鬆的類別。

### 問題 5：現有測試多半驗證 shape，不驗證語義真實性

嚴重度：`Medium`

我跑的測試都通過了，但其保護範圍有限。

例如：

- `tests/test_complex_skill_parser.py` 驗證的是 count、path extraction、finding category
- 它不驗證 decomposition 是否真的保留 source meaning
- 它也不驗證 parsed artifacts 是否符合目前 live schema

代表性證據：

- `tests/test_complex_skill_parser.py:14`
- `tests/test_complex_skill_parser.py:24`

這不是在否定現有測試，而是在界定「這些測試通過」目前究竟足以支撐哪些說法。

## 建議

### P0：先收斂單一 canonical contract

必須選一個 source of truth，並要求其他層全部服從：

- live schema
- parser output
- parsed dataset

不要再讓三者各自漂移。

最低驗收標準：

- `parsed/*.json` 能乾淨通過 live schema validation
- embedder/search 消費的欄位名稱與 schema 一致
- 文件不再混用 `2.1`、`2.4`、draft `2.5` 卻沒有清楚 compatibility language

### P1：把 governance 從 skill-name-centric 改成 artifact-centric

應引入不可變 artifact identity，例如：

- content hash / checksum
- source commit + path + extracted-at tuple
- revision table 與 logical skill name 分離

scan、approval、equivalence result 應綁在 revision，而不是只綁在某個 mutable latest row。

### P2：重新命名或縮限「equivalence」

在沒有更強證據之前，建議改用：

- compatibility score
- fidelity assessment
- conversion resemblance

只有在具備 canonical outputs 與可重現 comparison rules 的情況下，才保留「equivalence」這個詞。

### P3：讓 decomposition quality 變得可被證偽

如果 ternary model 真要當成理論模型，而不是方便標註的 annotation layer，至少應補：

- inferred elements 的 required provenance 或 confidence
- explicit unresolved / ambiguous state
- 對「無法分類而不失真」這種情況的審查流程

## 最終判斷

Skill-0 最強的描述方式是：

> 一個務實的 local-first prototype，用來索引、審查、操作化 skill documents

Skill-0 最弱的描述方式是：

> 一個已經穩定成立的 formal decomposition / governance / equivalence framework

後者未來可能成立，但就目前 repo 狀態來看，證據還不夠。
