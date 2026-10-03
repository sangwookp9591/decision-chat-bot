"""Request ingestion orchestration and independent attempt journaling."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path

from jevtriage.config import get_settings
from jevtriage.db.idempotency import get_or_create_in_tx
from jevtriage.db.locks import lock_node_in_tx
from jevtriage.db.tx import write_tx
from jevtriage.domain.ids import new_id
from jevtriage.ingest.files import store_upload
from jevtriage.ingest.parsers import parse_file
from jevtriage.ingest.store import (
    add_revision,
    create_request,
    get_evidence,
    get_request_meta,
    list_requests,
    request_detail,
    resolve_files,
)
from jevtriage.journal.reader import producer_heartbeat
from jevtriage.journal.writer import JournalWriter, failure_count


def _journal(attempt: str, kind: str, **fields) -> None:
    try:
        JournalWriter().append(
            {"event_id": new_id("event"), "attempt_id": attempt, "kind": kind,
             "ts": datetime.now(UTC).isoformat(), **fields}
        )
    finally:
        producer_heartbeat(get_settings().data_dir, "api", failure_count())


def _parse_stored_file(path: Path, filename: str, content_type: str | None):
    """Expose the original suffix while parsing a content-addressed stored file."""
    suffix = Path(filename).suffix.lower()
    if not suffix:
        return parse_file(path, filename, content_type)
    staged = path.with_name(f".parse-{new_id('event')}{suffix}")
    try:
        os.link(path, staged)
        return parse_file(staged, filename, content_type)
    finally:
        staged.unlink(missing_ok=True)


async def reanalyze(principal, request_id: str, expected_revision: int,
                    reason: str | None, key: str) -> dict:
    """Start a new run against the current confirmed input revision."""
    tenant_id = principal.tenant_id
    digest = hashlib.sha256(json.dumps(
        {"expected_revision": expected_revision, "reason": reason},
        sort_keys=True, ensure_ascii=False,
    ).encode()).hexdigest()

    async def op(tx):
        request = await lock_node_in_tx(tx, tenant_id, "Request", request_id)
        if request.get("revision_number") != expected_revision:
            raise ValueError("stale_revision")
        if request.get("latest_revision_id") is None or request.get("status") == "needs_file_decision":
            raise ValueError("revision_unconfirmed")

        async def create(tx):
            revision_id = request["latest_revision_id"]
            run_id, job_id = new_id("run"), new_id("job")
            await (await tx.run(
                "MATCH (i:InputRevision {tenant_id:$tenant,id:$revision,request_id:$request}) "
                "OPTIONAL MATCH (i)-[:HAS_ATTACHMENT]->(a:Attachment) "
                "WITH i, collect(a.status) AS attachment_statuses "
                "WHERE all(status IN attachment_statuses WHERE status IN ['ok','excluded','rejected']) "
                "CREATE (run:Run {id:$run,tenant_id:$tenant,request_id:$request,"
                "input_revision_id:$revision,kind:'reanalysis',status:'pending',reason:$reason,created_at:datetime()}) "
                "CREATE (job:Job {id:$job,tenant_id:$tenant,run_id:$run,kind:'judgment',"
                "input_revision_id:$revision,status:'pending',lease_generation:0,created_by:$actor,created_at:datetime()}) "
                "RETURN run.id AS run_id",
                tenant=tenant_id, revision=revision_id, request=request_id,
                run=run_id, job=job_id, reason=reason, actor=principal.user_id,
            )).single(strict=True)
            await (await tx.run(
                "MATCH (q:Request {tenant_id:$tenant,id:$request}) "
                "SET q.active_run_id=$run,q.status=CASE WHEN q.assignment_id IS NULL "
                "THEN 'judgment_pending' ELSE q.status END",
                tenant=tenant_id, request=request_id, run=run_id,
            )).consume()
            return {"request_id": request_id, "run_id": run_id, "job_id": job_id,
                    "revision_id": revision_id,
                    "status": "judgment_pending" if request.get("assignment_id") is None
                    else request.get("status")}

        return await get_or_create_in_tx(tx, tenant_id, f"reanalyze:{request_id}", key,
                                         digest, create)

    return await write_tx(tenant_id, op)


async def submit(tenant_id: str, user_id: str, text: str, files, key: str,
                 *, org_ids: tuple[str, ...] = ()) -> dict:
    attempt, started = new_id("attempt"), time.monotonic()
    received = datetime.now(UTC).isoformat()
    _journal(attempt, "request_received", validity="valid", tenant_id=tenant_id,
             received_at=received, org_ids=list(org_ids),
             org_id=org_ids[0] if org_ids else None)
    data_dir = get_settings().data_dir
    attachments = []
    try:
        if len(files) > 5:
            raise ValueError("too_many_attachments")
        declared = 0
        for upload in files:  # cheap size probe so an over-limit batch is refused before any parsing
            upload.file.seek(0, 2)
            declared += upload.file.tell()
            upload.file.seek(0)
        if declared > 25 * 1024 * 1024:
            raise ValueError("too_many_bytes")
        total_bytes = 0
        total_chars = len(text)
        for upload in files:
            try:
                path, sha, size = store_upload(upload.file, tenant_id, data_dir)
            except ValueError as exc:
                if str(exc) != "too_large":
                    raise
                upload.file.seek(0, 2)
                rejected_size = upload.file.tell()
                upload.file.seek(0)
                total_bytes += rejected_size
                attachments.append(
                    {
                        "id": new_id("event").replace("evt_", "att_"),
                        "filename": upload.filename or "upload",
                        "path": None,
                        "sha256": "",
                        "byte_count": rejected_size,
                        "status": "rejected",
                        "reason": "too_large",
                        "units": [],
                    }
                )
                continue
            total_bytes += size
            parsed = await asyncio.to_thread(
                _parse_stored_file, path, upload.filename or "upload", upload.content_type)
            total_chars += parsed.char_count
            attachments.append(
                {
                    "id": new_id("event").replace("evt_", "att_"),
                    "filename": upload.filename or "upload",
                    "path": str(path),
                    "sha256": sha,
                    "byte_count": size,
                    "status": parsed.status,
                    "reason": parsed.reason,
                    "units": [
                        {
                            "location": u.location,
                            "char_start": u.char_start,
                            "char_end": u.char_end,
                            "text": u.text,
                            "text_hash": hashlib.sha256(u.text.encode()).hexdigest(),
                        }
                        for u in parsed.units
                    ],
                }
            )
        if total_bytes > 25 * 1024 * 1024:
            raise ValueError("too_many_bytes")
        if total_chars > 20_000:
            raise ValueError("too_many_characters")
        payload_hash = hashlib.sha256(
            json.dumps(
                {"text": text, "files": [(f["filename"], f["sha256"]) for f in attachments]},
                sort_keys=True,
            ).encode()
        ).hexdigest()
        result = await create_request(
            tenant_id, user_id, text, attachments, key, payload_hash, received,
            org_ids=org_ids,
        )
        _journal(
            attempt,
            "request_completed",
            request_id=result["request_id"],
            tenant_id=tenant_id,
            org_ids=list(org_ids),
            org_id=org_ids[0] if org_ids else None,
            request_status=result["status"],
            eligible_first=result["status"] == "judgment_pending",
            file_count=len(attachments),
            excluded_file_count=sum(a["status"] == "rejected" for a in attachments),
            exclusion_reasons=[a["reason"] for a in attachments if a["status"] == "rejected"],
            input_type="attachment" if attachments else "text",
            status_code=202,
            duration_ms=round((time.monotonic() - started) * 1000),
            validity="valid",
        )
        return result
    except Exception as exc:
        db_error = (
            exc.__class__.__module__.startswith("neo4j")
            or "ServiceUnavailable" in exc.__class__.__name__
        )
        _journal(
            attempt,
            "request_failed",
            tenant_id=tenant_id,
            org_ids=list(org_ids),
            org_id=org_ids[0] if org_ids else None,
            request_status="failed",
            status_code=503 if db_error else 400,
            error_class="database_unavailable"
            if db_error
            else ("input_rejected" if isinstance(exc, ValueError) else "ingestion_error"),
            duration_ms=round((time.monotonic() - started) * 1000),
            validity="valid",
        )
        raise


async def visible_meta(principal, request_id: str):
    from jevtriage.auth.core import can_view_request

    meta = await get_request_meta(principal.tenant_id, request_id)
    if not meta or not can_view_request(principal, meta):
        return None
    return meta


async def visible_list(principal, status=None, start=None, end=None, skip=0, limit=50):
    from jevtriage.auth.core import scope_filter_cypher

    predicate = scope_filter_cypher(principal)
    params = {
        "tenant_id": principal.tenant_id,
        "user_id": principal.user_id,
        "org_ids": list(principal.org_ids),
        "skip": skip,
        "limit": limit,
    }
    if status:
        predicate += " AND r.status=$status"
        params["status"] = status
    if start:
        predicate += " AND r.created_at >= datetime($start)"
        params["start"] = start
    if end:
        predicate += " AND r.created_at <= datetime($end)"
        params["end"] = end
    return _public(await list_requests(principal.tenant_id, predicate, params))


def _public(value):
    """Drop server-internal fields (lock token, stored file path) from API payloads."""
    if isinstance(value, dict):
        return {k: _public(v) for k, v in value.items() if k not in {"_lock", "path"}}
    if isinstance(value, list):
        return [_public(v) for v in value]
    return value


async def visible_detail(principal, request_id: str):
    if not await visible_meta(principal, request_id):
        return None
    return _public(await request_detail(principal.tenant_id, request_id))


async def visible_evidence(principal, request_id: str, span_id: str):
    if not principal.can_read_source:
        return None
    if not await visible_meta(principal, request_id):
        return None
    return await get_evidence(principal.tenant_id, request_id, span_id)


async def decide_files(
    principal, request_id: str, expected_revision: int, exclude: list[str], key: str
):
    attempt, started = new_id("attempt"), time.monotonic()
    received = datetime.now(UTC).isoformat()
    _journal(attempt, "eligibility_received", tenant_id=principal.tenant_id,
             request_id=request_id, received_at=received, validity="valid",
             org_ids=list(principal.org_ids))
    payload_hash = hashlib.sha256(
        json.dumps(
            {"exclude": sorted(exclude), "expected_revision": expected_revision}, sort_keys=True
        ).encode()
    ).hexdigest()
    try:
        before = await get_request_meta(principal.tenant_id, request_id)
        result = await resolve_files(
            principal.tenant_id, request_id, principal.user_id, expected_revision,
            exclude, key, payload_hash,
        )
        _journal(attempt, "eligibility_completed", tenant_id=principal.tenant_id,
                 request_id=request_id, status_code=200, org_ids=list(principal.org_ids),
                 request_status=result.get("status"),
                 eligible_first=not (before or {}).get("first_supported_revision")
                 and result.get("status") == "judgment_pending",
                 excluded_file_count=len(exclude), input_type="attachment",
                 duration_ms=round((time.monotonic() - started) * 1000))
        return result
    except Exception as exc:
        _journal(attempt, "eligibility_failed", tenant_id=principal.tenant_id,
                 request_id=request_id, org_ids=list(principal.org_ids),
                 request_status="failed",
                 status_code=503 if exc.__class__.__module__.startswith("neo4j") else 400,
                 error_class=type(exc).__name__,
                 duration_ms=round((time.monotonic() - started) * 1000))
        raise


async def revise(principal, request_id: str, expected_revision: int, text: str, files, key: str):
    attempt, started = new_id("attempt"), time.monotonic()
    received = datetime.now(UTC).isoformat()
    _journal(attempt, "revision_received", tenant_id=principal.tenant_id,
             request_id=request_id, received_at=received, validity="valid",
             org_ids=list(principal.org_ids))
    try:
        before = await get_request_meta(principal.tenant_id, request_id)
        result = await _revise_impl(principal, request_id, expected_revision, text, files, key)
        _journal(attempt, "revision_completed", tenant_id=principal.tenant_id,
                 request_id=request_id, status_code=200, org_ids=list(principal.org_ids),
                 request_status=result.get("status"),
                 eligible_first=not (before or {}).get("first_supported_revision")
                 and result.get("status") == "judgment_pending",
                 input_type="attachment" if files or (before or {}).get("original_exclusion_count") else "text",
                 duration_ms=round((time.monotonic() - started) * 1000))
        return result
    except Exception as exc:
        _journal(attempt, "revision_failed", tenant_id=principal.tenant_id,
                 request_id=request_id, org_ids=list(principal.org_ids),
                 request_status="failed",
                 status_code=503 if exc.__class__.__module__.startswith("neo4j") else 400,
                 error_class=type(exc).__name__,
                 duration_ms=round((time.monotonic() - started) * 1000))
        raise


async def _revise_impl(principal, request_id: str, expected_revision: int, text: str, files, key: str):
    attachments = []
    total = 0
    chars = len(text)
    if len(files) > 5:
        raise ValueError("too_many_attachments")
    for upload in files:
        path, sha, size = store_upload(upload.file, principal.tenant_id, get_settings().data_dir)
        total += size
        parsed = await asyncio.to_thread(
            _parse_stored_file, path, upload.filename or "upload", upload.content_type)
        chars += parsed.char_count
        attachments.append(
            {
                "id": new_id("event").replace("evt_", "att_"),
                "filename": upload.filename or "upload",
                "path": str(path),
                "sha256": sha,
                "byte_count": size,
                "status": "ok" if parsed.status == "ok" else "rejected",
                "reason": parsed.reason,
                "units": [
                    {
                        "location": u.location,
                        "char_start": u.char_start,
                        "char_end": u.char_end,
                        "text": u.text,
                        "text_hash": hashlib.sha256(u.text.encode()).hexdigest(),
                    }
                    for u in parsed.units
                ],
            }
        )
    if total > 25 * 1024 * 1024 or chars > 20_000:
        raise ValueError("input_limit_exceeded")
    payload_hash = hashlib.sha256(
        json.dumps(
            {
                "text": text,
                "files": [(a["filename"], a["sha256"]) for a in attachments],
                "expected_revision": expected_revision,
            },
            sort_keys=True,
        ).encode()
    ).hexdigest()
    result = await add_revision(
        principal.tenant_id,
        request_id,
        principal.user_id,
        expected_revision,
        text,
        attachments,
        key,
        payload_hash,
    )
    return result
