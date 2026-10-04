"""Durability and concurrency contracts for grouped journal writes."""

import json
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest.mock import patch

import pytest

from jevtriage.journal.writer import JournalWriter, failure_count


def record(index):
    return {"event_id": f"e{index}", "attempt_id": "a", "kind": "received", "ts": "now"}


def lines(directory):
    return [json.loads(line) for path in (directory / "journal").glob("*.jsonl")
            for line in path.read_text().splitlines()]


def test_group_commit_batches_fsync_and_flushes(tmp_path):
    writer = JournalWriter(tmp_path, batch_size=100, flush_interval=10)
    with patch("jevtriage.journal.group_commit.os.fsync", wraps=__import__("os").fsync) as sync:
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(writer.append, map(record, range(80))))
        writer.flush()
    assert len(lines(tmp_path)) == 80
    assert sync.call_count < 80


def test_full_queue_falls_back_to_caller(tmp_path):
    from queue import Full

    writer = JournalWriter(tmp_path, queue_size=1, batch_size=100, flush_interval=10)
    with patch.object(writer._group.queue, "put_nowait", side_effect=Full):
        writer.append(record(1))
    assert [row["event_id"] for row in lines(tmp_path)] == ["e1"]


def test_background_failure_increments_counter_and_signals(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "journal").write_text("occupied")
    writer = JournalWriter(data_dir, raise_on_background_error=True)
    before = failure_count()
    writer.append(record(1))
    with pytest.raises(OSError):
        writer.flush()
    assert failure_count() == before + 1
    assert (data_dir / "metrics" / "journal-writer-failure.json").exists()
    with pytest.raises(OSError):
        writer.append(record(2))


def test_close_flushes_pending_records(tmp_path):
    writer = JournalWriter(tmp_path, batch_size=100, flush_interval=10)
    writer.append(record(1))
    writer.close()
    assert [row["event_id"] for row in lines(tmp_path)] == ["e1"]


def test_business_outcome_is_durable_when_append_returns(tmp_path):
    writer = JournalWriter(tmp_path, batch_size=100, flush_interval=10)
    outcome = {**record(2), "kind": "worker_run"}
    writer.append(outcome)
    assert [row["event_id"] for row in lines(tmp_path)] == ["e2"]


def test_business_outcome_reports_write_failure_before_return(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "journal").write_text("occupied")
    writer = JournalWriter(data_dir)
    before = failure_count()
    with pytest.raises(OSError):
        writer.append({**record(3), "kind": "worker_run"})
    assert failure_count() == before + 1


def test_business_outcome_waits_for_fsync(tmp_path):
    writer = JournalWriter(tmp_path)
    entered = Event()
    release = Event()
    real_fsync = os.fsync

    def slow_fsync(fd):
        entered.set()
        assert release.wait(2)
        real_fsync(fd)

    with (patch("jevtriage.journal.group_commit.os.fsync", side_effect=slow_fsync),
          ThreadPoolExecutor(max_workers=1) as pool):
        future = pool.submit(writer.append, {**record(4), "kind": "worker_run"})
        try:
            assert entered.wait(2)
            assert not future.done()
        finally:
            release.set()
        future.result(timeout=2)
