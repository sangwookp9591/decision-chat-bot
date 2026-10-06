"""Durable projection of the active or explicitly selected judgment run."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from ildongi.auth.core import Principal, get_principal
from ildongi.ingest.service import visible_meta
from ildongi.judgment.progress_store import get_progress

router = APIRouter(prefix="/api", tags=["judgment"])


@router.get("/requests/{request_id}/progress")
async def progress(request_id: str, run_id: str | None = Query(None),
                   principal: Principal = Depends(get_principal)):  # noqa: B008
    if await visible_meta(principal, request_id) is None:
        raise HTTPException(404, "Request not found")
    result = await get_progress(principal.tenant_id, request_id, run_id)
    if result is None:
        raise HTTPException(404, "Run not found")
    return result
