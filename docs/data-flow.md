# Data flow

```
sales.csv / customers.csv / inventory.csv / expenses.csv
        │
        ▼
   Upload + checksum
        │
        ▼
 Bronze records + profile + quality score
        │
        ▼
 Cleaning preview (optional) → Apply → Silver records
        │
        ▼
 Validation rules → quarantine failing rows
        │
        ▼
 Transform / map columns → Gold records
        │
        ├── Dashboard KPIs
        ├── Analytics charts
        ├── Exports
        └── AI Copilot (facts → optional narration)
```

## Pipeline stages

1. **Extract** — read Bronze
2. **Profile** — column stats and quality issues
3. **Clean** — standard recipe or last applied recipe
4. **Validate** — rule engine + quarantine
5. **Transform** — map to business fields
6. **Load** — write Gold + lineage edges

## Important guarantees

- Metrics come from stored Gold rows, not hard-coded demo numbers
- Quality scores are calculated from actual cells
- Sample datasets are labelled `is_sample=true`
