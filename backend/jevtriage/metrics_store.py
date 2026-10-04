"""SQLite connection shared by the journal collector and monitoring readers."""

import sqlite3
from pathlib import Path

from jevtriage.config import get_settings


def metrics_path(data_dir: Path | None = None) -> Path:
    return Path(data_dir or get_settings().data_dir) / "metrics" / "metrics.db"


def connect(data_dir: Path | None = None) -> sqlite3.Connection:
    path = metrics_path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=30)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS events (
          event_id TEXT PRIMARY KEY, attempt_id TEXT NOT NULL, request_id TEXT,
          run_id TEXT, kind TEXT NOT NULL, ts TEXT NOT NULL, status_code TEXT,
          error_class TEXT, duration_ms REAL, validity TEXT, payload TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS events_ts ON events(ts);
        CREATE INDEX IF NOT EXISTS events_request ON events(request_id);
        CREATE INDEX IF NOT EXISTS events_attempt ON events(attempt_id);
        CREATE TABLE IF NOT EXISTS offsets (
          file_key TEXT PRIMARY KEY, path TEXT NOT NULL, byte_offset INTEGER NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS collection_issues (
          id INTEGER PRIMARY KEY, file_key TEXT NOT NULL, byte_offset INTEGER NOT NULL,
          kind TEXT NOT NULL, detected_at TEXT NOT NULL,
          UNIQUE(file_key, byte_offset, kind)
        );
        CREATE TABLE IF NOT EXISTS collector_ticks (ts TEXT PRIMARY KEY);
        CREATE TABLE IF NOT EXISTS collection_gaps (
          start_at TEXT PRIMARY KEY, end_at TEXT NOT NULL
        );
    """)
    return db
