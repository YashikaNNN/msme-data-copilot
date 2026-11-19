#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "Starting MSME Data Copilot..."
echo "API: http://localhost:8000/docs"
echo "UI:  http://localhost:3000"

(
  cd "$ROOT/backend"
  # shellcheck disable=SC1091
  source .venv/bin/activate
  PYTHONPATH=. uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
) &
API_PID=$!

(
  cd "$ROOT/frontend"
  npm run dev
) &
WEB_PID=$!

trap 'kill $API_PID $WEB_PID 2>/dev/null || true' EXIT
wait
