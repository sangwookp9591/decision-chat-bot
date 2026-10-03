"""Alert transport independent of the business database and journal."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import Request, urlopen
from uuid import uuid4

from jevtriage.config import get_settings


def emit(kind: str, detail: dict, *, data_dir: Path | None = None,
         webhook_url: str | None = None) -> dict:
    directory = Path(data_dir or get_settings().data_dir) / "alerts"
    alert = {"id": f"alert_{uuid4().hex}", "kind": kind,
             "ts": datetime.now(UTC).isoformat(), "detail": detail}
    print(json.dumps(alert), flush=True)
    path = directory / f"{alert['id']}.json"
    try:
        directory.mkdir(parents=True, exist_ok=True)
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        try:
            os.write(fd, json.dumps(alert, separators=(",", ":")).encode())
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError as exc:
        print(json.dumps({"alert_storage_error": type(exc).__name__}), flush=True)
    if webhook_url:
        request = Request(webhook_url, json.dumps(alert).encode(),
                          {"Content-Type": "application/json"}, method="POST")
        try:
            with urlopen(request, timeout=5) as response:
                response.read()
        except OSError as exc:
            print(json.dumps({"alert_delivery_error": type(exc).__name__}), flush=True)
    return alert


def list_alerts(data_dir: Path | None = None, limit: int = 100) -> list[dict]:
    directory = Path(data_dir or get_settings().data_dir) / "alerts"
    result = []
    for path in sorted(directory.glob("alert_*.json"), reverse=True)[:limit]:
        try:
            result.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            continue
    return result
