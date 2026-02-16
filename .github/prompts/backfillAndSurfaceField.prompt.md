---
name: backfillAndSurfaceField
description: Trace a missing UI field across the full stack, backfill data, and surface it end-to-end.
argument-hint: The field name or data point that is missing from the UI (e.g., "source URL", "author avatar", "last modified date")
---
A data field is missing or not displayed on the web UI. Systematically fix it across the entire stack.

## Step 1: Data Flow Audit

Trace the field from database to frontend. For each layer, determine:

| Layer | Check |
|-------|-------|
| **DB Schema** | Does the column/field exist in the table definition? |
| **DB Data** | Is the field actually populated, or are values empty/null? |
| **API Model (List)** | Is the field included in the list/summary response schema? |
| **API Model (Detail)** | Is the field included in the detail response schema? |
| **API Service** | Does the service method return this field from DB records? |
| **Frontend Types** | Does the TypeScript interface include this field? |
| **Frontend List View** | Does the table/list component render this field? |
| **Frontend Detail View** | Does the detail page display this field? |

## Step 2: Backfill Missing Data

If the DB column exists but data is empty:
1. Create a backfill script that derives or maps the correct values
2. Support `--dry-run` mode for safe preview
3. Use the existing DB update API (not raw SQL) to preserve audit trails
4. Run dry-run first, verify output, then execute for real

If the DB column doesn't exist:
1. Add a migration to create the column
2. Then proceed with backfill

## Step 3: API Layer

- Add the field to the **list/summary** response model if missing
- Add the field to the service method that builds summary dicts
- Ensure the **detail** endpoint already returns it (fix if not)

## Step 4: Frontend

- Add the field to the TypeScript **summary** interface
- In the **list/table** component: add a column or icon link for the field
- In the **detail** page: display the field with appropriate UX (e.g., clickable link for URLs, badge for status)
- Use `e.stopPropagation()` on inline links within clickable table rows
- External links should use `target="_blank"` and `rel="noopener noreferrer"`

## Step 5: Verify

- Confirm DB has populated values
- Confirm API list endpoint returns the field
- Confirm API detail endpoint returns the field
- Confirm frontend renders correctly with no type errors
- Run existing tests to ensure no regressions
