# Project explanation

## Problem

MSMEs keep business data in spreadsheets. Those files often contain missing values, duplicates, inconsistent IDs, mixed date formats, and invalid amounts. Using them directly produces unreliable reports.

## Solution

MSME Data Copilot turns messy files into trusted analytical data:

1. Ingest and profile
2. Score and explain quality issues
3. Clean with preview and approval
4. Validate and quarantine bad rows
5. Load trusted Gold data
6. Visualize KPIs and answer questions with evidence

## What was reused from the ETL platform

- FastAPI + Next.js + Postgres stack
- Environment-based LLM configuration
- Layered ETL thinking (extract → transform → load)
- CORS, health checks, and service separation

## What is new

- Multi-file MSME datasets (sales/customers/inventory/expenses)
- Real quality engine and cleaning workspace
- Bronze/Silver/Gold storage of business rows
- Quarantine and lineage
- Analytics that refuse to invent missing metrics
- Intent-based AI copilot with offline fallback

## Design decisions

- **SQLite by default locally** so the project runs without Docker; Postgres remains the production path.
- **Heuristics for column mapping** instead of a heavyweight MDM product.
- **Predefined analytics intents** instead of free-form SQL generation for safety.
