"""Journal write failure counter shared by batching and API heartbeat readers."""

import json
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock

_failure_count = 0
_count_lock = Lock()


def failure_count() -> int:
    with _count_lock:
        return _failure_count


def record_failure(directory: Path, exc: OSError) -> None:
    global _failure_count
    with _count_lock:
        _failure_count += 1
        count = _failure_count
    try:
        signal_dir = directory.parent / "metrics"
        signal_dir.mkdir(parents=True, exist_ok=True)
        path = signal_dir / "journal-writer-failure.json"
        path.write_text(json.dumps({"ts": datetime.now(UTC).isoformat(),
                                    "journal_write_failures": count,
                                    "error_class": type(exc).__name__}), encoding="utf-8")
    except OSError:
        pass
