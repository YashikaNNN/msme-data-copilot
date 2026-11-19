# Deploy MSME Data Copilot (Vercel + Render)

Vercel hosts the **Next.js frontend** only.  
Render hosts the **FastAPI backend + PostgreSQL**.

```
Browser → Vercel (frontend)
              ↓ NEXT_PUBLIC_API_URL
         Render (FastAPI + Postgres)
```

## STEP 1 — Deploy backend on Render

1. Open [https://dashboard.render.com](https://dashboard.render.com) and sign in with GitHub.
2. Click **New → Blueprint**.
3. Select repo **`YashikaNNN/msme-data-copilot`**.
4. Render reads `render.yaml` and creates:
   - Postgres: `msme-copilot-db`
   - Web service: `msme-copilot-api`
5. For `CORS_ORIGINS`, put a temporary value for now:

```text
http://localhost:3000
```

6. Click **Apply**.
7. Wait until the API is **Live**.
8. Copy the API URL, for example:

```text
https://msme-copilot-api.onrender.com
```

9. Open that URL + `/api/v1/health`. You should see:

```json
{"status":"ok","service":"msme-data-copilot"}
```

> Free Render services sleep after idle time. The first request after sleep can take ~30–60 seconds.

## STEP 2 — Deploy frontend on Vercel

1. Open [https://vercel.com/new](https://vercel.com/new) and sign in with GitHub.
2. Import **`YashikaNNN/msme-data-copilot`**.
3. Configure the project:
   - **Framework Preset:** Next.js
   - **Root Directory:** `frontend`  ← important
   - **Build Command:** `npm run build`
   - **Output Directory:** leave default / `.next`
4. Add Environment Variable:

| Name | Value |
| --- | --- |
| `NEXT_PUBLIC_API_URL` | `https://msme-copilot-api.onrender.com` |

Use your real Render API URL (no trailing slash).

5. Click **Deploy**.
6. Copy the Vercel URL, for example:

```text
https://msme-data-copilot.vercel.app
```

## STEP 3 — Connect frontend and backend

1. Go back to Render → `msme-copilot-api` → **Environment**.
2. Set:

| Key | Value |
| --- | --- |
| `CORS_ORIGINS` | `https://msme-data-copilot.vercel.app` |

If you also use preview URLs, the API already allows `https://*.vercel.app` via regex.

3. Save → Render redeploys the API.
4. Open the Vercel site.
5. Go to **Sample Data → Load sample workspace**.
6. Check Dashboard / Quality / Analytics / Copilot.

## STEP 4 — Optional LLM

In Render env vars:

| Key | Value |
| --- | --- |
| `LLM_PROVIDER` | `auto` |
| `GEMINI_API_KEY` or `OPENROUTER_API_KEY` | your key |

Without a key, Copilot still answers from calculated metrics.

## Troubleshooting

| Problem | Fix |
| --- | --- |
| Frontend loads but API fails | Check `NEXT_PUBLIC_API_URL` (no trailing slash) and redeploy Vercel |
| CORS error in browser | Set `CORS_ORIGINS` to your exact Vercel URL on Render |
| Health check fails on Render | Confirm start command uses `$PORT` and path `/api/v1/health` |
| Empty analytics after deploy | Click **Load sample workspace** or upload files on the live site |
| Slow first request | Free Render spin-up; wait and retry |

## Local reminder

Docker remains the local path:

```bash
cd msme-data-copilot
docker compose up --build
```
