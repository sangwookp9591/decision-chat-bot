#!/usr/bin/env python3
"""Read root .env without shell evaluation; keys remain env references in the profile."""

import os
import re
import shutil
import sys
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[2]


def main():
    action = sys.argv[1] if len(sys.argv) == 2 else ""
    if action not in {"init", "doctor", "run"}:
        raise SystemExit("사용법: backend/.venv/bin/python scripts/mcp/tunnel.py init|doctor|run")
    values = dotenv_values(ROOT / ".env", interpolate=False)
    env = os.environ.copy()
    for name in ("CONTROL_PLANE_API_KEY", "CONTROL_PLANE_TUNNEL_ID"):
        if not values.get(name):
            raise SystemExit(f"루트 .env에 {name}를 입력하세요. Platform 터널 설정에서 발급합니다.")
        env[name] = values[name]
    if not re.fullmatch(r"tunnel_[0-9a-f]{32}", env["CONTROL_PLANE_TUNNEL_ID"]):
        raise SystemExit("CONTROL_PLANE_TUNNEL_ID 형식 오류: tunnel_ 뒤 소문자 16진수 32자여야 합니다.")
    candidates = sorted((ROOT / ".data/bin/tunnel-client-release").rglob("tunnel-client"))
    binary = shutil.which("tunnel-client") or (str(candidates[0]) if candidates else None)
    if not binary:
        raise SystemExit("먼저 bash scripts/mcp/install.sh 또는 brew install openai/tools/tunnel-client를 실행하세요.")
    try:
        port = int(values.get("MCP_PORT") or 8787)
        if not 1 <= port <= 65535:
            raise ValueError
    except ValueError:
        raise SystemExit("MCP_PORT는 1~65535 정수여야 합니다.") from None
    profile_dir = ROOT / ".data/mcp-tunnel"
    profile_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    env["TUNNEL_CLIENT_PROFILE_DIR"] = str(profile_dir)
    command = [binary, action, "--profile", "ildongi-dev"]
    if action == "init":
        command += ["--sample", "sample_mcp_remote_no_auth", "--tunnel-id",
                    env["CONTROL_PLANE_TUNNEL_ID"], "--mcp-server-url", f"http://127.0.0.1:{port}/mcp"]
    elif action == "doctor":
        command += ["--explain"]
    # No shell sourcing, command echo, or literal API key argument/profile value.
    os.execve(binary, command, env)


if __name__ == "__main__":
    main()
