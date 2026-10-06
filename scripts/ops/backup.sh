#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
BACKUP_DIR=""; CONTAINER=""; PROJECT=""; PORT=""; NEO4J_VOLUME=""; DATA_DIR="${DATA_DIR:-$ROOT/.data}"
while (($#)); do
  case "$1" in
    --backup-dir) BACKUP_DIR="${2:?}"; shift 2 ;;
    --container) CONTAINER="${2:?}"; shift 2 ;;
    --project) PROJECT="${2:?}"; shift 2 ;;
    --port) PORT="${2:?}"; shift 2 ;;
    --neo4j-volume) NEO4J_VOLUME="${2:?}"; shift 2 ;;
    --data-dir) DATA_DIR="${2:?}"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done
if [[ -z "$BACKUP_DIR" || -z "$CONTAINER" || -z "$PROJECT" || -z "$PORT" || -z "$NEO4J_VOLUME" ]]; then
  echo "Usage: backup.sh --backup-dir DIR --container NAME --project ildongi-backup --port 7689 --neo4j-volume DIR [--data-dir DIR]" >&2; exit 2
fi
if [[ "$PROJECT" != ildongi-backup || "$PORT" != 7689 || "$CONTAINER" == decision-chat-bot-neo4j-1 ]]; then
  echo "Refusing non-dedicated backup target; require project ildongi-backup, port 7689, and its own container." >&2; exit 2
fi
if ! docker inspect "$CONTAINER" >/dev/null 2>&1; then echo "Dedicated container not found: $CONTAINER" >&2; exit 2; fi
actual_project="$(docker inspect --format '{{ index .Config.Labels "com.docker.compose.project" }}' "$CONTAINER")"
actual_port="$(docker inspect --format '{{ (index (index .HostConfig.PortBindings "7687/tcp") 0).HostPort }}' "$CONTAINER")"
actual_volume="$(docker inspect --format '{{range .Mounts}}{{if eq .Destination "/data"}}{{.Source}}{{end}}{{end}}' "$CONTAINER")"
if [[ "$actual_project" != "$PROJECT" || "$actual_port" != "$PORT" || "$(basename "$CONTAINER")" == decision-chat-bot-neo4j-1 ]]; then
  echo "Refusing target with mismatched Compose project or Bolt port." >&2; exit 2
fi
canonical() { (cd "$1" && pwd -P); }
if [[ ! -d "$NEO4J_VOLUME" || "$(canonical "$actual_volume")" != "$(canonical "$NEO4J_VOLUME")" ]]; then
  echo "Container /data mount does not match --neo4j-volume." >&2; exit 2
fi
while IFS= read -r shared_id; do
  [[ -n "$shared_id" ]] || continue
  shared_volume="$(docker inspect --format '{{range .Mounts}}{{if eq .Destination "/data"}}{{.Source}}{{end}}{{end}}' "$shared_id")"
  if [[ -n "$shared_volume" && "$(canonical "$shared_volume")" == "$(canonical "$NEO4J_VOLUME")" ]]; then
    echo "Refusing backup: a running decision-chat-bot Compose database uses this data volume." >&2; exit 2
  fi
done < <(docker ps -q --filter label=com.docker.compose.project=decision-chat-bot)
if [[ "$(docker inspect --format '{{.State.Running}}' "$CONTAINER")" != true ]]; then
  echo "Dedicated Neo4j container must be running before the script can stop it cleanly." >&2; exit 2
fi
if [[ -e "$BACKUP_DIR" && -n "$(find "$BACKUP_DIR" -mindepth 1 -maxdepth 1 -print -quit)" ]]; then
  echo "Backup destination must be empty: $BACKUP_DIR" >&2; exit 2
fi
mkdir -p "$BACKUP_DIR/neo4j" "$BACKUP_DIR/data"
chmod 700 "$BACKUP_DIR" "$BACKUP_DIR/neo4j" "$BACKUP_DIR/data"
echo "Stopping dedicated Neo4j container $CONTAINER for offline dump." >&2
docker stop "$CONTAINER" >/dev/null
# Community Edition dump requires the database offline. The read/write mount is
# needed because neo4j-admin checks its database lock; the source remains offline.
chmod 777 "$BACKUP_DIR/neo4j"
docker run --rm --user neo4j \
  -v "$(canonical "$NEO4J_VOLUME"):/data" \
  -v "$(canonical "$BACKUP_DIR/neo4j"):/backups" \
  neo4j:5.26.0-community \
  neo4j-admin database dump neo4j --to-path=/backups
chmod 700 "$BACKUP_DIR/neo4j"
for item in files journal metrics alerts; do
  if [[ -e "$DATA_DIR/$item" ]]; then tar -C "$DATA_DIR" -czf "$BACKUP_DIR/data/$item.tar.gz" "$item"; fi
done
(
  cd "$BACKUP_DIR"
  if command -v sha256sum >/dev/null 2>&1; then
    find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS
  else
    find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 shasum -a 256 > SHA256SUMS
  fi
)
echo "Backup created at $BACKUP_DIR; dedicated Neo4j remains stopped."
echo "Restart with: NEO4J_BOLT_PORT=7689 docker compose -p $PROJECT -f docker-compose.yml -f scripts/ops/compose.backup.yml up -d neo4j"
