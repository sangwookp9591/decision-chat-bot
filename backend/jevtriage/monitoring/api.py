"""Operator monitoring API backed by independent collected metrics."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query

from jevtriage.auth.core import Principal, require_roles
from jevtriage.config import get_settings
from jevtriage.monitoring.aggregates import (
    business_counts,
    collection_status,
    committed_entities,
    events_between,
    review_wait,
    summarize,
)
from jevtriage.monitoring.alerts import list_alerts
from jevtriage.monitoring.slo import error_budget

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


def _range(start: str | None, end: str | None) -> tuple[datetime, datetime]:
    try:
        stop = datetime.fromisoformat(end).astimezone(UTC) if end else datetime.now(UTC)
        begin = datetime.fromisoformat(start).astimezone(UTC) if start else stop - timedelta(days=30)
    except ValueError as exc:
        raise HTTPException(422, "Invalid ISO 8601 timestamp") from exc
    if begin > stop:
        raise HTTPException(422, "from must be before to")
    return begin, stop


async def _rows(principal: Principal, begin: datetime, stop: datetime) -> tuple[list[dict], int]:
    all_rows = await asyncio.to_thread(events_between, get_settings().data_dir, begin, stop, principal.tenant_id)
    known_requests = {r["request_id"] for r in all_rows
                      if r.get("tenant_id") == principal.tenant_id and r.get("request_id")}
    scoped = [r for r in all_rows if r.get("tenant_id") == principal.tenant_id or
              (not r.get("tenant_id") and r["kind"] == "sse_deliver"
               and r.get("request_id") in known_requests)]
    attributed_ids = {r["event_id"] for r in scoped}
    # Boundary diagnostics are intentionally written before authentication.
    # Their unscoped copies do not indicate an unattributed business event.
    boundary_kinds = {"api_boundary_received", "api_boundary_completed"}
    return scoped, sum(not r.get("tenant_id") and r["kind"] not in boundary_kinds
                       and r["event_id"] not in attributed_ids
                       for r in all_rows)


@router.get("/summary")
async def summary(from_: str | None = Query(None, alias="from"), to: str | None = None,
                  org: str | None = None, status: str | None = None,
                  version: str | None = None,
                  principal: Principal = Depends(require_roles("operator"))):  # noqa: B008
    begin, stop = _range(from_, to)
    rows, unscoped = await _rows(principal, begin, stop)
    business_result, review_result = await asyncio.gather(
            business_counts(principal.tenant_id, begin, stop, org, status),
            review_wait(principal.tenant_id, org, status),
            return_exceptions=True,
        )
    if isinstance(business_result, Exception):
        if org or status:
            raise HTTPException(503, "Request scope filter unavailable") from business_result
        business = {"request_denominator": None, "org_unconfirmed": None,
                    "auto_assignment_count": None, "review_completed_count": None}
    else:
        business = business_result
    if isinstance(review_result, Exception):
        review = {"p50": None, "p95": None, "longest": None,
                  "unresolved": None, "source_status": "unavailable"}
    else:
        review = review_result
    if org or status:
        scoped_requests = set(business.pop("request_ids", []))
        rows = [r for r in rows if r.get("request_id") in scoped_requests]
    else:
        business.pop("request_ids", None)
    if version:
        matching_requests = {r["request_id"] for r in rows
                             if str(r.get("config_version")) == version and r.get("request_id")}
        version_attempts = {r["attempt_id"] for r in rows
                            if r.get("request_id") in matching_requests}
        rows = [r for r in rows if r.get("request_id") in matching_requests
                or r["attempt_id"] in version_attempts
                or str(r.get("config_version")) == version]
    result = summarize(rows, now=stop)
    if version or status:
        for field in ("valid_calls", "successful_calls", "failed_calls", "pending_calls",
                      "unknown_validity", "ratio"):
            result["availability"][field] = None
        result["availability"]["scope_incomplete"] = True
    result["review_wait_ms"] = review
    result.update({"from": begin.isoformat(), "to": stop.isoformat(),
                   "filters": {"org": org, "status": status, "version": version},
                   "collection": collection_status(get_settings().data_dir),
                   "unscoped_events": unscoped})
    result["business"] = business
    return result


@router.get("/slo")
async def slo(principal: Principal = Depends(require_roles("operator"))):  # noqa: B008
    now = datetime.now(UTC)
    rows, unscoped = await _rows(principal, datetime(1970, 1, 1, tzinfo=UTC), now)
    state = collection_status(get_settings().data_dir)
    result = error_budget(rows, now=now, collection_complete=state["continuous_30d"] and unscoped == 0)
    result["collection"] = state
    return result


@router.get("/failures")
async def failures(from_: str | None = Query(None, alias="from"), to: str | None = None,
                   principal: Principal = Depends(require_roles("operator"))):  # noqa: B008
    begin, stop = _range(from_, to)
    rows, unscoped = await _rows(principal, begin, stop)
    return {"from": begin.isoformat(), "to": stop.isoformat(),
            "causes": summarize(rows, now=stop)["failures"], "unscoped_events": unscoped}


@router.get("/alerts")
async def alerts(principal: Principal = Depends(require_roles("operator"))):  # noqa: B008
    del principal
    return {"alerts": list_alerts()}


@router.get("/collection-status")
async def status(principal: Principal = Depends(require_roles("operator"))):  # noqa: B008
    del principal
    return collection_status(get_settings().data_dir)


async def reconcile_commits(tenant_id: str, rows: list[dict]) -> dict:
    """Compare journal IDs with Neo4j; never replay business operations."""
    db_requests, db_runs = await committed_entities(tenant_id)
    journal_requests = {r["request_id"] for r in rows if r.get("tenant_id") == tenant_id
                        and r["kind"] == "request_completed" and r.get("request_id")}
    journal_runs = {r["run_id"]: r.get("status_code") for r in rows
                    if r.get("tenant_id") == tenant_id and r["kind"] == "worker_run" and r.get("run_id")}
    terminal_runs = {run_id for run_id, status in db_runs.items()
                     if status in {"judgment_saved", "failed", "cancelled"}}
    return {"request_commits_missing_journal": sorted(db_requests - journal_requests),
            "journal_success_missing_db": sorted(journal_requests - db_requests),
            "run_commits_missing_journal": sorted(terminal_runs - set(journal_runs)),
            "run_status_mismatch": sorted(r for r in db_runs.keys() & journal_runs.keys()
                                          if db_runs[r] != journal_runs[r])}
