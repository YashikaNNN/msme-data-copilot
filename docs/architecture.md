# Architecture

## Overview

MSME Data Copilot is a monorepo with:

- `frontend/` — Next.js App Router UI
- `backend/` — FastAPI services, SQLAlchemy models, Pandas processing
- `docker-compose.yml` — Postgres + API + web

## Layers

1. **Presentation** — dashboard pages call REST endpoints
2. **API** — FastAPI routers validate input and return JSON
3. **Services** — ingest, quality, cleaning, validation, pipeline, analytics, copilot
4. **Storage** — uploaded files on disk; metadata and row layers in the database

## Data architecture

| Layer | Meaning |
| --- | --- |
| Bronze | Exact uploaded rows after header normalization |
| Silver | Cleaned copy; may include quarantined rows |
| Gold | Trusted business rows used by analytics |

Cleaning never mutates Bronze. Rejecting cleaning deletes Silver/Gold for that dataset and keeps the original upload.

## AI design

1. User asks a question
2. Intent matcher selects an analytics function
3. Metrics are computed from Gold / quality tables
4. Optional LLM receives only those facts and narrates them
5. If no API key exists, the calculated answer is still returned

The LLM never receives a database connection and never executes SQL.
