"""Metric calculations over the independent collected event stream."""

from __future__ import annotations

import json
import sqlite3
from collections import Counter, defaultdict
from contextlib import closing
from datetime import UTC, datetime, timedelta
from math import ceil
from pathlib import Path

from jevtriage.db.tx import read_tx
from jevtriage.journal.collector import connect, metrics_path


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value).astimezone(UTC)


def percentile(values: list[float], rank: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, ceil(rank * len(ordered)) - 1)]


def events_between(data_dir: Path, start: datetime, end: datetime) -> list[dict]:
    if not metrics_path(data_dir).exists():
        return []
    with closing(connect(data_dir)) as db:
        rows = db.execute("SELECT * FROM events WHERE ts >= ? AND ts <= ? ORDER BY ts,event_id",
                          (start.isoformat(), end.isoformat())).fetchall()
    return [dict(row) | json.loads(row["payload"]) for row in rows]


def _failure_group(error: str | None) -> str:
    value = (error or "").lower()
    if any(term in value for term in ("jev", "model", "timeout", "http")):
        return "external_model"
    if any(term in value for term in ("parse", "pdf", "docx", "file", "decode", "json")):
        return "parsing"
    if any(term in value for term in ("database", "neo4j", "storage", "serviceunavailable")):
        return "storage"
    if "sse" in value or "stream" in value:
        return "sse"
    return "other"


def summarize(rows: list[dict], *, now: datetime | None = None) -> dict:
    now = now or datetime.now(UTC)
    attempts: dict[str, list[dict]] = defaultdict(list)
    runs: dict[str, list[dict]] = defaultdict(list)
    request_runs: dict[str, set[str]] = defaultdict(set)
    failure_ids: dict[str, list[dict]] = defaultdict(list)
    seen_failures: set[tuple[str, str]] = set()
    kinds = Counter()
    for row in rows:
        kinds[row["kind"]] += 1
        attempts[row["attempt_id"]].append(row)
        if row.get("run_id"):
            runs[row["run_id"]].append(row)
            if row.get("request_id"):
                request_runs[row["request_id"]].add(row["run_id"])
        if row.get("error_class") and row.get("run_kind") != "shadow":
            key = (row["attempt_id"], row["error_class"])
            if key not in seen_failures:
                seen_failures.add(key)
                failure_ids[_failure_group(row["error_class"])].append({
                    "request_id": row.get("request_id"), "run_id": row.get("run_id"),
                    "attempt_id": row["attempt_id"], "error_class": row["error_class"],
                    "ts": row["ts"],
                })

    valid_calls = completed = failed_calls = pending_calls = 0
    intake_latency: list[float] = []
    unknown_validity = 0
    for parts in attempts.values():
        starts = [r for r in parts if r["kind"] in ("request_received", "lookup_received")]
        if not starts:
            continue
        start = starts[0]
        terminal = next((r for r in reversed(parts) if r["kind"] in
                         ("request_completed", "request_failed", "lookup_completed", "lookup_failed")), None)
        if start.get("validity") not in ("valid", "invalid"):
            unknown_validity += 1
            continue
        if start["validity"] == "invalid" or (terminal and (
                terminal.get("validity") == "invalid" or terminal.get("error_class") == "input_rejected")):
            continue
        valid_calls += 1
        if terminal is None:
            pending_calls += 1
            continue
        code = terminal.get("status_code")
        if code is not None and str(code).isdigit() and 200 <= int(code) < 300:
            completed += 1
        else:
            failed_calls += 1
        if terminal.get("duration_ms") is not None and start["kind"] == "request_received":
            intake_latency.append(float(terminal["duration_ms"]))

    # Run termination is diagnostic; only judgment_committed proves a stored judgment.
    candidate_judgments = 0
    failed_runs = 0
    revisions: list[float] = []
    step_latency: list[float] = []
    steps: dict[str, list[float]] = defaultdict(list)
    shadow_runs = 0
    by_version: dict[str, Counter] = defaultdict(Counter)
    for parts in runs.values():
        if any(r.get("run_kind") == "shadow" for r in parts):
            shadow_runs += 1
            continue
        config = next((str(r["config_version"]) for r in parts
                       if r.get("config_version") is not None), "unknown")
        model = next((str(r["model_version"]) for r in parts
                      if r.get("model_version") is not None), "unknown")
        version = f"config={config}|model={model}"
        if any(r["kind"] == "worker_run" and r.get("status_code") == "judgment_saved" for r in parts):
            candidate_judgments += 1
            by_version[version]["saved"] += 1
        if any(r["kind"] == "worker_run" and r.get("status_code") == "failed" for r in parts):
            failed_runs += 1
            by_version[version]["failed"] += 1
        for r in parts:
            if r["kind"] == "worker_step" and r.get("duration_ms") is not None:
                step_latency.append(float(r["duration_ms"]))
                steps[r.get("step_name") or "unknown"].append(float(r["duration_ms"]))
            if r["kind"] == "worker_run" and r.get("duration_ms") is not None:
                revisions.append(float(r["duration_ms"]))
    sse_latency = [float(r["duration_ms"]) for r in rows if r["kind"] == "sse_deliver"
                   and r.get("duration_ms") is not None]
    first_eligible: dict[str, tuple[datetime, str]] = {}
    for parts in attempts.values():
        start = next((r for r in parts if r["kind"] in
                      ("request_received", "eligibility_received", "revision_received")), None)
        end = next((r for r in parts if r["kind"] in
                    ("request_completed", "eligibility_completed", "revision_completed") and
                    r.get("eligible_first") is True and r.get("request_id")), None)
        if start and end:
            rid = end["request_id"]
            began = _time(start.get("received_at") or start["ts"])
            if rid not in first_eligible or began < first_eligible[rid][0]:
                first_eligible[rid] = (began, end.get("input_type") or "text")
    completed_by_request: dict[str, datetime] = {}
    for row in rows:
        if (row["kind"] == "judgment_committed" and row.get("status_code") == "committed"
                and row.get("complete_judgment") is True and row.get("request_id")
                and row.get("run_kind") != "shadow"):
            rid = row["request_id"]
            when = _time(row["ts"])
            if rid not in completed_by_request or when < completed_by_request[rid]:
                completed_by_request[rid] = when
    first_success = first_failed = first_pending = late_recoveries = 0
    text_samples: list[float] = []
    attachment_samples: list[float] = []
    for rid, (began, input_type) in first_eligible.items():
        committed = completed_by_request.get(rid)
        elapsed = (committed - began).total_seconds() * 1000 if committed else None
        if elapsed is not None and 0 <= elapsed <= 120_000:
            first_success += 1
            sample = max(0, elapsed)
        elif now - began >= timedelta(seconds=120):
            first_failed += 1
            sample = 120_000.0
            if committed:
                late_recoveries += 1
        else:
            first_pending += 1
            continue
        (attachment_samples if input_type == "attachment" else text_samples).append(sample)
    return {
        "availability": {"valid_calls": valid_calls, "successful_calls": completed,
                         "failed_calls": failed_calls, "pending_calls": pending_calls,
                         "unknown_validity": unknown_validity,
                         "ratio": completed / valid_calls if valid_calls and not pending_calls and not unknown_validity else None},
        "judgment": {"eligible_requests": len(first_eligible), "within_120s": first_success,
                     "failed_120s": first_failed, "pending_120s": first_pending,
                     "ratio": first_success / (first_success + first_failed)
                     if first_success + first_failed else None,
                     "candidate_commits": candidate_judgments, "failed_runs": failed_runs,
                     "late_recoveries": late_recoveries,
                     "unconfirmed_samples": len(set(request_runs) - set(first_eligible))},
        "latency_ms": {"intake_p95": percentile(intake_latency, .95),
                       "text_first_p95": percentile(text_samples, .95),
                       "attachment_first_p95": percentile(attachment_samples, .95),
                       "sse_deliver_p95": percentile(sse_latency, .95),
                       "revision_p95": percentile(revisions, .95),
                       "step_p95": percentile(step_latency, .95)},
        "review_wait_ms": {"p50": None, "p95": None, "longest": None, "unresolved": None},
        "requests": {"received": len({r["request_id"] for r in rows
                                      if r["kind"] == "request_completed" and r.get("request_id")}),
                     "failed_before_id": sum(r["kind"] == "request_failed" and not r.get("request_id")
                                             for r in rows)},
        "file_exclusions": sum(int(r.get("excluded_file_count") or 0) for r in rows
                               if r["kind"] == "request_completed"),
        "first_eligible_after_file_decision": len({r["request_id"] for r in rows
            if r["kind"] in ("eligibility_completed", "revision_completed")
            and r.get("eligible_first") and r.get("request_id")}),
        "cancellations": sum(r.get("status_code") == "cancelled" for r in rows
                             if r["kind"] == "worker_run"), "shadow_runs": shadow_runs,
        "usage": {"model_calls": None, "cost": None},
        "by_version": {k: dict(v) for k, v in by_version.items()},
        "steps": {name: {"count": len(values), "p50_ms": percentile(values, .5),
                         "p95_ms": percentile(values, .95)} for name, values in steps.items()},
        "kinds": dict(kinds), "failures": dict(failure_ids),
    }


def collection_status(data_dir: Path, *, now: datetime | None = None,
                      stale_seconds: int = 30) -> dict:
    now = now or datetime.now(UTC)
    path = Path(data_dir) / "metrics" / "collector-heartbeat.json"
    issues = []
    last_heartbeat = None
    if path.exists():
        try:
            last_heartbeat = json.loads(path.read_text(encoding="utf-8")).get("ts")
        except (ValueError, OSError):
            issues.append("invalid_collector_heartbeat")
    try:
        if not last_heartbeat or (now - _time(last_heartbeat)).total_seconds() > stale_seconds:
            issues.append("collector_stopped")
    except ValueError:
        issues.append("invalid_collector_heartbeat")
    damaged = 0
    observed_events = 0
    intervals: list[dict] = []
    first_tick = last_tick = None
    gaps: list[dict] = []
    if metrics_path(data_dir).exists():
        try:
            with closing(connect(data_dir)) as db:
                cutoff = (now - timedelta(days=30)).isoformat()
                damaged = db.execute("SELECT count(*) FROM collection_issues WHERE detected_at>=?",
                                     (cutoff,)).fetchone()[0]
                observed_events = int(db.execute("SELECT EXISTS(SELECT 1 FROM events LIMIT 1)").fetchone()[0])
                intervals = [dict(row) for row in db.execute(
                    "SELECT kind,detected_at AS start_at FROM collection_issues WHERE detected_at>=? "
                    "ORDER BY id DESC LIMIT 100", (cutoff,))]
                tick_bounds = db.execute("SELECT min(ts) AS first_tick,max(ts) AS last_tick "
                                         "FROM collector_ticks").fetchone()
                first_tick, last_tick = tick_bounds["first_tick"], tick_bounds["last_tick"]
                gaps = [dict(row) for row in db.execute(
                    "SELECT start_at,end_at FROM collection_gaps WHERE end_at>=? "
                    "ORDER BY start_at DESC LIMIT 100", (cutoff,))]
        except sqlite3.Error:
            issues.append("metrics_store_unavailable")
    if damaged:
        issues.append("damaged_or_truncated_journal")
    if gaps:
        issues.append("collector_gap_30d")
    continuous_30d = bool(first_tick and _time(first_tick) <= now - timedelta(days=30)
                          and last_tick and (now - _time(last_tick)).total_seconds() <= stale_seconds
                          and not issues)
    return {"complete": not issues, "issues": issues,
            "has_collected_events": bool(observed_events),
            "continuous_30d": continuous_30d,
            "damaged_lines_or_truncations": damaged,
            "incomplete_intervals": intervals + gaps,
            "last_collected_at": last_heartbeat,
            "limitations": ["org and request status are not recorded independently",
                            "producer heartbeat is activity-based"]}


async def review_wait(tenant_id: str, org: str | None = None,
                      status: str | None = None) -> dict:
    """Human queue timing from business state; separate from system SLO."""
    async def query(tx):
        result = await tx.run("""MATCH (v:Review {tenant_id:$tenant})
            MATCH (r:Request {tenant_id:$tenant,id:v.request_id})
            WHERE ($org IS NULL OR $org IN coalesce(r.org_ids, []) OR r.org_id=$org)
              AND ($status IS NULL OR r.status=$status)
            RETURN v.status AS status,
            CASE WHEN v.decided_at IS NULL THEN datetime().epochMillis
                 ELSE v.decided_at.epochMillis END - v.created_at.epochMillis AS wait_ms""",
            tenant=tenant_id, org=org, status=status)
        return [dict(row) async for row in result]

    rows = await read_tx(tenant_id, query)
    waits = [float(r["wait_ms"]) for r in rows if r.get("wait_ms") is not None]
    return {"p50": percentile(waits, .5), "p95": percentile(waits, .95),
            "longest": max(waits, default=None),
            "unresolved": sum(r.get("status") == "pending" for r in rows)}


async def business_counts(tenant_id: str, start: datetime, end: datetime,
                          org: str | None = None, status: str | None = None) -> dict:
    """Current request denominator and business outcomes, separate from SLO samples."""
    async def query(tx):
        result = await tx.run("""MATCH (q:Request {tenant_id:$tenant})
            WHERE q.created_at >= datetime($start) AND q.created_at <= datetime($end)
              AND ($status IS NULL OR q.status=$status)
              AND ($org IS NULL OR $org IN coalesce(q.org_ids, []) OR q.org_id=$org
                   OR (q.org_id IS NULL AND q.org_ids IS NULL))
            OPTIONAL MATCH (a:Assignment {tenant_id:$tenant,request_id:q.id})
            OPTIONAL MATCH (v:Review {tenant_id:$tenant,request_id:q.id})-[:HAS_DECISION]->(d:ReviewDecision)
            RETURN q.id AS id, q.org_id AS org_id, q.org_ids AS org_ids,
                   count(DISTINCT CASE WHEN a.pathway='auto' THEN a.id END) AS auto_assignments,
                   count(DISTINCT d.id) AS review_decisions""",
            tenant=tenant_id, start=start.isoformat(), end=end.isoformat(), org=org, status=status)
        return [dict(row) async for row in result]
    rows = await read_tx(tenant_id, query)
    return {"request_ids": [r["id"] for r in rows],
            "request_denominator": len(rows),
            "org_unconfirmed": sum(not r.get("org_id") and not r.get("org_ids") for r in rows),
            "auto_assignment_count": sum(bool(r["auto_assignments"]) for r in rows),
            "review_completed_count": sum(bool(r["review_decisions"]) for r in rows)}
