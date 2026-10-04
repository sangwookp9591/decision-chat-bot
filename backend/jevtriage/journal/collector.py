"""Independent journal-to-SQLite collector. Run with ``python -m``."""

from __future__ import annotations

import argparse
import json
import os
import time
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path

from jevtriage.config import get_settings
from jevtriage.journal.reader import journal_files, records
from jevtriage.metrics_store import connect, metrics_path  # noqa: F401 - public compatibility


def _heartbeat(data_dir: Path, data: dict) -> None:
    path = data_dir / "metrics" / "collector-heartbeat.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    os.replace(temp, path)


def collect_once(data_dir: Path | None = None) -> dict:
    data_dir = Path(data_dir or get_settings().data_dir)
    inserted = damaged = 0
    with closing(connect(data_dir)) as db, db:
        now = datetime.now(UTC)
        previous_tick = db.execute("SELECT ts FROM collector_ticks ORDER BY ts DESC LIMIT 1").fetchone()
        if previous_tick:
            previous = datetime.fromisoformat(previous_tick["ts"])
            if now - previous > timedelta(seconds=30):
                db.execute("INSERT OR IGNORE INTO collection_gaps(start_at,end_at) VALUES(?,?)",
                           (previous.isoformat(), now.isoformat()))
        if not previous_tick or now - datetime.fromisoformat(previous_tick["ts"]) >= timedelta(seconds=10):
            db.execute("INSERT OR IGNORE INTO collector_ticks(ts) VALUES(?)", (now.isoformat(),))
        for path in journal_files(data_dir / "journal"):
            stat = path.stat()
            key = f"{stat.st_dev}:{stat.st_ino}"
            row = db.execute("SELECT byte_offset FROM offsets WHERE file_key=?", (key,)).fetchone()
            offset = int(row[0]) if row else 0
            if stat.st_size < offset:
                db.execute("INSERT OR IGNORE INTO collection_issues(file_key,byte_offset,kind,detected_at) VALUES(?,?,?,?)",
                           (key, offset, "truncated", datetime.now(UTC).isoformat()))
                offset = 0
            for position, record in records(path, offset):
                if record is None:
                    damaged += 1
                    db.execute("INSERT OR IGNORE INTO collection_issues(file_key,byte_offset,kind,detected_at) VALUES(?,?,?,?)",
                               (key, offset, "damaged_line", datetime.now(UTC).isoformat()))
                else:
                    inserted += db.execute("""INSERT OR IGNORE INTO events
                        (event_id,attempt_id,request_id,run_id,kind,ts,status_code,error_class,duration_ms,validity,payload)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                        (record["event_id"], record["attempt_id"], record.get("request_id"),
                         record.get("run_id"), record["kind"], record["ts"],
                         str(record["status_code"]) if record.get("status_code") is not None else None,
                         record.get("error_class"), record.get("duration_ms"),
                         record.get("validity"), json.dumps(record))).rowcount
                offset = position
            db.execute("""INSERT INTO offsets VALUES(?,?,?,?) ON CONFLICT(file_key) DO UPDATE SET
                path=excluded.path,byte_offset=excluded.byte_offset,updated_at=excluded.updated_at""",
                (key, str(path), offset, datetime.now(UTC).isoformat()))
    result = {"ts": datetime.now(UTC).isoformat(), "inserted": inserted, "damaged": damaged}
    _heartbeat(data_dir, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", type=float, default=1.0)
    args = parser.parse_args()
    if args.interval <= 0:
        parser.error("interval must be positive")
    while True:
        collect_once()
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
