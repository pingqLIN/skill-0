# TOOLS — CLI Utilities

## OVERVIEW

Python CLI scripts for batch parsing, scanning, governance, and database operations.

## WHERE TO LOOK

| Task | File | Notes |
|------|------|-------|
| Parse skills to JSON | `batch_parse.py` | Main entry, uses `advanced_skill_analyzer.py` |
| Security scanning | `batch_security_scan.py`, `skill_scanner.py` | Outputs to repo root |
| Governance DB | `governance_db.py` | SQLite schema for reviews/approvals |
| License detection | `license_detector.py` | Scans for license info |
| Schema migration | `migrate_to_schema_2_1.py` | One-time migration script |
| Pattern extraction | `pattern_extractor.py` | Extracts patterns from parsed skills |
| Evaluation | `evaluate.py`, `analyzer.py` | Parser quality metrics |

## KEY FILES

| File | Lines | Purpose |
|------|-------|---------|
| `advanced_skill_analyzer.py` | 39K | Core parsing logic with LLM |
| `skill_governance.py` | 22K | Approval workflow |
| `skill_scanner.py` | 28K | Security vulnerability scanner |
| `skill_tester.py` | 27K | Equivalence testing |
| `batch_parse.py` | 20K | Batch parsing orchestrator |

## CONVENTIONS

- All scripts are executable (`chmod +x`)
- Output goes to repo root or `governance/db/`
- Use `argparse` for CLI arguments
- Progress bars via `tqdm` when available

## COMMANDS

```bash
# Common operations
python batch_parse.py                     # Parse all skills
python batch_security_scan.py             # Security scan
python batch_import.py --dir ../source    # Import skills
python migrate_to_schema_2_1.py           # Schema migration
python analyzer.py                        # Coverage report
```
