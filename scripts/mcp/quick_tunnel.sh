#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
command -v cloudflared >/dev/null || { echo '먼저 brew install cloudflared를 실행하세요.' >&2; exit 1; }
port="${MCP_PORT:-8787}"
[[ "$port" =~ ^[0-9]+$ ]] && (( port >= 1 && port <= 65535 )) || { echo '잘못된 MCP_PORT' >&2; exit 1; }
mkdir -p .data
rm -f .data/mcp-tunnel-url.txt
# Keep SDK Host/DNS-rebinding protection enabled behind the public tunnel.
export TUNNEL_HTTP_HOST_HEADER="127.0.0.1:$port"
cloudflared tunnel --url "http://127.0.0.1:${MCP_PORT:-8787}" --no-autoupdate > .data/mcp-quick-tunnel.log 2>&1 &
tunnel_pid=$!
printf '%s\n' "$tunnel_pid" > .data/mcp-tunnel.pid
cleanup() { kill "$tunnel_pid" 2>/dev/null || true; }
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
for (( attempt=0; attempt<60; attempt++ )); do
  url=$(sed -nE 's@.*(https://[a-z0-9-]+\.trycloudflare\.com).*@\1@p' .data/mcp-quick-tunnel.log | head -n 1)
  if [[ -n "$url" ]]; then
    printf '%s/mcp\n' "$url" > .data/mcp-tunnel-url.txt
    printf 'ChatGPT 서버 URL: %s/mcp\n터널 PID: %s (종료: kill %s)\n' "$url" "$tunnel_pid" "$tunnel_pid"
    wait "$tunnel_pid"
    exit $?
  fi
  kill -0 "$tunnel_pid" 2>/dev/null || { echo '터널 기동 실패: .data/mcp-quick-tunnel.log 확인' >&2; exit 1; }
  sleep 1
done
echo '60초 내 터널 URL이 나오지 않았습니다.' >&2
exit 1
