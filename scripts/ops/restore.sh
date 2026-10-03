#!/usr/bin/env bash
set -euo pipefail
BACKUP_DIR=""; NEW_DATA=""; NEW_NEO4J=""; CONTAINER=""; PROJECT=""; PORT=""
while (($#)); do
  case "$1" in
    --backup-dir) BACKUP_DIR="${2:?}"; shift 2 ;;
    --new-data-dir) NEW_DATA="${2:?}"; shift 2 ;;
    --new-neo4j-dir) NEW_NEO4J="${2:?}"; shift 2 ;;
    --container) CONTAINER="${2:?}"; shift 2 ;;
    --project) PROJECT="${2:?}"; shift 2 ;;
    --port) PORT="${2:?}"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done
if [[ -z "$BACKUP_DIR" || -z "$NEW_DATA" || -z "$CONTAINER" || -z "$PROJECT" || -z "$PORT" ]]; then
  echo "Usage: restore.sh --backup-dir DIR --new-data-dir DIR --container NAME --project jevtriage-backup --port 7689 [--new-neo4j-dir DIR]" >&2; exit 2
fi
if [[ "$PROJECT" != jevtriage-backup || "$PORT" != 7689 || "$CONTAINER" == decision-chat-bot-neo4j-1 ]]; then
  echo "Refusing non-dedicated restore target; require project jevtriage-backup, port 7689, and its own container." >&2; exit 2
fi
if ! docker inspect "$CONTAINER" >/dev/null 2>&1; then echo "Dedicated container not found: $CONTAINER" >&2; exit 2; fi
actual_project="$(docker inspect --format '{{ index .Config.Labels "com.docker.compose.project" }}' "$CONTAINER")"
actual_port="$(docker inspect --format '{{ (index (index .HostConfig.PortBindings "7687/tcp") 0).HostPort }}' "$CONTAINER")"
if [[ "$actual_project" != "$PROJECT" || "$actual_port" != "$PORT" ]]; then
  echo "Refusing target with mismatched Compose project or Bolt port." >&2; exit 2
fi
if [[ ! -d "$BACKUP_DIR" || ! -f "$BACKUP_DIR/neo4j/neo4j.dump" || ! -f "$BACKUP_DIR/SHA256SUMS" ]]; then
  echo "Backup directory, neo4j.dump, or SHA256SUMS missing" >&2; exit 2
fi
if command -v sha256sum >/dev/null 2>&1; then (cd "$BACKUP_DIR" && sha256sum -c SHA256SUMS >/dev/null)
else (cd "$BACKUP_DIR" && shasum -a 256 -c SHA256SUMS >/dev/null); fi
if [[ -e "$NEW_DATA" && -n "$(find "$NEW_DATA" -mindepth 1 -maxdepth 1 -print -quit)" ]]; then
  echo "Refusing to restore into non-empty destination: $NEW_DATA" >&2; exit 2
fi
NEW_NEO4J="${NEW_NEO4J:-$NEW_DATA/neo4j}"
mkdir -p "$NEW_DATA" "$NEW_NEO4J"
chmod 700 "$NEW_DATA"
canonical_neo4j="$(cd "$NEW_NEO4J" && pwd -P)"
while IFS= read -r running_id; do
  [[ -n "$running_id" ]] || continue
  mounted_volume="$(docker inspect --format '{{range .Mounts}}{{if eq .Destination "/data"}}{{.Source}}{{end}}{{end}}' "$running_id")"
  if [[ -n "$mounted_volume" && "$(cd "$mounted_volume" && pwd -P)" == "$canonical_neo4j" ]]; then
    echo "Refusing restore: a running container already uses the target Neo4j data directory." >&2
    exit 2
  fi
done < <(docker ps -q)
if [[ "$(docker inspect --format '{{.State.Running}}' "$CONTAINER")" == true ]]; then
  echo "Stop the dedicated target container before restoring." >&2; exit 2
fi
chmod 777 "$NEW_NEO4J"
for archive in "$BACKUP_DIR"/data/*.tar.gz; do [[ -e "$archive" ]] || continue; tar -xzf "$archive" -C "$NEW_DATA"; done
docker run --rm --user neo4j \
  -v "$(cd "$NEW_NEO4J" && pwd -P):/data" \
  -v "$(cd "$BACKUP_DIR/neo4j" && pwd -P):/backups:ro" \
  neo4j:5.26.0-community \
  neo4j-admin database load neo4j --from-path=/backups
chmod 700 "$NEW_NEO4J"
printf 'Restored files and Neo4j database under %s (Neo4j data: %s).\n' "$NEW_DATA" "$NEW_NEO4J"
printf 'Neo4j dump excludes system users/roles; recreate auth and verify schema before service use.\n'
