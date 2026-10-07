#!/bin/bash
# Official macOS arm64 release; leaves the bundled companion beside the executable.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
if [[ "$(uname -s)" != Darwin || "$(uname -m)" != arm64 ]]; then
  echo '이 설치 스크립트는 macOS arm64 전용입니다.' >&2; exit 1
fi
python3 - "$ROOT" <<'PY'
import hashlib
import io
import json
import sys
import urllib.request
import zipfile
from pathlib import Path
release = json.load(urllib.request.urlopen('https://api.github.com/repos/openai/tunnel-client/releases/latest', timeout=30))
name = f"tunnel-client-{release['tag_name']}-darwin-arm64.zip"
asset = next(a for a in release['assets'] if a['name'] == name)
raw = urllib.request.urlopen(asset['browser_download_url'], timeout=60).read()
digest = asset.get('digest')
if not digest or digest != 'sha256:' + hashlib.sha256(raw).hexdigest():
    raise SystemExit('공식 릴리스 SHA256 검증에 실패했습니다.')
target = Path(sys.argv[1]) / '.data/bin/tunnel-client-release'
target.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(io.BytesIO(raw)) as archive:
    for entry in archive.infolist():
        path = (target / entry.filename).resolve()
        if not path.is_relative_to(target.resolve()):
            raise SystemExit('릴리스 ZIP 경로 검증에 실패했습니다.')
    archive.extractall(target)
for executable in target.rglob('*'):
    if executable.is_file() and executable.name in {'tunnel-client', 'cloudflared'}:
        executable.chmod(0o755)
print(f"공식 릴리스 {release['tag_name']} 설치 완료: {target}")
PY
# Never bypass Gatekeeper; use the official Homebrew tap if macOS blocks the release.
