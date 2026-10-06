#!/usr/bin/env bash
# Dedicated runtime for the UX-2 source-viewer / judgment-map E2E: shared Neo4j (make up), tenant t-ux2,
# API on 8391, a worker limited to t-ux2 (AI_MODE=live, key from .env). The vite server (5591) is started by Playwright.
# Usage: env.sh start|stop   (state under .data/ux2 and artifacts/ux2-e2e/logs)
set -u
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"; cd "$ROOT"
TEN="${UX2_TENANT:-t-ux2}"; PORT="${UX2_API_PORT:-8391}"; DATA="$ROOT/.data/ux2"; LOGS="$ROOT/artifacts/ux2-e2e/logs"
mkdir -p "$DATA" "$LOGS"
case "${1:-}" in
  start)
    (cd backend && .venv/bin/python ../frontend/e2e/source-viewer/seed.py "$TEN") >"$LOGS/seed.log" 2>&1 || { cat "$LOGS/seed.log"; exit 1; }
    (cd backend && DATA_DIR="$DATA" AI_MODE=live .venv/bin/uvicorn ildongi.main:app --host 127.0.0.1 --port "$PORT" >"$LOGS/api.log" 2>&1 & echo $! >"$LOGS/api.pid")
    (cd backend && DATA_DIR="$DATA" AI_MODE=live .venv/bin/python -m ildongi.jobs.worker --tenant "$TEN" >"$LOGS/worker.log" 2>&1 & echo $! >"$LOGS/worker.pid")
    for _ in $(seq 1 40); do curl -sf "http://127.0.0.1:$PORT/api/ready" >/dev/null && break; sleep 1; done
    curl -sf "http://127.0.0.1:$PORT/api/ready" >/dev/null && echo "api ready on $PORT, tenant $TEN" || { echo "api not ready"; exit 1; }
    ;;
  stop)
    for name in api worker; do
      pid=$(cat "$LOGS/$name.pid" 2>/dev/null) || continue
      pkill -P "$pid" 2>/dev/null; kill "$pid" 2>/dev/null; sleep 1; kill -9 "$pid" 2>/dev/null; rm -f "$LOGS/$name.pid"
    done
    ;;
  *) echo "usage: env.sh start|stop"; exit 2 ;;
esac
