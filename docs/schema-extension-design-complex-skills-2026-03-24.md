# Complex Skill Schema Extension Design

Updated: `2026-03-24`

**Implementation status:** 🟡 Designed

## 1. Purpose

本文件定義 `Foundation F1` 所需的 complex-skill schema/output 設計，目的是為 `skill-0` parser、`skill-0-GUI` reviewer surface、以及 shared contracts 建立共同資料形狀。

這份設計處理的是 `P0` 範圍，不追求完整 graph platform。它要解的是：

- 如何在保留現有 `decomposition` 輸出的前提下，新增 manifest-oriented structure
- 如何讓 supporting files、command references、delegation、unresolved references 成為 first-class data
- 如何讓 GUI 能消費這些資料而不需要猜測 parser output
- 如何避免直接打斷現有 `parse_skill_md(name, text)` 消費者

## 2. Design Goals

P0 設計只服務以下幾件事：

1. discovery-first analysis
2. backward-compatible parser evolution
3. mode-aware output
4. reviewer-meaningful warnings
5. minimal schema expansion with clear upgrade path

P0 不處理：

- full graph reasoning
- recursive skill inheritance semantics
- parameter-level command semantics
- complete execution simulation

## 3. Current Gaps

目前 live schema `2.4.0` 已有：

- `provenance`
- `related_elements`
- `execution_paths`
- `parser_meta`

但缺少這些 first-class 結構：

- `manifest`
- `supporting_files`
- `command_references`
- `delegation_nodes`
- `analysis_findings`
- `authority_profile`
- `reference_resolution`

這造成三個實際問題：

1. parser 只能輸出單檔 decomposition，不能清楚表達 skill package
2. GUI 只能從文字與 heuristics 猜 supporting context
3. warnings 很難做到 evidence-backed 而不是自由發揮

## 4. Proposed Versioning Rule

本設計建議把 complex-skill P0 的目標 schema 版本定為：

`2.5.0`

版本規則：

- `2.4.x`：既有單檔 decomposition baseline
- `2.5.0`：新增 manifest-oriented P0 fields，但保持 backward compatible
- 舊 consumer 若只讀 `meta` / `decomposition` / `execution_paths`，不應被破壞

這表示：

- 新欄位應全部為 optional
- 不更改既有 `decomposition` 結構
- 不移除既有欄位

## 5. Proposed Top-Level Additions

### 5.1 `manifest`

用途：

- 提供 cheap deterministic pass 的結構摘要

建議形狀：

```json
{
  "manifest": {
    "entry_skill": {
      "path": "fixtures/multi-ref/SKILL.md",
      "name": "multi-ref-skill",
      "resolved": true
    },
    "analysis_level": "manifest",
    "supporting_files_count": 3,
    "command_references_count": 2,
    "delegation_nodes_count": 1,
    "unresolved_references_count": 1
  }
}
```

### 5.2 `supporting_files`

用途：

- 列出與 entry skill 相關的 supporting context

最小欄位：

- `id`
- `path`
- `kind`
- `resolved`
- `referenced_by`
- `summary`

建議 `kind`：

- `reference`
- `script`
- `template`
- `asset`
- `config`
- `unknown`

### 5.3 `command_references`

用途：

- 讓 command block 不再只被壓扁成 generic action

最小欄位：

- `id`
- `source_path`
- `command`
- `shell_family`
- `authority_profile`
- `risk_grade`
- `resolved_from`

建議 `authority_profile`：

- `read_only`
- `content_transform`
- `file_write`
- `process_exec`
- `network_call`
- `system_mutation`
- `unknown_authority`

建議 `risk_grade`：

- `info`
- `low`
- `medium`
- `high`

### 5.4 `delegation_nodes`

用途：

- 表達 `context: fork`、`agent`、或等價 delegation signal

最小欄位：

- `id`
- `kind`
- `agent`
- `source_path`
- `resolved`
- `notes`

建議 `kind`：

- `fork_context`
- `named_agent`
- `subagent_reference`

### 5.5 `analysis_findings`

用途：

- 為 GUI 與 reviewer surface 提供 evidence-backed findings basis

最小欄位：

- `finding_id`
- `title`
- `category`
- `severity`
- `confidence`
- `affected_paths`
- `evidence`
- `recommended_action`

這層不應取代 GUI 自己的 rendering logic，但應提供穩定的 parser-side evidence substrate。

## 6. Proposed Definition Sketch

本階段不直接修改 live schema，但建議新增下列 definitions：

- `manifest_entry_skill`
- `supporting_file`
- `command_reference`
- `delegation_node`
- `analysis_finding`
- `evidence_item`

其中最重要的是 `supporting_file`、`command_reference`、`analysis_finding`。

## 7. Proposed Parser Output Contract

### 7.1 Single-file compatibility path

舊入口：

```python
parse_skill_md(skill_name: str, content: str) -> dict
```

保留原行為，但允許回傳 optional new fields：

- `manifest`
- `command_references`
- `analysis_findings`
- `parser_meta.analysis_level`

在 text-only 路徑下：

- `supporting_files` 可為空陣列
- `delegation_nodes` 可由 frontmatter / text hints 判斷
- `analysis_level` 應標記為 `single_file`

### 7.2 Complex-skill entrypoint

新增入口：

```python
parse_skill_manifest(entry_path: str, *, root_dir: str | None = None, options: dict | None = None) -> dict
```

用途：

- 掃描 entry skill 與 supporting files
- 解析相對路徑 references
- 建立 manifest-oriented structure
- 保留原本 `decomposition` 作為 parser core output

這樣 GUI bridge 可逐步升級，不必一次打斷舊 API。

## 8. Proposed `parser_meta` Additions

在不破壞既有 `parser_meta` 的前提下，建議新增：

- `analysis_level`
- `manifest_present`
- `reference_resolution_complete`
- `fallback_compatible_only`
- `legacy_entrypoint_used`

建議值：

```json
{
  "parser_meta": {
    "analysis_level": "manifest",
    "manifest_present": true,
    "reference_resolution_complete": false,
    "fallback_compatible_only": false,
    "legacy_entrypoint_used": false
  }
}
```

## 9. Proposed GUI Consumption Shape

`skill-0-GUI` 在 P0 不需要完整 graph engine，只需要穩定讀這些欄位：

1. `manifest`
2. `supporting_files`
3. `command_references`
4. `delegation_nodes`
5. `analysis_findings`
6. `parser_meta.analysis_level`

GUI 最低限度應能：

- 顯示 mode / equivalence caveat
- 顯示 supporting files summary
- 顯示 unresolved references count
- 顯示 top command risks
- 顯示 prioritized findings

## 10. Example Output

```json
{
  "meta": {
    "skill_id": "claude__multi_ref_skill",
    "name": "multi-ref-skill",
    "skill_layer": "claude_skill",
    "schema_version": "2.5.0",
    "parse_timestamp": "2026-03-24T10:00:00Z"
  },
  "manifest": {
    "entry_skill": {
      "path": "fixtures/multi-ref/SKILL.md",
      "name": "multi-ref-skill",
      "resolved": true
    },
    "analysis_level": "manifest",
    "supporting_files_count": 2,
    "command_references_count": 1,
    "delegation_nodes_count": 1,
    "unresolved_references_count": 1
  },
  "supporting_files": [
    {
      "id": "sf_001",
      "path": "fixtures/multi-ref/references/deploy.md",
      "kind": "reference",
      "resolved": true,
      "referenced_by": ["fixtures/multi-ref/SKILL.md"],
      "summary": "Deployment workflow reference"
    }
  ],
  "command_references": [
    {
      "id": "cr_001",
      "source_path": "fixtures/multi-ref/SKILL.md",
      "command": "npm run deploy",
      "shell_family": "npm",
      "authority_profile": "process_exec",
      "risk_grade": "medium",
      "resolved_from": "fenced_code_block"
    }
  ],
  "delegation_nodes": [
    {
      "id": "dg_001",
      "kind": "fork_context",
      "agent": "reviewer",
      "source_path": "fixtures/multi-ref/SKILL.md",
      "resolved": true,
      "notes": "Delegates review in forked context"
    }
  ],
  "analysis_findings": [
    {
      "finding_id": "f_001",
      "title": "Unresolved supporting reference on reachable path",
      "category": "reference_integrity",
      "severity": "medium",
      "confidence": "high",
      "affected_paths": ["fixtures/multi-ref/SKILL.md"],
      "evidence": [
        {
          "kind": "missing_reference",
          "source_path": "fixtures/multi-ref/SKILL.md",
          "excerpt": "./references/missing.md",
          "explanation": "Referenced path was not resolved during manifest scan"
        }
      ],
      "recommended_action": "resolve_reference"
    }
  ],
  "decomposition": {
    "actions": [],
    "rules": [],
    "directives": []
  },
  "parser_meta": {
    "analysis_level": "manifest",
    "manifest_present": true,
    "reference_resolution_complete": false,
    "legacy_entrypoint_used": false
  }
}
```

## 11. Fixture Profiles Required For F2

因為 `converted-skills/` 目前沒有現成 multi-file complex-skill 樣本，F2 應手工建立至少三個 fixtures：

### Fixture A: `fixture-simple-frontmatter`

目標：

- 驗證 rich frontmatter extraction

至少包含：

- `allowed-tools`
- `disable-model-invocation`
- `argument-hint`

### Fixture B: `fixture-multi-ref`

目標：

- 驗證 markdown 相對路徑與 supporting file summary

至少包含：

- `SKILL.md`
- `references/`
- 至少一個 resolved ref
- 至少一個 unresolved ref

### Fixture C: `fixture-delegation`

目標：

- 驗證 `context: fork`、`agent`、scripts summary、command reference grading

至少包含：

- `SKILL.md`
- `scripts/`
- delegation signal
- 至少一個 state-changing 或 process-exec command

## 12. Documentation Alignment

完成 F1 後，至少應同步這些文件：

- `reference.md`
- `examples.md`
- `docs/dossier/07-complex-skills-analysis-strategy.md`
- `skill-0-GUI/docs/09-complex-skill-analysis-spec.md`
- `skill-0-GUI/docs/10-complex-skill-risk-schema.md`
- `skill-0-GUI/docs/11-evidence-based-warning-template.md`

並在上述設計 / 規格文件頂部加入狀態標記：

- 🟢 Implemented
- 🟡 Designed
- ⚪ Planned

## 13. Recommended Next Step

F1 完成後，最直接的下一步不是立刻大改 live schema，而是：

1. 先建立 3 個 fixtures
2. 先做 parser-side manifest prototype
3. 用 prototype output 驗證 GUI consumption shape
4. 確認後再進行 live schema 變更

這樣可以避免 schema 先擴太多，但 parser / GUI 實際上又不消費。
