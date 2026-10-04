"""Bounded, process-local journal batching with process-safe file commits."""

from __future__ import annotations

import fcntl
import os
import queue
import threading
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

from jevtriage.journal.failure import record_failure


@dataclass
class DurableLine:
    line: bytes
    completed: threading.Event = field(default_factory=threading.Event)
    error: OSError | None = None


class GroupCommit:
    def __init__(self, directory: Path, max_bytes: int, *, queue_size: int,
                 batch_size: int, flush_interval: float):
        self.directory = directory
        self.max_bytes = max_bytes
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.queue: queue.Queue[bytes | DurableLine | threading.Event] = queue.Queue(queue_size)
        self.file_lock = threading.Lock()
        self.error: OSError | None = None
        self.thread = threading.Thread(target=self._run, name="journal-group-commit", daemon=True)
        self.thread.start()

    def append(self, line: bytes, *, durable: bool = False) -> bool:
        if self.error is not None:
            self._write_batch([line])
            self.error = None
            return True
        if durable:
            item = DurableLine(line)
            self.queue.put(item)
            item.completed.wait()
            if item.error is not None:
                raise item.error
            return True
        try:
            self.queue.put_nowait(line)
            return False
        except queue.Full:
            self._write_batch([line])
            return True

    def flush(self) -> None:
        if self.error is not None:
            raise self.error
        barrier = threading.Event()
        self.queue.put(barrier)
        barrier.wait()
        if self.error is not None:
            raise self.error

    def _run(self) -> None:
        while True:
            first = self.queue.get()
            batch: list[bytes] = []
            durable_items: list[DurableLine] = []
            barrier = None
            if isinstance(first, bytes):
                batch.append(first)
            elif isinstance(first, DurableLine):
                batch.append(first.line)
                durable_items.append(first)
            else:
                barrier = first
            while barrier is None and len(batch) < self.batch_size:
                try:
                    item = self.queue.get(timeout=self.flush_interval)
                except queue.Empty:
                    break
                if isinstance(item, bytes):
                    batch.append(item)
                elif isinstance(item, DurableLine):
                    batch.append(item.line)
                    durable_items.append(item)
                else:
                    barrier = item
            if batch and self.error is None:
                try:
                    self._write_batch(batch)
                except OSError as exc:
                    self.error = exc
            for item in durable_items:
                item.error = self.error
                item.completed.set()
            if barrier is not None:
                barrier.set()

    def _signal_failure(self, exc: OSError) -> None:
        record_failure(self.directory, exc)

    def _write_batch(self, batch: list[bytes]) -> None:
        with self.file_lock:
            try:
                self.directory.mkdir(parents=True, exist_ok=True)
                lock_fd = os.open(self.directory / ".append.lock", os.O_CREAT | os.O_RDWR, 0o600)
                try:
                    fcntl.flock(lock_fd, fcntl.LOCK_EX)
                    self._write_locked(batch)
                finally:
                    fcntl.flock(lock_fd, fcntl.LOCK_UN)
                    os.close(lock_fd)
            except OSError as exc:
                self._signal_failure(exc)
                raise

    def _write_locked(self, batch: list[bytes]) -> None:
        path = self.directory / "current.jsonl"
        size = path.stat().st_size if path.exists() else 0
        pending: list[bytes] = []

        def commit() -> None:
            if not pending:
                return
            fd = os.open(path, os.O_CREAT | os.O_WRONLY | os.O_APPEND, 0o600)
            try:
                payload = b"".join(pending)
                written = os.write(fd, payload)
                if written != len(payload):
                    raise OSError("short journal write")
                os.fsync(fd)
            finally:
                os.close(fd)
            pending.clear()

        for line in batch:
            if size + len(line) > self.max_bytes:
                commit()
                if path.exists():
                    os.replace(path, self.directory / f"archive-{uuid4().hex}.jsonl")
                    dir_fd = os.open(self.directory, os.O_RDONLY)
                    try:
                        os.fsync(dir_fd)
                    finally:
                        os.close(dir_fd)
                size = 0
            pending.append(line)
            size += len(line)
        commit()
