# Skill-0 vs Cisco AI Defense Skill Scanner: Security Comparison Report

**Author**: pingqLIN  
**Date**: 2026-02-10  
**Version**: 1.0.0

## Executive Summary

This report compares **Cisco AI Defense Skill Scanner** with **Skill-0** across positioning, architecture, data formats, and security capabilities. Skill Scanner focuses on **agent skill security detection** (prompt injection, data exfiltration, malicious code) with multi-engine scanning, SARIF output, and CI/CD integration. Skill-0 focuses on **skill decomposition, semantic search, and governance**, while providing a foundational rule-based security scanner and risk scoring.

Conclusion: the two projects are complementary. If Skill-0 absorbs Skill Scanner's multi-engine security analysis and AITech taxonomy mapping, its governance stack becomes enterprise-ready. If Skill Scanner adopts Skill-0's structured decomposition and semantic search, it gains stronger explainability and traceability.

---

## 1. Positioning Comparison

### Skill-0
- **Positioning**: Skill decomposition analyzer and semantic search engine
- **Core value**: Parse Claude Skills/MCP Tools into structured JSON (Schema 2.3.0) with composable atomic elements and governance workflow
- **Security focus**: Built-in rule-based scanning (SEC001-SEC007) with governance database

### Cisco AI Defense Skill Scanner
- **Positioning**: Agent skills security scanner
- **Core value**: Multi-engine detection for prompt injection, data exfiltration, and malicious code with SARIF/JSON/Markdown reports
- **Supported formats**: Agent Skills specification (OpenAI Codex Skills, Cursor Agent Skills)

---

## 2. Architecture & Workflow Comparison

| Dimension | Skill-0 | Skill Scanner |
|-----------|---------|---------------|
| **Core flow** | Parse → Structure → Vector search → Governance | Load skill → Multi-engine scan → Risk reports |
| **Security engines** | Rule-based scanning (Python regex) | Static rules (YAML/YARA) + Behavioral dataflow + LLM Analyzer + Meta Analyzer |
| **Interfaces** | Python CLI + FastAPI + Dashboard | CLI + FastAPI API |
| **Outputs** | Governance DB + report files | SARIF/JSON/Markdown/Table |
| **Extensibility** | Parser abstraction + governance workflow | Analyzer plugins + ruleset expansion |

---

## 3. Data Format Comparison

### Skill-0: Structured JSON
- JSON Schema 2.3.0
- Action/Rule/Directive ternary classification
- Provenance and skill_links supported

### Skill Scanner: SKILL.md
- YAML frontmatter + Markdown body
- Metadata includes allowed_tools, compatibility, etc.

---

## 4. Security Capability Comparison

| Capability | Skill-0 | Skill Scanner |
|------------|---------|---------------|
| **Prompt Injection** | Rule-based checks | YAML/YARA + LLM detection |
| **Data Exfiltration** | Rule-based checks | Behavioral dataflow + LLM analysis |
| **Malicious Code** | Rule-based checks | Static rules + behavioral analysis |
| **Threat Taxonomy** | SEC001-SEC007 | AITech taxonomy mapping |
| **CI/CD** | Requires manual wrapping | Built-in fail-on-findings + SARIF |
| **False Positive Filtering** | None | Meta Analyzer for noise reduction |

---

## 5. Use Case Comparison

### Scenario A: Governance + structured analysis
- **Skill-0 wins**: traceable decomposition with semantic search

### Scenario B: Enterprise CI security scanning
- **Skill Scanner wins**: SARIF output, fail-on-findings, LLM/behavioral analysis

### Scenario C: Threat taxonomy & compliance
- **Skill Scanner wins**: AITech taxonomy alignment and broader threat model

---

## 6. Strengths & Weaknesses

### Skill-0 Strengths
1. **Deep structure**: composable Action/Rule/Directive atoms
2. **Semantic search**: vector retrieval and pattern analysis
3. **Governance workflow**: approvals, risk scores, scan history

### Skill-0 Weaknesses
1. **Single security engine**: primarily rule-based scanning
2. **No standard taxonomy**: lacks AITech/OWASP mapping
3. **Limited CI formats**: no SARIF output

### Skill Scanner Strengths
1. **Multi-engine detection**: static + behavioral + LLM + meta
2. **CI-friendly outputs**: SARIF and fail-on-findings
3. **Robust taxonomy**: AITech-aligned threat categories

### Skill Scanner Weaknesses
1. **No structured decomposition**: lacks Action/Rule/Directive model
2. **No semantic search**: limited cross-skill pattern analysis
3. **Light governance**: minimal approval/provenance workflow

---

## 7. Complementarity & Integration

Position Skill-0 as the governance/structure layer and Skill Scanner as the security scanning layer:

```
┌──────────────────────────┐
│ Skill Scanner            │
│ Multi-engine scanning    │
└─────────────┬────────────┘
              │ Findings
              ↓
┌──────────────────────────┐
│ Skill-0 Governance        │
│ Risk scoring + structure  │
└──────────────────────────┘
```

---

## 8. Upgrade & New Skill Recommendations for Skill-0

### 8.1 Upgrade Items
1. **Adopt AITech taxonomy**: add taxonomy codes/categories in scan results.
2. **Expand rule engine**: support YAML/YARA rules and multi-language scanning.
3. **SARIF output + CI gates**: add `--format sarif` and `--fail-on-findings`.
4. **Analyzer plugin architecture**: enable modular LLM/behavioral analyzers.
5. **SKILL.md loader**: ingest Agent Skills format and convert to Skill-0 JSON.

### 8.2 Proposed New Skills (Skill-0 Skill format)
1. **Skill Security Audit**: scan skill directories and emit SARIF/Markdown reports.
2. **Threat Taxonomy Mapper**: normalize findings to AITech/OWASP/NIST categories.
3. **Secure Skill Packaging**: validate allowed_tools, metadata completeness, and intent alignment.
4. **Security Rule Authoring Guide**: assist in writing/validating security rules and test cases.

---

## 9. Conclusion

Skill Scanner provides a mature security scanning engine and taxonomy framework, while Skill-0 provides structured decomposition and governance. By absorbing Skill Scanner's detection and reporting strengths, Skill-0 can evolve into a comprehensive, enterprise-ready skill security platform for CI/CD and compliance.

---

## 10. References

- https://github.com/cisco-ai-defense/skill-scanner
- https://raw.githubusercontent.com/cisco-ai-defense/skill-scanner/main/docs/architecture.md
- https://raw.githubusercontent.com/cisco-ai-defense/skill-scanner/main/docs/threat-taxonomy.md
- https://github.com/pingqLIN/skill-0
