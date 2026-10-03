#!/usr/bin/env bash
# Start/stop the acceptance runtime: API (ACC_PORT), tenant-limited worker, a failing-key worker
# (tenant t-acc21f only), collector and watchdog. Usage: env.sh start|stop|status <out-dir>
set -u
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"; cd "$ROOT"
CMD="${1:-status}"; OUT="${2:-$ROOT/artifacts/validation/t21/latest}"; PIDS="$OUT/logs/pids"
RUN_ID="${ACC_RUN_ID:-$(cat "$OUT/run-id" 2>/dev/null || date -u +%Y%m%dT%H%M%SZ)}"
PORT="${ACC_PORT:-8121}"; DATA="${ACC_DATA_DIR:-$ROOT/.data/t21/$RUN_ID}"
TEN="${ACC_TENANT:-t-acc21}"
mkdir -p "$OUT/logs" "$DATA"
start() {  # name, env-assignments..., command...
  local name="$1"; shift
  ( cd backend && env "$@" >"$OUT/logs/$name.log" 2>&1 & echo "$name $!" >>"$PIDS" )
}
case "$CMD" in
  start)
    : >"$PIDS"
    PY=backend/.venv/bin/python
    ( cd backend && DATA_DIR="$DATA" ../backend/.venv/bin/python tests/acceptance/provision.py ) >"$OUT/logs/provision.log" 2>&1 || { cat "$OUT/logs/provision.log"; exit 1; }
    start api DATA_DIR="$DATA" .venv/bin/uvicorn jevtriage.main:app --host 127.0.0.1 --port "$PORT"
    start worker DATA_DIR="$DATA" .venv/bin/python -m jevtriage.jobs.worker \
      --tenant "$TEN" --tenant "${TEN}b" --tenant "${TEN}p" --tenant "${TEN}g"
    # Deliberately invalid key: real Jev rejects it, giving a genuine failed run (no secret involved).
    start worker_badkey DATA_DIR="$DATA" JEV_API_KEY=invalid-acceptance-key \
      .venv/bin/python -m jevtriage.jobs.worker --tenant "${TEN}f"
    start collector DATA_DIR="$DATA" .venv/bin/python -m jevtriage.journal.collector
    start watchdog DATA_DIR="$DATA" .venv/bin/python -m jevtriage.journal.watchdog
    for _ in $(seq 1 40); do curl -sf "http://127.0.0.1:$PORT/api/ready" >/dev/null && break; sleep 1; done
    curl -sf "http://127.0.0.1:$PORT/api/ready" >/dev/null && echo "api ready on $PORT" || { echo "api not ready"; exit 1; }
    ;;
  restart-api|restart-worker)
    which="${CMD#restart-}"
    pid=$(awk -v n="$which" '$1==n{print $2}' "$PIDS")
    if [ -n "$pid" ]; then pkill -P "$pid" 2>/dev/null; kill "$pid" 2>/dev/null; sleep 2; pkill -9 -P "$pid" 2>/dev/null; kill -9 "$pid" 2>/dev/null; fi
    grep -v "^$which " "$PIDS" >"$PIDS.tmp"; mv "$PIDS.tmp" "$PIDS"
    if [ "$which" = api ]; then
      start api DATA_DIR="$DATA" .venv/bin/uvicorn jevtriage.main:app --host 127.0.0.1 --port "$PORT"
      for _ in $(seq 1 40); do curl -sf "http://127.0.0.1:$PORT/api/ready" >/dev/null && break; sleep 1; done
    else
      start worker DATA_DIR="$DATA" .venv/bin/python -m jevtriage.jobs.worker \
        --tenant "$TEN" --tenant "${TEN}b" --tenant "${TEN}p" --tenant "${TEN}g"
    fi
    ;;
  stop)
    [ -f "$PIDS" ] || exit 0
    while read -r name pid; do pkill -P "$pid" 2>/dev/null; kill "$pid" 2>/dev/null; done <"$PIDS"
    sleep 2
    while read -r name pid; do pkill -9 -P "$pid" 2>/dev/null; kill -9 "$pid" 2>/dev/null; done <"$PIDS"
    : >"$PIDS"
    ;;
  status)
    [ -f "$PIDS" ] && while read -r name pid; do kill -0 "$pid" 2>/dev/null && echo "$name $pid up" || echo "$name $pid down"; done <"$PIDS"
    ;;
esac
