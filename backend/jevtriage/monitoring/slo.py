"""Thirty-day SLO and error-budget calculations."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from jevtriage.monitoring.aggregates import parse_time, summarize


def error_budget(rows: list[dict], *, now: datetime | None = None,
                 collection_complete: bool = False) -> dict:
    now = now or datetime.now(UTC)
    window_start = now - timedelta(days=30)
    window = [r for r in rows if window_start <= parse_time(r["ts"]) <= now]
    coverage = collection_complete
    summary = summarize(window, now=now)
    availability = summary["availability"]
    count = availability["valid_calls"]
    failures = availability["failed_calls"]
    allowed = count * .001
    remaining = (max(0.0, allowed - failures) if coverage and count > 0 and not availability["pending_calls"]
                 and not availability["unknown_validity"] else None)
    # 1-hour burn compared with the thirty-day per-hour allowance.
    recent = summarize([r for r in window if parse_time(r["ts"]) >= now - timedelta(hours=1)], now=now)
    recent_calls = recent["availability"]["valid_calls"]
    burn = (recent["availability"]["failed_calls"] / recent_calls / .001
            if recent_calls and not recent["availability"]["pending_calls"] else None)
    judgment = summary["judgment"]
    judgment_total = judgment["within_120s"] + judgment["failed_120s"]
    judgment_complete = not judgment["pending_120s"] and not judgment["unconfirmed_samples"]
    judgment_remaining = (max(0.0, judgment_total * .01 - judgment["failed_120s"])
                          if coverage and judgment_total > 0 and judgment_complete else None)
    recent_judgment = recent["judgment"]
    recent_total = recent_judgment["within_120s"] + recent_judgment["failed_120s"]
    judgment_burn = (recent_judgment["failed_120s"] / recent_total / .01
                     if judgment_complete and recent_total else None)
    availability_verified = bool(coverage and count > 0 and not availability["pending_calls"]
                                 and not availability["unknown_validity"])
    judgment_verified = bool(coverage and judgment_total > 0 and judgment_complete)
    return {
        "window_start": window_start.isoformat(), "window_end": now.isoformat(),
        "verified": availability_verified and judgment_verified,
        "availability": {"target": .999, "allowed_failure_rate": .001,
                         "total": count, "failures": failures, "remaining_failures": remaining,
                         "burn_rate_1h": burn, "verified": availability_verified},
        "first_judgment": {"target": .99, "allowed_failure_rate": .01,
                           "total": judgment_total, "failures": judgment["failed_120s"],
                           "remaining_failures": judgment_remaining,
                           "burn_rate_1h": judgment_burn, "verified": judgment_verified},
        "reason": (None if availability_verified and judgment_verified else
                   "Less than 30 days of complete observation" if not coverage else
                   "Incomplete or insufficient samples"),
    }
