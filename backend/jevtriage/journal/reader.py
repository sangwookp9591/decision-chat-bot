"""Read complete journal lines with byte offsets, leaving partial lines for later."""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

from jevtriage.journal.writer import REQUIRED_FIELDS


def journal_files(directory: Path) -> list[Path]:
    return sorted(directory.glob("archive-*.jsonl")) + sorted(directory.glob("current.jsonl"))


def records(path: Path, offset: int = 0) -> Iterator[tuple[int, dict | None]]:
    with path.open("rb") as stream:
        stream.seek(offset)
        while line := stream.readline():
            if not line.endswith(b"\n"):
                break
            position = stream.tell()
            try:
                value = json.loads(line)
                if not isinstance(value, dict) or not REQUIRED_FIELDS <= value.keys():
                    raise ValueError("invalid journal record")
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
                value = None
            yield position, value


def producer_heartbeat(data_dir: Path, role: str, failure_count: int) -> None:
    directory = Path(data_dir) / "metrics"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{role}-heartbeat.json"
    temp = directory / f".{role}-{os.getpid()}.tmp"
    temp.write_text(json.dumps({"ts": datetime.now(UTC).isoformat(),
                                "journal_write_failures": failure_count}), encoding="utf-8")
    os.replace(temp, path)
