"""Process-safe append-only JSONL writer independent of Neo4j."""

import atexit
import json
import multiprocessing.util
import os
from pathlib import Path
from threading import Lock

from ildongi.config import get_settings
from ildongi.journal.failure import failure_count as _failure_count_value
from ildongi.journal.group_commit import GroupCommit

ALLOWED_FIELDS = frozenset({
    "event_id", "attempt_id", "request_id", "run_id", "kind", "ts", "status_code",
    "error_class", "duration_ms", "validity",
    "tenant_id", "org_id", "revision_id", "eligible_first", "first_supported_revision",
    "file_count", "excluded_file_count", "exclusion_reasons", "config_version",
    "model_version", "qset_version", "run_kind", "review_id", "input_type",
    "complete_judgment", "received_at", "step_name", "journal_write_failures",
    "judgment_committed_at",
    "org_ids", "request_status", "time_to_preliminary_ms", "time_to_evidence_ms", "time_to_tasks_ms",
})
REQUIRED_FIELDS = frozenset({"event_id", "attempt_id", "kind", "ts"})
DURABLE_KINDS = frozenset({
    "request_received", "request_completed", "request_failed",
    "lookup_received", "lookup_completed", "lookup_failed",
    "eligibility_received", "eligibility_completed", "eligibility_failed",
    "revision_received", "revision_completed", "revision_failed",
    "worker_attempt_start", "worker_attempt_failure", "worker_run", "ownership_lost",
    "judgment_preliminary", "judgment_committed", "retention_cleanup",
})
_groups: dict[tuple, GroupCommit] = {}
_groups_lock = Lock()


def failure_count() -> int:
    return _failure_count_value()


def _reset_after_fork() -> None:
    global _groups, _groups_lock
    _groups = {}
    _groups_lock = Lock()


os.register_at_fork(after_in_child=_reset_after_fork)
atexit.register(lambda: flush_all())


class JournalWriter:
    def __init__(self, data_dir: Path | None = None, max_bytes: int = 16 * 1024 * 1024,
                 *, queue_size: int = 1024, batch_size: int = 64,
                 flush_interval: float = 0.005,
                 raise_on_background_error: bool = False):
        if max_bytes < 1 or queue_size < 1 or batch_size < 1 or flush_interval <= 0:
            raise ValueError("journal limits must be positive")
        self.directory = Path(data_dir or get_settings().data_dir) / "journal"
        self.max_bytes = max_bytes
        self.raise_on_background_error = raise_on_background_error
        key = (str(self.directory.resolve()), max_bytes, queue_size, batch_size, flush_interval)
        with _groups_lock:
            if key not in _groups:
                _groups[key] = GroupCommit(self.directory, max_bytes, queue_size=queue_size,
                                           batch_size=batch_size, flush_interval=flush_interval)
                multiprocessing.util.Finalize(_groups[key], flush_all, exitpriority=10)
            self._group = _groups[key]

    def append(self, record: dict) -> None:
        if not isinstance(record, dict) or not REQUIRED_FIELDS <= record.keys() or not record.keys() <= ALLOWED_FIELDS:
            raise ValueError("journal record has missing or forbidden fields")
        line = (json.dumps(record, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
        if len(line) > self.max_bytes:
            raise ValueError("journal record exceeds max_bytes")
        if self.raise_on_background_error and self._group.error is not None:
            raise self._group.error
        self._group.append(line, durable=record["kind"] in DURABLE_KINDS)

    def flush(self) -> None:
        self._group.flush()

    def close(self) -> None:
        self.flush()


def flush_all() -> None:
    with _groups_lock:
        groups = list(_groups.values())
    for group in groups:
        try:
            group.flush()
        except OSError:
            pass  # Failure was already counted and signaled by the writer.
