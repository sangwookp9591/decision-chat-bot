#!/usr/bin/env bash
# `make test-acceptance`: start the acceptance runtime (shared Neo4j via `make up`, dedicated tenants,
# tenant-limited workers, API on ACC_PORT), run backend acceptance tests and the Playwright UI scenarios,
# write everything under artifacts/validation/t21/<timestamp>/, and always stop what it started.
# Uses live Jev (JEV_MODE=live; JEV_API_KEY from .env). Set ACC_SKIP_UI=1 to skip the UI part.
set -u
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"; cd "$ROOT"
TS="$(printf '%s' "${ACC_RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)-$$}" | tr '[:upper:]' '[:lower:]')"
export ACC_TENANT="${ACC_TENANT:-t-acc21-${TS}}"
export ACC_DATA_DIR="${ACC_DATA_DIR:-$ROOT/.data/t21/$TS}"
export ACC_PORT="${ACC_PORT:-8121}" ACC_UI_PORT="${ACC_UI_PORT:-5421}"
OUT="$ROOT/${ACC_OUT_ROOT:-artifacts/validation/t21}/$TS"; mkdir -p "$OUT/logs"
export ACC_API="http://127.0.0.1:$ACC_PORT" ACC_ENV_OUT="$OUT"
echo "$TS" >"$OUT/run-id"; echo "tenant base: $ACC_TENANT"
trap 'bash backend/tests/acceptance/env.sh stop "$OUT"' EXIT
make up >"$OUT/logs/make-up.log" 2>&1 || { echo "make up failed"; exit 1; }
for _ in $(seq 1 60); do
  [ "$(docker inspect -f '{{.State.Health.Status}}' decision-chat-bot-neo4j-1 2>/dev/null)" = healthy ] && break; sleep 3
done
bash backend/tests/acceptance/env.sh start "$OUT" || exit 1
rc=0
( cd backend && ACC_OUT="$OUT/records" .venv/bin/pytest -o python_files='acc_*.py' ${ACC_PYTEST_ARGS:-tests/acceptance} \
    -p no:cacheprovider -ra --junitxml="$OUT/junit.xml" ) 2>&1 | grep -v "GqlStatusObject\|Received notification" | tee "$OUT/pytest.log"
[ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
if [ "${ACC_SKIP_UI:-0}" != 1 ]; then
  ( cd frontend && E2E_TENANT="$ACC_TENANT" E2E_API="$ACC_API" E2E_PORT="$ACC_UI_PORT" ACC_UI_OUT="$OUT/ui" \
      ACC_UI_JSON="$OUT/ui-results.json" ACC_RECORDS="$OUT/records/records.jsonl" npx playwright test -c playwright.acceptance.config.ts ${ACC_UI_ARGS:-} ) 2>&1 \
    | grep -v "WebServer\|React Router" | tee "$OUT/ui.log"
  [ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
fi
echo "evidence: $OUT (exit $rc)"
exit $rc
