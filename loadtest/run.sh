#!/usr/bin/env bash
set -euo pipefail
repo_dir="$(cd "$(dirname "$0")/.." && pwd)"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
run_dir="$repo_dir/${T25_OUTPUT_ROOT:-artifacts/validation/t25}/$stamp"
mkdir -p "$run_dir"
export T25_NEO4J_DIR="$run_dir/neo4j"
export NEO4J_URI="bolt://localhost:${T25_NEO4J_BOLT_PORT:-7690}"
export DATA_DIR="$run_dir/data"
export JEV_MODE=live
export PYTHONPATH="$repo_dir/backend"
mkdir -p "$DATA_DIR"
api_pid= worker_pid= collector_pid=
cleanup() {
  if [[ -n "$api_pid" ]]; then
    for child in $(pgrep -P "$api_pid" 2>/dev/null || true); do kill "$child" 2>/dev/null || true; done
  fi
  for pid in "$api_pid" "$worker_pid" "$collector_pid"; do
    if [[ -n "$pid" ]]; then kill "$pid" 2>/dev/null || true; fi
  done
  for pid in "$api_pid" "$worker_pid" "$collector_pid"; do
    if [[ -n "$pid" ]]; then wait "$pid" 2>/dev/null || true; fi
  done
  docker compose -p "${T25_COMPOSE_PROJECT:-jevtriage-t25}" -f "$repo_dir/loadtest/compose.yml" down >/dev/null 2>&1 || true
  # Raw journal, collector metrics, timings and Run snapshots are retained above.
  "$repo_dir/backend/.venv/bin/python" - <<'PY'
import os
import shutil
from pathlib import Path

base = Path(os.environ["T25_NEO4J_DIR"]).resolve().parent
for target in (Path(os.environ["T25_NEO4J_DIR"]), Path(os.environ["DATA_DIR"]) / "files"):
    if target.exists() and not target.is_symlink() and target.resolve().is_relative_to(base):
        shutil.rmtree(target)
PY
}
trap cleanup EXIT INT TERM
docker compose -p "${T25_COMPOSE_PROJECT:-jevtriage-t25}" -f "$repo_dir/loadtest/compose.yml" up -d --wait
(cd "$repo_dir" && backend/.venv/bin/python scripts/bootstrap_dev.py) >"$run_dir/bootstrap.log" 2>&1
(cd "$repo_dir/backend" && .venv/bin/python "$repo_dir/loadtest/serve.py") >"$run_dir/api.log" 2>&1 & api_pid=$!
(cd "$repo_dir/backend" && .venv/bin/python -m jevtriage.jobs.worker --tenant t-alpha --concurrency 10) >"$run_dir/worker.log" 2>&1 & worker_pid=$!
(cd "$repo_dir/backend" && .venv/bin/python -m jevtriage.journal.collector) >"$run_dir/collector.log" 2>&1 & collector_pid=$!
for _ in $(seq 1 60); do
  if curl -fsS "http://127.0.0.1:${T25_API_PORT:-8125}/api/ready" >/dev/null 2>&1; then break; fi
  sleep 1
done
curl -fsS "http://127.0.0.1:${T25_API_PORT:-8125}/api/ready" >/dev/null
set +e
(cd "$repo_dir" && backend/.venv/bin/python loadtest/run.py --output "$run_dir" --base-url "http://127.0.0.1:${T25_API_PORT:-8125}" "$@")
runner_status=$?
(cd "$repo_dir" && backend/.venv/bin/python loadtest/analyze.py --output "$run_dir") >"$run_dir/analyze.log" 2>&1
analyzer_status=$?
set -e
echo "T25 output: $run_dir"
if [[ "$analyzer_status" -ne 0 ]]; then
  echo "T25 analysis failed; see $run_dir/analyze.log" >&2
  exit "$analyzer_status"
fi
exit "$runner_status"
