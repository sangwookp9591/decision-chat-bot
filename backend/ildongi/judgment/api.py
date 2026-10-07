"""Read-only judgment and run history API."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Query

from ildongi.auth.core import Principal, get_principal
from ildongi.domain.serialize import json_value
from ildongi.judgment.service import visible_judgment, visible_request
from ildongi.judgment.store import list_runs

router = APIRouter(prefix="/api")


def _date(value):
    return json_value(value)


@router.get("/requests/{request_id}/judgment")
async def judgment(request_id: str, run_id: str | None = Query(None),
                   principal: Principal = Depends(get_principal)):  # noqa: B008
    return await visible_judgment(principal, request_id, run_id)


@router.get("/requests/{request_id}/runs")
async def runs(request_id: str, principal: Principal = Depends(get_principal)):  # noqa: B008
    meta = await visible_request(principal, request_id)
    rows = await list_runs(principal.tenant_id, request_id)
    return {"active_run_id": meta.get("active_run_id"), "runs": [
        {"id": r["r"]["id"], "revision_id": r["r"].get("input_revision_id"),
         "status": r["r"].get("status"), "versions": json.loads(r["r"].get("versions_json") or "{}"),
         "created_at": _date(r["r"].get("created_at")),
         "first_judgment_committed_at": _date(r["r"].get("first_judgment_committed_at"))}
        for r in rows]}
