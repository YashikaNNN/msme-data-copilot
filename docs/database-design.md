# Database design

Core tables used by the running product:

| Table | Purpose |
| --- | --- |
| `datasets` | Dataset metadata, status, quality score |
| `dataset_files` | Stored file name, checksum, size |
| `dataset_records` | Bronze/Silver rows as JSON |
| `dataset_columns` | Profiled column statistics |
| `quality_issues` | Detected issues with severity and advice |
| `quality_snapshots` | Historical quality dimensions |
| `quality_rules` | Configurable validation rules |
| `validation_results` | Latest rule outcomes |
| `cleaning_operations` | Preview/apply/reject history |
| `pipeline_runs` / `pipeline_stages` | Execution monitoring |
| `lineage_edges` | Source → target stage graph |
| `gold_records` | Analytics-ready rows |
| `chat_sessions` / `chat_messages` | Copilot history |
| `activity_events` | Dashboard activity feed |

## Indexes

Important indexes exist on dataset/layer, pipeline status, gold entity/date, and foreign keys.

## Migrations

Alembic is configured under `backend/alembic`. Local SQLite and Docker startup also call `Base.metadata.create_all` so the app boots without a separate migrate step during demos.
