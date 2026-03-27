# Parsed Dataset Validation Report

Date: `2026-03-27`
Scope: checked-in `parsed/*.json`

## Command

```bash
.venv/bin/python tools/validate_skill_schema.py parsed
```

## Result

- Files validated: `195`
- Passed: `195`
- Failed: `0`

## Interpretation

The checked-in parsed dataset currently validates cleanly against the live schema.

This does not prove parser quality or semantic correctness by itself. It only confirms that the stored artifact shape is contract-compliant.

## Follow-On Checks

- parser output should continue to emit canonical metadata and decomposition fields
- search/embedder consumers should continue to prefer canonical fields
- documentation should avoid stale dataset counts or old schema-version wording
