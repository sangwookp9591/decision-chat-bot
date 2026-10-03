"""HTTP API for request intake, file decisions, revisions and source evidence."""

from __future__ import annotations

import time

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from pydantic import BaseModel

from jevtriage.auth.core import Principal, enforce_csrf, get_principal
from jevtriage.auth.policy import redact_source
from jevtriage.config import get_settings
from jevtriage.db.idempotency import IdempotencyConflict
from jevtriage.domain.ids import new_id
from jevtriage.ingest import service

router = APIRouter(prefix="/api", tags=["ingest"])


@router.get("/meta")
async def meta():
    from jevtriage.ingest.parsers.api import (
        MAX_ATTACHMENTS,
        MAX_FILE_BYTES,
        MAX_TEXT_CHARS,
        MAX_TOTAL_BYTES,
    )

    return {
        "mode": get_settings().jev_mode,
        "limits": {
            "attachments": MAX_ATTACHMENTS,
            "file_bytes": MAX_FILE_BYTES,
            "total_bytes": MAX_TOTAL_BYTES,
            "text_characters": MAX_TEXT_CHARS,
        },
        "version": "0.1.0",
    }


@router.post("/requests", status_code=202)
async def submit_request(
    request: Request,
    text: str = Form(""),
    files: list[UploadFile] = File(default=[]),  # noqa: B008
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    principal: Principal = Depends(get_principal),  # noqa: B008
):
    if not principal.roles.intersection({"requester", "reviewer", "operator"}):
        raise HTTPException(403, "requester role required")
    if not idempotency_key:
        raise HTTPException(400, "Idempotency-Key required")
    try:
        return await service.submit(
            principal.tenant_id, principal.user_id, text, files, idempotency_key,
            org_ids=principal.org_ids,
        )
    except IdempotencyConflict as exc:
        raise HTTPException(409, "Idempotency-Key payload conflict") from exc
    except ValueError as exc:
        raise HTTPException(409 if str(exc) == "stale_revision" else 400, str(exc)) from exc
    except Exception as exc:
        if exc.__class__.__name__ == "IdempotencyConflict":
            raise HTTPException(409, "Idempotency-Key payload conflict") from exc
        if (
            exc.__class__.__module__.startswith("neo4j")
            or "ServiceUnavailable" in exc.__class__.__name__
        ):
            raise HTTPException(503, "request persistence unavailable") from exc
        raise


class FileDecision(BaseModel):
    exclude: list[str]
    expected_revision: int


@router.post("/requests/{request_id}/file-decision", status_code=202)
async def file_decision(
    request_id: str,
    body: FileDecision,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    principal: Principal = Depends(get_principal),  # noqa: B008
):
    if not principal.roles.intersection({"requester", "reviewer", "operator"}):
        raise HTTPException(403, "requester role required")
    if not idempotency_key:
        raise HTTPException(400, "Idempotency-Key required")
    meta = await service.visible_meta(principal, request_id)
    if not meta:
        raise HTTPException(404, "Request not found")
    try:
        return await service.decide_files(
            principal, request_id, body.expected_revision, body.exclude, idempotency_key
        )
    except IdempotencyConflict as exc:
        raise HTTPException(409, "Idempotency-Key payload conflict") from exc
    except ValueError as exc:
        raise HTTPException(409, "revision conflict") from exc
    except Exception as exc:
        if exc.__class__.__name__ == "IdempotencyConflict":
            raise HTTPException(409, "Idempotency-Key payload conflict") from exc
        if exc.__class__.__module__.startswith("neo4j"):
            raise HTTPException(503, "request persistence unavailable") from exc
        raise


@router.post("/requests/{request_id}/revisions", status_code=202)
async def add_revision(
    request_id: str,
    expected_revision: int = Form(...),
    text: str = Form(""),
    files: list[UploadFile] = File(default=[]),  # noqa: B008
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    principal: Principal = Depends(get_principal),  # noqa: B008
):
    if not principal.roles.intersection({"requester", "reviewer", "operator"}):
        raise HTTPException(403, "requester role required")
    if not idempotency_key:
        raise HTTPException(400, "Idempotency-Key required")
    meta = await service.visible_meta(principal, request_id)
    if not meta:
        raise HTTPException(404, "Request not found")
    try:
        return await service.revise(
            principal, request_id, expected_revision, text, files, idempotency_key
        )
    except IdempotencyConflict as exc:
        raise HTTPException(409, "Idempotency-Key payload conflict") from exc
    except ValueError as exc:
        raise HTTPException(409 if str(exc) == "stale_revision" else 400, str(exc)) from exc
    except Exception as exc:
        if exc.__class__.__name__ == "IdempotencyConflict":
            raise HTTPException(409, "Idempotency-Key payload conflict") from exc
        if exc.__class__.__module__.startswith("neo4j"):
            raise HTTPException(503, "request persistence unavailable") from exc
        raise


class ReanalyzeRequest(BaseModel):
    expected_revision: int
    reason: str | None = None


@router.post("/requests/{request_id}/reanalyze", status_code=202,
             dependencies=[Depends(enforce_csrf)])
async def reanalyze_request(
    request_id: str,
    body: ReanalyzeRequest,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    principal: Principal = Depends(get_principal),  # noqa: B008
):
    if not principal.roles.intersection({"requester", "reviewer", "operator"}):
        raise HTTPException(403, "requester role required")
    if not idempotency_key:
        raise HTTPException(400, "Idempotency-Key required")
    if not await service.visible_meta(principal, request_id):
        raise HTTPException(404, "Request not found")
    try:
        return await service.reanalyze(
            principal, request_id, body.expected_revision, body.reason, idempotency_key
        )
    except IdempotencyConflict as exc:
        raise HTTPException(409, "Idempotency-Key payload conflict") from exc
    except ValueError as exc:
        raise HTTPException(409 if str(exc) in {"stale_revision", "revision_unconfirmed"} else 400,
                            str(exc)) from exc
    except Exception as exc:
        if exc.__class__.__module__.startswith("neo4j"):
            raise HTTPException(503, "request persistence unavailable") from exc
        raise


@router.get("/requests")
async def requests(
    principal: Principal = Depends(get_principal),  # noqa: B008
    status: str | None = None,
    start: str | None = None,
    end: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    attempt, started = new_id("attempt"), time.monotonic()
    service._journal(attempt, "lookup_received", validity="valid", tenant_id=principal.tenant_id,
                     org_ids=list(principal.org_ids), request_status=status)
    try:
        items = await service.visible_list(principal, status, start, end, skip, limit)
    except Exception as exc:
        service._journal(attempt, "lookup_failed", tenant_id=principal.tenant_id,
                         org_ids=list(principal.org_ids), request_status="failed",
                         status_code=503, error_class=type(exc).__name__,
                         duration_ms=round((time.monotonic() - started) * 1000))
        raise
    service._journal(attempt, "lookup_completed", tenant_id=principal.tenant_id,
                     org_ids=list(principal.org_ids), request_status=status,
                     status_code=200, duration_ms=round((time.monotonic() - started) * 1000))
    return {"items": items, "skip": skip, "limit": limit}


@router.get("/requests/{request_id}")
async def request_detail(request_id: str, principal: Principal = Depends(get_principal)):  # noqa: B008
    attempt, started = new_id("attempt"), time.monotonic()
    service._journal(attempt, "lookup_received", validity="valid", tenant_id=principal.tenant_id,
                     request_id=request_id, org_ids=list(principal.org_ids))
    try:
        value = await service.visible_detail(principal, request_id)
    except Exception as exc:
        service._journal(attempt, "lookup_failed", tenant_id=principal.tenant_id,
                         org_ids=list(principal.org_ids), request_status="failed",
                         request_id=request_id, status_code=503, error_class=type(exc).__name__,
                         duration_ms=round((time.monotonic() - started) * 1000))
        raise
    if not value:
        service._journal(attempt, "lookup_failed", tenant_id=principal.tenant_id,
                         org_ids=list(principal.org_ids), request_status="not_found",
                         request_id=request_id, status_code=404, validity="invalid",
                         duration_ms=round((time.monotonic() - started) * 1000))
        raise HTTPException(404, "Request not found")
    service._journal(attempt, "lookup_completed", tenant_id=principal.tenant_id,
                     org_ids=list(principal.org_ids),
                     request_status=(value.get("request") or {}).get("status"),
                     request_id=request_id, status_code=200,
                     duration_ms=round((time.monotonic() - started) * 1000))
    return redact_source(principal, value)


@router.get("/requests/{request_id}/evidence/{span_id}")
async def evidence(request_id: str, span_id: str, principal: Principal = Depends(get_principal)):  # noqa: B008
    value = await service.visible_evidence(principal, request_id, span_id)
    if not value:
        raise HTTPException(404, "Evidence not found")
    return redact_source(principal, value)


@router.get("/requests/{request_id}/revisions/{revision}/document")
async def source_document(
    request_id: str,
    revision: str,
    source: str = Query(..., min_length=1),
    principal: Principal = Depends(get_principal),  # noqa: B008
):
    value = await service.visible_document(principal, request_id, revision, source)
    if not value:
        raise HTTPException(404, "Document not found")
    return redact_source(principal, value)
