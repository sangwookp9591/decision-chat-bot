import json
from multiprocessing import Process
from pathlib import Path

import pytest

from jevtriage.domain.models import RequestStatus, RunStatus
from jevtriage.domain.transitions import InvalidTransition, assert_transition
from jevtriage.journal.writer import JournalWriter


def _write_batch(directory: str, worker: int, count: int) -> None:
    writer = JournalWriter(Path(directory), max_bytes=512)
    for index in range(count):
        writer.append({"event_id": f"e{worker}-{index}", "attempt_id": f"a{worker}", "kind": "received", "ts": "2026-10-03T00:00:00Z"})


def test_transitions():
    assert_transition(RequestStatus.RECEIVED, RequestStatus.PROCESSING)
    with pytest.raises(InvalidTransition):
        assert_transition(RequestStatus.ASSIGNED, RequestStatus.RECEIVED)
    with pytest.raises(InvalidTransition):
        assert_transition(RunStatus.JUDGMENT_SAVED, RunStatus.RUNNING)


def test_multiprocess_journal_and_forbidden_fields(tmp_path):
    workers = [Process(target=_write_batch, args=(str(tmp_path), i, 25)) for i in range(4)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=15)
        assert worker.exitcode == 0
    lines = [line for path in (tmp_path / "journal").glob("*.jsonl") for line in path.read_text().splitlines()]
    assert len(lines) == 100
    assert len({json.loads(line)["event_id"] for line in lines}) == 100
    with pytest.raises(ValueError):
        JournalWriter(tmp_path).append({"event_id": "x", "attempt_id": "y", "kind": "z", "ts": "now", "api_key": "secret"})
