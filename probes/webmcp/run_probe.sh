#!/bin/sh
set -eu

chrome="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
if [ ! -x "$chrome" ]; then
  echo "Google Chrome is not installed at the expected path" >&2
  exit 2
fi
mode=${1:-enabled}
case "$mode" in
  enabled) feature_flags=--enable-features=WebMCP; query='?selfTest=1' ;;
  unsupported) feature_flags=--disable-features=WebMCP; query='' ;;
  *) echo "Usage: $0 [enabled|unsupported]" >&2; exit 2 ;;
esac
probe_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
profile=$(mktemp -d "${TMPDIR:-/tmp}/webmcp-probe.XXXXXX")
trap 'rm -rf "$profile"' EXIT
"$chrome" --headless --no-sandbox --disable-gpu --no-first-run \
  --user-data-dir="$profile" "$feature_flags" \
  --virtual-time-budget=5000 --dump-dom "file://$probe_dir/index.html$query"
