"""Process-safe append-only JSONL writer independent of Neo4j."""

import fcntl
import json
import os
from pathlib import Path
from threading import Lock
from uuid import uuid4

from jevtriage.config import get_settings

ALLOWED_FIELDS = frozenset({
    "event_id", "attempt_id", "request_id", "run_id", "kind", "ts", "status_code",
    "error_class", "duration_ms", "validity",
    "tenant_id", "org_id", "revision_id", "eligible_first", "first_supported_revision",
    "file_count", "excluded_file_count", "exclusion_reasons", "config_version",
    "model_version", "qset_version", "run_kind", "review_id", "input_type",
    "complete_judgment", "received_at", "step_name", "journal_write_failures",
    "judgment_committed_at",
    "org_ids", "request_status",
})
REQUIRED_FIELDS = frozenset({"event_id", "attempt_id", "kind", "ts"})
_failure_count = 0
_count_lock = Lock()


def failure_count() -> int:
    with _count_lock:
        return _failure_count


class JournalWriter:
    def __init__(self, data_dir: Path | None = None, max_bytes: int = 16 * 1024 * 1024):
        if max_bytes < 1:
            raise ValueError("max_bytes must be positive")
        self.directory = Path(data_dir or get_settings().data_dir) / "journal"
        self.max_bytes = max_bytes

    def append(self, record: dict) -> None:
        global _failure_count
        if not isinstance(record, dict) or not REQUIRED_FIELDS <= record.keys() or not record.keys() <= ALLOWED_FIELDS:
            raise ValueError("journal record has missing or forbidden fields")
        line = (json.dumps(record, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
        if len(line) > self.max_bytes:
            raise ValueError("journal record exceeds max_bytes")
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            lock_fd = os.open(self.directory / ".append.lock", os.O_CREAT | os.O_RDWR, 0o600)
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_EX)
                path = self.directory / "current.jsonl"
                if path.exists() and path.stat().st_size + len(line) > self.max_bytes:
                    os.replace(path, self.directory / f"archive-{uuid4().hex}.jsonl")
                    dir_fd = os.open(self.directory, os.O_RDONLY)
                    try:
                        os.fsync(dir_fd)
                    finally:
                        os.close(dir_fd)
                fd = os.open(path, os.O_CREAT | os.O_WRONLY | os.O_APPEND, 0o600)
                try:
                    written = os.write(fd, line)
                    if written != len(line):
                        raise OSError("short journal write")
                    os.fsync(fd)
                finally:
                    os.close(fd)
            finally:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
                os.close(lock_fd)
        except OSError:
            with _count_lock:
                _failure_count += 1
            raise
