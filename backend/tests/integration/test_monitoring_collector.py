"""Journal-backed monitoring contract tests, without Neo4j availability."""

from __future__ import annotations

import asyncio
import json
from contextlib import closing
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from jevtriage.auth.core import Principal, get_principal
from jevtriage.db.schema import apply_schema
from jevtriage.db.tx import write_tx
from jevtriage.ingest.store import create_request, get_request_meta
from jevtriage.journal.collector import collect_once, connect
from jevtriage.journal.reader import producer_heartbeat
from jevtriage.journal.watchdog import check_once
from jevtriage.journal.writer import JournalWriter, failure_count
from jevtriage.main import create_app
from jevtriage.monitoring import api as monitoring_api
from jevtriage.monitoring.aggregates import collection_status, events_between, summarize
from jevtriage.monitoring.api import reconcile_commits
from jevtriage.monitoring.slo import error_budget


@pytest.mark.asyncio
async def test_monitoring_rows_share_one_snapshot_for_concurrent_windows(tmp_path, monkeypatch):
    now = datetime.now(UTC)
    writer = JournalWriter(tmp_path)
    _record(writer, now - timedelta(seconds=1), "shared-1", "a1", "request_received",
            validity="valid")
    _record(writer, now, "shared-2", "a1", "request_failed", error_class="ModelTimeout")
    collect_once(tmp_path)
    monkeypatch.setattr(monitoring_api, "get_settings",
                        lambda: SimpleNamespace(data_dir=tmp_path))
    original = monitoring_api.events_between
    calls = []

    def counted(*args):
        calls.append(args)
        return original(*args)

    monkeypatch.setattr(monitoring_api, "events_between", counted)
    principal = Principal("t-alpha", "operator", (), frozenset({"operator"}))
    windows = [(now - timedelta(days=30), now + timedelta(seconds=1)),
               (datetime(1970, 1, 1, tzinfo=UTC), now + timedelta(seconds=1))]
    first, second = await asyncio.gather(*(monitoring_api._rows(principal, *w) for w in windows))
    assert len(calls) == 1
    assert first == second
    assert len(first[0]) == 2


@pytest.mark.asyncio
async def test_monitoring_snapshot_expires_and_stays_tenant_scoped(tmp_path, monkeypatch):
    now = datetime.now(UTC)
    writer = JournalWriter(tmp_path)
    _record(writer, now, "alpha", "a1", "request_received", validity="valid")
    writer.append({"event_id": "beta", "attempt_id": "b1", "kind": "request_received",
                   "ts": now.isoformat(), "tenant_id": "t-beta", "validity": "valid"})
    writer.flush()
    collect_once(tmp_path)
    monkeypatch.setattr(monitoring_api, "get_settings",
                        lambda: SimpleNamespace(data_dir=tmp_path))
    window = (now - timedelta(seconds=1), now + timedelta(seconds=2))
    alpha = Principal("t-alpha", "operator", (), frozenset({"operator"}))
    beta = Principal("t-beta", "operator", (), frozenset({"operator"}))
    assert {r["event_id"] for r in (await monitoring_api._rows(alpha, *window))[0]} == {"alpha"}
    assert {r["event_id"] for r in (await monitoring_api._rows(beta, *window))[0]} == {"beta"}
    _record(writer, now + timedelta(seconds=1), "alpha-new", "a2", "request_received",
            validity="valid")
    collect_once(tmp_path)
    assert {r["event_id"] for r in (await monitoring_api._rows(alpha, *window))[0]} == {"alpha"}
    key = (asyncio.get_running_loop(), tmp_path, "t-alpha")
    created, task = monitoring_api._snapshot_cache[key]
    monitoring_api._snapshot_cache[key] = (created - monitoring_api._SNAPSHOT_TTL, task)
    assert {r["event_id"] for r in (await monitoring_api._rows(alpha, *window))[0]} == {
        "alpha", "alpha-new"}


@pytest.mark.asyncio
async def test_monitoring_snapshot_keeps_windowed_legacy_sse_attribution(tmp_path, monkeypatch):
    now = datetime.now(UTC)
    writer = JournalWriter(tmp_path)
    _record(writer, now - timedelta(minutes=2), "outside", "a1", "request_completed",
            request_id="old-request")
    _record(writer, now, "inside", "a2", "request_completed", request_id="new-request")
    for event_id, request_id in (("linked", "new-request"), ("unlinked", "old-request")):
        writer.append({"event_id": event_id, "attempt_id": event_id,
                       "kind": "sse_deliver", "request_id": request_id,
                       "ts": now.isoformat()})
    writer.flush()
    collect_once(tmp_path)
    monkeypatch.setattr(monitoring_api, "get_settings",
                        lambda: SimpleNamespace(data_dir=tmp_path))
    principal = Principal("t-alpha", "operator", (), frozenset({"operator"}))
    rows, unscoped = await monitoring_api._rows(
        principal, now - timedelta(seconds=1), now + timedelta(seconds=1))
    assert {r["event_id"] for r in rows} == {"inside", "linked"}
    assert unscoped == 1


def test_metrics_store_has_tenant_time_index(tmp_path):
    with closing(connect(tmp_path)) as db:
        indexes = {row[1] for row in db.execute("PRAGMA index_list(events)")}
    assert "events_tenant_ts" in indexes


def _record(writer, when, event, attempt, kind, **fields):
    writer.append({"event_id": event, "attempt_id": attempt, "kind": kind,
                   "ts": when.isoformat(), "tenant_id": "t-alpha", **fields})
    writer.flush()


def test_summary_reports_supplement_answer_wait_separately_from_first_judgment():
    from jevtriage.monitoring.aggregates import summarize

    start = datetime(2026, 1, 1, tzinfo=UTC)
    rows = [
        {"kind": "review_decided", "action": "request_info", "request_id": "req_1",
         "ts": start.isoformat(), "attempt_id": "review-1"},
        {"kind": "revision_received", "request_id": "req_1",
         "ts": (start + timedelta(seconds=90)).isoformat(), "received_at":
         (start + timedelta(seconds=90)).isoformat(), "attempt_id": "revision-1"},
        {"kind": "review_decided", "action": "request_info", "request_id": "req_2",
         "ts": (start + timedelta(seconds=5)).isoformat(), "attempt_id": "review-2"},
    ]
    result = summarize(rows, now=start + timedelta(minutes=5))
    assert result["supplement_wait_ms"] == {"p50": 90_000.0, "p95": 90_000.0, "unresolved": 1}
    assert result["judgment"]["eligible_requests"] == 0


def test_collector_deduplicates_and_keeps_db_failure_in_availability(tmp_path):
    now = datetime.now(UTC)
    start = now - timedelta(minutes=5)
    writer = JournalWriter(tmp_path)
    _record(writer, start, "e1", "a1", "request_received", validity="valid")
    _record(writer, start + timedelta(milliseconds=50), "e2", "a1", "request_completed",
            request_id="req_1", status_code=202, duration_ms=50,
            eligible_first=True, input_type="text")
    _record(writer, start + timedelta(seconds=3), "e3", "w1", "worker_run",
            request_id="req_1", run_id="run_1", status_code="judgment_saved",
            complete_judgment=False, run_kind="normal")
    _record(writer, start + timedelta(seconds=3), "e3b", "w1", "judgment_committed",
            request_id="req_1", run_id="run_1", status_code="committed",
            complete_judgment=True, run_kind="normal")
    _record(writer, start + timedelta(seconds=10), "e4", "a2", "request_received", validity="valid")
    _record(writer, start + timedelta(seconds=11), "e5", "a2", "request_failed",
            status_code=503, error_class="database_unavailable", duration_ms=1000)
    _record(writer, start + timedelta(seconds=20), "e6", "a3", "request_received", validity="valid")
    _record(writer, start + timedelta(seconds=21), "e7", "a3", "request_completed",
            request_id="req_2", status_code=202, duration_ms=1000,
            eligible_first=True, input_type="attachment", excluded_file_count=0)
    _record(writer, start + timedelta(seconds=150), "e8", "w2", "worker_run",
            request_id="req_2", run_id="run_2", status_code="judgment_saved",
            complete_judgment=False, run_kind="normal")
    _record(writer, start + timedelta(seconds=150), "e8b", "w2", "judgment_committed",
            request_id="req_2", run_id="run_2", status_code="committed",
            complete_judgment=True, run_kind="normal")
    _record(writer, start + timedelta(seconds=30), "e9", "shadow", "worker_run",
            request_id="req_1", run_id="run_shadow", status_code="judgment_saved",
            complete_judgment=False, run_kind="shadow")
    _record(writer, start + timedelta(seconds=30), "e9b", "shadow", "judgment_committed",
            request_id="req_1", run_id="run_shadow", status_code="committed",
            complete_judgment=True, run_kind="shadow")
    with (tmp_path / "journal" / "current.jsonl").open("ab") as stream:
        stream.write(b"{bad json}\n")
    assert collect_once(tmp_path)["inserted"] == 12
    assert collect_once(tmp_path)["inserted"] == 0
    rows = events_between(tmp_path, start - timedelta(seconds=1), now)
    result = summarize(rows, now=now)
    assert result["availability"] == {"valid_calls": 3, "successful_calls": 2,
        "failed_calls": 1, "pending_calls": 0, "unknown_validity": 0, "ratio": 2 / 3}
    assert result["judgment"]["eligible_requests"] == 2
    assert result["judgment"]["within_120s"] == 1
    assert result["judgment"]["failed_120s"] == 1
    assert result["judgment"]["late_recoveries"] == 1
    assert result["latency_ms"]["attachment_first_p95"] == 120_000
    assert result["shadow_runs"] == 1
    assert collection_status(tmp_path)["damaged_lines_or_truncations"] == 1
    assert result["failures"]["storage"][0]["attempt_id"] == "a2"


def test_watchdog_alerts_without_journal_or_neo4j(tmp_path):
    assert "collector_stopped" in [a["kind"] for a in check_once(tmp_path)]
    heartbeat = tmp_path / "metrics" / "api-heartbeat.json"
    heartbeat.parent.mkdir(parents=True, exist_ok=True)
    heartbeat.write_text(json.dumps({"ts": datetime.now(UTC).isoformat(),
                                     "journal_write_failures": 2}), encoding="utf-8")
    kinds = [a["kind"] for a in check_once(tmp_path)]
    assert "journal_write_failure" in kinds
    assert len(list((tmp_path / "alerts").glob("alert_*.json"))) >= 2


def test_error_budget_is_unverified_before_30_days(tmp_path):
    writer = JournalWriter(tmp_path)
    now = datetime.now(UTC)
    _record(writer, now, "one", "attempt", "request_received", validity="valid")
    collect_once(tmp_path)
    rows = events_between(tmp_path, now - timedelta(days=30), now + timedelta(seconds=1))
    budget = error_budget(rows, now=now + timedelta(seconds=1), collection_complete=True)
    assert budget["verified"] is False
    assert budget["availability"]["remaining_failures"] is None
    assert budget["first_judgment"]["remaining_failures"] is None


def test_first_eligible_after_file_exclusion_and_retry_keep_one_sample(tmp_path):
    now = datetime.now(UTC)
    t0 = now - timedelta(minutes=10)
    writer = JournalWriter(tmp_path)
    _record(writer, t0, "r0", "intake", "request_received", validity="valid")
    _record(writer, t0 + timedelta(seconds=1), "r1", "intake", "request_completed",
            request_id="req_file", status_code=202, eligible_first=False,
            excluded_file_count=1, input_type="attachment")
    _record(writer, t0 + timedelta(seconds=200), "f0", "decision", "eligibility_received",
            request_id="req_file", validity="valid")
    _record(writer, t0 + timedelta(seconds=201), "f1", "decision", "eligibility_completed",
            request_id="req_file", eligible_first=True, input_type="attachment",
            excluded_file_count=1, status_code=200)
    _record(writer, t0 + timedelta(seconds=210), "w0", "first_attempt", "worker_attempt_failure",
            request_id="req_file", run_id="run_first", error_class="ModelTimeout",
            status_code="failed", run_kind="normal")
    _record(writer, t0 + timedelta(seconds=240), "w1", "retry", "judgment_committed",
            request_id="req_file", run_id="run_first", status_code="committed",
            complete_judgment=True, run_kind="normal")
    _record(writer, t0 + timedelta(seconds=300), "s1", "supplement", "judgment_committed",
            request_id="req_file", run_id="run_supplement", status_code="committed",
            complete_judgment=True, run_kind="supplement")
    collect_once(tmp_path)
    rows = events_between(tmp_path, t0 - timedelta(seconds=1), now)
    result = summarize(rows, now=now)
    assert result["file_exclusions"] == 1
    assert result["first_eligible_after_file_decision"] == 1
    assert result["judgment"]["eligible_requests"] == 1
    assert result["judgment"]["within_120s"] == 1
    assert result["judgment"]["failed_120s"] == 0
    assert result["latency_ms"]["attachment_first_p95"] == 40_000


def test_monitoring_api_requires_operator():
    app = create_app()
    app.dependency_overrides[get_principal] = lambda: Principal(
        "t-alpha", "user", (), frozenset({"requester"}))
    with TestClient(app) as client:
        assert client.get("/api/monitoring/collection-status").status_code == 403
        app.dependency_overrides[get_principal] = lambda: Principal(
            "t-alpha", "operator", (), frozenset({"operator"}))
        response = client.get("/api/monitoring/collection-status")
        assert response.status_code == 200
        assert "complete" in response.json()


def test_actual_journal_write_failure_reaches_watchdog(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "journal").write_text("occupied", encoding="utf-8")
    before = failure_count()
    with pytest.raises(OSError):
        _record(JournalWriter(data_dir), datetime.now(UTC), "broken", "attempt",
                "request_received", validity="valid")
    assert failure_count() == before + 1
    producer_heartbeat(data_dir, "api", failure_count())
    assert "journal_write_failure" in [a["kind"] for a in check_once(data_dir)]


def test_collector_waits_for_complete_line(tmp_path):
    directory = tmp_path / "journal"
    directory.mkdir()
    path = directory / "current.jsonl"
    record = {"event_id": "partial", "attempt_id": "attempt", "kind": "request_received",
              "ts": datetime.now(UTC).isoformat(), "validity": "valid"}
    encoded = json.dumps(record).encode()
    path.write_bytes(encoded)
    assert collect_once(tmp_path)["inserted"] == 0
    with path.open("ab") as stream:
        stream.write(b"\n")
    assert collect_once(tmp_path)["inserted"] == 1


def test_watchdog_reports_corrupt_metrics_store(tmp_path):
    directory = tmp_path / "metrics"
    directory.mkdir()
    (directory / "metrics.db").write_text("not sqlite", encoding="utf-8")
    assert "metrics_store_unavailable" in [a["kind"] for a in check_once(tmp_path)]


def test_collection_gap_is_exposed(tmp_path):
    with closing(connect(tmp_path)) as db, db:
        db.execute("INSERT INTO collector_ticks(ts) VALUES(?)",
                   ((datetime.now(UTC) - timedelta(seconds=45)).isoformat(),))
    collect_once(tmp_path)
    state = collection_status(tmp_path)
    assert "collector_gap_30d" in state["issues"]
    assert state["continuous_30d"] is False
    assert state["incomplete_intervals"]


def test_error_budget_uses_distinct_availability_and_judgment_denominators(tmp_path):
    now = datetime.now(UTC)
    start = now - timedelta(minutes=20)
    writer = JournalWriter(tmp_path)
    _record(writer, start, "budget-in-1", "b1", "request_received", validity="valid")
    _record(writer, start + timedelta(seconds=1), "budget-out-1", "b1",
            "request_completed", request_id="req_budget", status_code=202,
            eligible_first=True, input_type="text")
    _record(writer, start + timedelta(seconds=3), "budget-commit", "w1",
            "judgment_committed", request_id="req_budget", run_id="run_budget",
            complete_judgment=True, status_code="committed", run_kind="normal")
    _record(writer, start + timedelta(seconds=5), "budget-in-2", "b2",
            "request_received", validity="valid")
    _record(writer, start + timedelta(seconds=6), "budget-out-2", "b2",
            "request_failed", status_code=503, error_class="database_unavailable")
    collect_once(tmp_path)
    rows = events_between(tmp_path, start - timedelta(seconds=1), now)
    budget = error_budget(rows, now=now, collection_complete=True)
    assert budget["verified"] is True
    assert budget["availability"]["total"] == 2
    assert budget["availability"]["failures"] == 1
    assert budget["availability"]["remaining_failures"] == 0
    assert budget["first_judgment"]["total"] == 1
    assert budget["first_judgment"]["failures"] == 0
    assert budget["first_judgment"]["remaining_failures"] == .01


def test_watchdog_alerts_fast_burn_and_repeated_failures(tmp_path):
    now = datetime.now(UTC)
    writer = JournalWriter(tmp_path)
    for number in range(3):
        attempt = f"f{number}"
        _record(writer, now - timedelta(minutes=1), f"start-{number}", attempt,
                "request_received", validity="valid")
        _record(writer, now - timedelta(seconds=30), f"end-{number}", attempt,
                "request_failed", status_code=503, error_class="database_unavailable")
    collect_once(tmp_path)
    kinds = {a["kind"] for a in check_once(tmp_path)}
    assert "fast_budget_burn" in kinds
    assert "repeated_failures" in kinds


def test_summary_filters_org_and_current_status(tmp_path, monkeypatch):
    now = datetime.now(UTC)
    writer = JournalWriter(tmp_path)
    _record(writer, now, "org-start", "org-attempt", "request_received",
            validity="valid", org_ids=["org-a"])
    _record(writer, now + timedelta(milliseconds=5), "org-end", "org-attempt",
            "request_completed", request_id="req_org", status_code=202,
            eligible_first=True, input_type="text", org_ids=["org-a"],
            request_status="judgment_pending")
    collect_once(tmp_path)
    monkeypatch.setattr(monitoring_api, "get_settings",
                        lambda: SimpleNamespace(data_dir=tmp_path))
    async def business(_tenant, _start, _end, _org, _status):
        return {"request_ids": ["req_org"], "request_denominator": 1,
                "org_unconfirmed": 0, "auto_assignment_count": 1,
                "review_completed_count": 0}
    async def no_reviews(_tenant, _org, _status):
        return {"p50": None, "p95": None, "longest": None, "unresolved": 0}
    monkeypatch.setattr(monitoring_api, "business_counts", business)
    monkeypatch.setattr(monitoring_api, "review_wait", no_reviews)
    app = create_app()
    app.dependency_overrides[get_principal] = lambda: Principal(
        "t-alpha", "operator", (), frozenset({"operator"}))
    with TestClient(app) as client:
        response = client.get("/api/monitoring/summary", params={"org": "org-a",
            "status": "judgment_pending", "to": (now + timedelta(seconds=1)).isoformat()})
        assert response.status_code == 200
        body = response.json()
        assert body["requests"]["received"] == 1
        assert body["availability"]["scope_incomplete"] is True
        assert body["filters"]["org"] == "org-a"
        assert body["business"]["request_denominator"] == 1
        assert body["business"]["auto_assignment_count"] == 1


@pytest.mark.asyncio
async def test_request_org_scope_is_persisted_in_intake_transaction():
    tenant = f"t18_{uuid4().hex}"
    await apply_schema()
    try:
        result = await create_request(tenant, "user", "hello", [], "key", "hash",
                                      datetime.now(UTC).isoformat(), org_ids=("org-a", "org-b"))
        meta = await get_request_meta(tenant, result["request_id"])
        assert meta["org_ids"] == ["org-a", "org-b"]
        missing = await reconcile_commits(tenant, [])
        assert result["request_id"] in missing["request_commits_missing_journal"]
        reconciled = await reconcile_commits(tenant, [{"tenant_id": tenant,
            "kind": "request_completed", "request_id": result["request_id"]}])
        assert result["request_id"] not in reconciled["request_commits_missing_journal"]
    finally:
        async def cleanup(tx):
            await (await tx.run("MATCH (n {tenant_id:$tenant}) DETACH DELETE n",
                                tenant=tenant)).consume()
        await write_tx(tenant, cleanup)
