# BizQuery : MSME Data Copilot

**From messy business data to data quality and business intelligence.**

A platform for small and medium businesses to upload CSV/Excel/JSON files, diagnose data quality, clean and validate data, load trusted rows into analytics, and ask evidence-based questions through an AI copilot.

This is a **new project**. It reuses ideas and stack patterns from the AI-powered ETL Analytics Platform, but lives in its own repository so the original project stays untouched.

## Features

- Business registration and login (business name, owner, email, password)
- Private per-business workspaces — datasets and analytics stay isolated
- Upload CSV, XLSX, JSON with schema detection and preview
- Clear workflow: Upload → Check quality → Clean & validate → View insights
- Real data-quality scoring with plain-language explanations
- Cleaning workspace with preview / apply / reject (original upload never overwritten)
- Validation rules with quarantine for blocking failures
- Processing history with understandable stage labels
- Business analytics charts for sales, customers, inventory, expenses
- AI Copilot grounded in calculated metrics (works without an API key)
- Sample messy business datasets for a labelled demo
- Authenticated downloads for cleaned data, quality reports, and analytics summaries

## Tech stack

| Layer | Technology |
| --- | --- |
| Frontend | Next.js 15, React, TypeScript, Tailwind CSS, Recharts |
| Backend | FastAPI, Pydantic, SQLAlchemy, Alembic |
| Data | Pandas, PostgreSQL (or SQLite for local demo) |
| AI | Gemini / OpenRouter via env vars, with metrics-only fallback |

## Quick start (local)

### 1. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env   # optional
uvicorn app.main:app --reload --port 8000
```

Default database is SQLite (`backend/msme_copilot.db`). For Postgres, set:

```bash
DATABASE_URL=postgresql+psycopg://msme:msme@localhost:5433/msme_copilot
```

### 2. Frontend

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

### 3. Demo path

1. Create a business account (or sign in)
2. Open **Try Sample Data** → **Load into my workspace**
3. Follow **Check quality → Clean data → Process for insights**
4. Open **Analytics** and **Ask AI**

## Docker

```bash
cp .env.example .env
docker compose up --build
```

- Frontend: http://localhost:3000
- API docs: http://localhost:8000/docs
- Postgres: localhost:5433

## Production deploy (Vercel + Render)

Vercel cannot host FastAPI + Postgres. Use:

1. **Render** for API + database (`render.yaml`)
2. **Vercel** for the Next.js app (`frontend/` root directory)

Full steps: [docs/deployment-vercel.md](docs/deployment-vercel.md)

## Architecture

```
Upload → Bronze (raw) → Profile/Quality → Clean (Silver) → Validate/Quarantine → Gold analytics → Dashboard / Copilot
```

See:

- [docs/architecture.md](docs/architecture.md)
- [docs/data-flow.md](docs/data-flow.md)
- [docs/database-design.md](docs/database-design.md)
- [docs/project-explanation.md](docs/project-explanation.md)
- [docs/viva-preparation.md](docs/viva-preparation.md)

## API overview

Base path: `/api/v1`

- `POST /datasets/upload`
- `GET /datasets/{id}/quality`
- `POST /datasets/{id}/cleaning/preview|apply|reject`
- `POST /datasets/{id}/validate`
- `POST /datasets/{id}/pipeline/run`
- `GET /analytics/*`
- `POST /copilot/ask`
- `POST /samples/load`

Interactive docs: `/docs`

## Environment variables

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | SQLAlchemy URL |
| `CORS_ORIGINS` | Allowed frontend origins |
| `GEMINI_API_KEY` | Optional Gemini narration |
| `OPENROUTER_API_KEY` | Optional OpenRouter narration |
| `LLM_PROVIDER` | `auto`, `gemini`, `openrouter`, or `none` |
| `NEXT_PUBLIC_API_URL` | Frontend → API base URL |

## Tests

```bash
cd backend
source .venv/bin/activate
PYTHONPATH=. pytest -q
```

## Limitations

- Single-tenant local workspace (no multi-user auth yet)
- Column mapping is heuristic, not a full MDM system
- Copilot answers a fixed set of business intents from analytics functions
- Large files are capped (`MAX_UPLOAD_MB`, `MAX_ROWS`)

## Future scope

- Auth / workspaces
- More cleaning recipes and rule templates
- Scheduled pipelines
- Richer lineage graph UI
