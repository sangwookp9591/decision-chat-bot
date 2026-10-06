"""Out-of-band collector, producer, disk and error-budget watchdog."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import time
from datetime import UTC, datetime
from pathlib import Path

from ildongi.config import get_settings
from ildongi.monitoring.aggregates import collection_status, events_between
from ildongi.monitoring.alerts import emit
from ildongi.monitoring.slo import error_budget


def check_once(data_dir: Path | None = None, *, stale_seconds: int = 30,
               min_free_bytes: int = 100 * 1024 * 1024,
               webhook_url: str | None = None) -> list[dict]:
    from datetime import timedelta

    data_dir = Path(data_dir or get_settings().data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(UTC)
    state_path = data_dir / "alerts" / "watchdog-state.json"
    try:
        previous = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        previous = {}
    current: dict[str, object] = {}
    alerts = []

    def trigger(kind: str, detail: dict) -> None:
        current[kind] = detail
        if previous.get(kind) != detail:
            alerts.append(emit(kind, detail, data_dir=data_dir, webhook_url=webhook_url))

    status = collection_status(data_dir, now=now, stale_seconds=stale_seconds)
    if "collector_stopped" in status["issues"] or "invalid_collector_heartbeat" in status["issues"]:
        trigger("collector_stopped", {"last_collected_at": status["last_collected_at"]})
    if "metrics_store_unavailable" in status["issues"]:
        trigger("metrics_store_unavailable", {})
    # Producers can publish their own heartbeat and write-failure counter files.
    for role in ("api", "worker"):
        path = data_dir / "metrics" / f"{role}-heartbeat.json"
        if path.exists():
            try:
                beat = json.loads(path.read_text(encoding="utf-8"))
                if (now - datetime.fromisoformat(beat["ts"])).total_seconds() > stale_seconds:
                    trigger(f"{role}_stopped", {"last_seen": beat["ts"]})
                failures = int(beat.get("journal_write_failures", 0))
                prior = int(previous.get(f"{role}_write_count", 0))
                if failures > prior or (failures > 0 and failures < prior):
                    trigger("journal_write_failure", {"producer": role, "count": failures,
                                                      "counter_reset": failures < prior})
                current[f"{role}_write_count"] = failures
            except (OSError, ValueError, KeyError):
                trigger(f"{role}_heartbeat_invalid", {})
    free = shutil.disk_usage(data_dir).free
    if free < min_free_bytes:
        trigger("disk_low", {"free_bytes": free, "threshold_bytes": min_free_bytes})
    if (data_dir / "metrics" / "metrics.db").exists():
        try:
            rows = events_between(data_dir, now - timedelta(days=30), now)
            budget = error_budget(rows, now=now, collection_complete=status["continuous_30d"])
            rate = budget["availability"]["burn_rate_1h"]
            if rate is not None and rate >= 10:
                trigger("fast_budget_burn", {"burn_rate_1h": round(rate, 2)})
            judgment_rate = budget["first_judgment"]["burn_rate_1h"]
            if judgment_rate is not None and judgment_rate >= 10:
                trigger("fast_judgment_budget_burn", {"burn_rate_1h": round(judgment_rate, 2)})
            failures = {r["attempt_id"] for r in rows if r.get("error_class") and
                        datetime.fromisoformat(r["ts"]) > now - timedelta(minutes=5)}
            if len(failures) >= 3:
                trigger("repeated_failures", {"count": len(failures)})
        except (sqlite3.Error, ValueError):
            trigger("metrics_store_unavailable", {})
    try:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        temp = state_path.with_suffix(".tmp")
        temp.write_text(json.dumps(current), encoding="utf-8")
        os.replace(temp, state_path)
    except OSError as exc:
        print(json.dumps({"watchdog_state_error": type(exc).__name__}), flush=True)
    return alerts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", type=float, default=10)
    parser.add_argument("--stale-seconds", type=int, default=30)
    args = parser.parse_args()
    if args.interval <= 0:
        parser.error("interval must be positive")
    while True:
        check_once(stale_seconds=args.stale_seconds,
                   webhook_url=os.getenv("MONITORING_WEBHOOK_URL"))
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
