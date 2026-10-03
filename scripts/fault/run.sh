#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "$0")/../.." && pwd)"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
evidence="$root/artifacts/validation/t22/$stamp"
container="jevtriage-fault-neo4j"
mkdir -p "$evidence" "$root/.data/neo4j-fault"

cleanup() {
  docker unpause "$container" >/dev/null 2>&1 || true
  docker rm -f "$container" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

if docker container inspect "$container" >/dev/null 2>&1; then
  echo "Dedicated fault container already exists: $container" >&2
  exit 1
fi
docker run -d --name "$container" -p 127.0.0.1:7688:7687 \
  -e NEO4J_AUTH=neo4j/development-only \
  -v "$root/.data/neo4j-fault:/data" neo4j:5.26.0-community >"$evidence/container-id.txt"
for attempt in $(seq 1 90); do
  if docker exec "$container" cypher-shell -u neo4j -p development-only 'RETURN 1' >/dev/null 2>&1; then
    break
  fi
  if [ "$attempt" -eq 90 ]; then
    echo "Dedicated Neo4j did not become ready" >&2
    exit 1
  fi
  sleep 1
done
export NEO4J_URI=bolt://localhost:7688
export NEO4J_PASSWORD=development-only
export JEV_MODE=mock
export T22_EVIDENCE_DIR="$evidence"
export DATA_DIR="$evidence/data"
export T22_FAULT_CONTAINER="$container"
cd "$root/backend"
set +e
.venv/bin/pytest -q tests/fault/scenarios.py --tb=short \
  --junitxml="$evidence/junit.xml" "$@" 2>&1 | tee "$evidence/pytest.log"
result=${PIPESTATUS[0]}
set -e
"$root/backend/.venv/bin/python" "$root/scripts/fault/report.py" "$evidence"
exit "$result"
