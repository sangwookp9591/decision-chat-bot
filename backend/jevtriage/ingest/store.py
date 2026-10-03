"""Neo4j persistence for requests, revisions, source attachments and evidence."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from jevtriage.db.idempotency import get_or_create_in_tx
from jevtriage.db.locks import lock_node_in_tx
from jevtriage.db.tx import read_tx, write_tx
from jevtriage.domain.ids import new_id
from jevtriage.domain.runs import start_run_in_tx


async def _create_input(
    tx,
    *,
    tenant_id: str,
    user_id: str,
    request_id: str,
    revision_id: str,
    revision_number: int,
    text: str,
    attachments: list[dict[str, Any]],
    supported: bool,
    first_received_at: str | None = None,
) -> dict[str, Any]:
    await (
        await tx.run(
            "CREATE (i:InputRevision {id:$revision_id,tenant_id:$tenant_id,request_id:$request_id,"
            "number:$number,created_by:$user_id,created_at:datetime(),text:$text}) "
            "WITH i MATCH (r:Request {id:$request_id,tenant_id:$tenant_id}) "
            "CREATE (r)-[:HAS_REVISION]->(i) "
            "SET r.latest_revision_id=$revision_id, r.revision_number=$number "
            "RETURN i.id AS id",
            revision_id=revision_id,
            tenant_id=tenant_id,
            request_id=request_id,
            number=revision_number,
            user_id=user_id,
            text=text,
        )
    ).single(strict=True)
    excluded = []
    # Persist the exact submitted conversation as revision-scoped source spans.
    # Blank-line-delimited paragraphs and sentence spans retain original text offsets.
    paragraphs, paragraph_start = [], 0
    for separator in re.finditer(r"\r?\n[ \t]*\r?\n+", text):
        paragraphs.append((paragraph_start, text[paragraph_start:separator.start()]))
        paragraph_start = separator.end()
    paragraphs.append((paragraph_start, text[paragraph_start:]))
    paragraph_index = 0
    for start_offset, paragraph in paragraphs:
        if not paragraph.strip():
            continue
        sentence_index = 0
        for match in re.finditer(r"[^.!?。！？]+[.!?。！？]*", paragraph):
            sentence = match.group(0)
            if not sentence.strip():
                continue
            start = start_offset + match.start()
            end = start_offset + match.end()
            span_id = new_id("event").replace("evt_", "esp_", 1)
            await (await tx.run(
                "MATCH (i:InputRevision {id:$revision_id,tenant_id:$tenant_id}) "
                "CREATE (e:EvidenceSpan {id:$id,tenant_id:$tenant_id,request_id:$request_id,"
                "revision_id:$revision_id,source:'chat',location_json:$location,"
                "char_start:$start,char_end:$end,text_hash:$text_hash,source_text:$text}) "
                "CREATE (i)-[:HAS_EVIDENCE]->(e)",
                id=span_id, tenant_id=tenant_id, request_id=request_id,
                revision_id=revision_id,
                location=json.dumps({"revision": revision_number, "paragraph": paragraph_index,
                                     "sentence": sentence_index}, ensure_ascii=False),
                start=start, end=end, text_hash=hashlib.sha256(sentence.encode()).hexdigest(),
                text=sentence,
            )).consume()
            sentence_index += 1
        paragraph_index += 1
    for item in attachments:
        attachment_id = item["id"]
        await (
            await tx.run(
                "MATCH (i:InputRevision {id:$revision_id,tenant_id:$tenant_id}) "
                "CREATE (a:Attachment {id:$id,tenant_id:$tenant_id,request_id:$request_id,"
                "revision_id:$revision_id,filename:$filename,path:$path,sha256:$sha256,"
                "byte_count:$byte_count,status:$status,reason:$reason,excluded:$excluded,"
                "created_at:datetime()}) CREATE (i)-[:HAS_ATTACHMENT]->(a)",
                id=attachment_id,
                tenant_id=tenant_id,
                request_id=request_id,
                revision_id=revision_id,
                filename=item["filename"],
                path=item.get("path"),
                sha256=item.get("sha256", ""),
                byte_count=item.get("byte_count", 0),
                status=item["status"],
                reason=item.get("reason"),
                excluded=item["status"] == "excluded",
            )
        ).consume()
        if item["status"] == "rejected":
            excluded.append(item.get("reason", "rejected"))
        for unit in item.get("units", []):
            span_id = new_id("event").replace("evt_", "esp_", 1)
            await (
                await tx.run(
                    "MATCH (i:InputRevision {id:$revision_id,tenant_id:$tenant_id}) "
                    "CREATE (e:EvidenceSpan {id:$id,tenant_id:$tenant_id,request_id:$request_id,"
                    "revision_id:$revision_id,attachment_id:$attachment_id,location_json:$location,"
                    "char_start:$start,char_end:$end,text_hash:$text_hash,source_text:$text}) "
                    "CREATE (i)-[:HAS_EVIDENCE]->(e)",
                    id=span_id,
                    tenant_id=tenant_id,
                    request_id=request_id,
                    revision_id=revision_id,
                    attachment_id=attachment_id,
                    location=json.dumps(unit["location"], ensure_ascii=False),
                    start=unit["char_start"],
                    end=unit["char_end"],
                    text_hash=unit["text_hash"],
                    text=unit["text"],
                )
            ).consume()
    status = "needs_file_decision" if excluded else "received"
    await (
        await tx.run(
            "MATCH (r:Request {id:$request_id,tenant_id:$tenant_id}) "
            # An assigned request keeps its assignment status; only a rejected file changes it.
            "SET r.status=CASE WHEN r.assignment_id IS NOT NULL AND $status='received' "
            "THEN r.status ELSE $status END, r.first_received_at=coalesce(r.first_received_at,datetime($received)), "
            "r.original_exclusion_reasons=coalesce(r.original_exclusion_reasons,$reasons), "
            "r.original_exclusion_count=coalesce(r.original_exclusion_count,size($reasons)), "
            "r.first_supported_revision=CASE WHEN $supported AND size($reasons)=0 "
            "THEN coalesce(r.first_supported_revision,$revision_id) ELSE r.first_supported_revision END, "
            "r.first_supported_at=CASE WHEN $supported AND size($reasons)=0 "
            "THEN coalesce(r.first_supported_at,datetime($received)) ELSE r.first_supported_at END "
            "RETURN r.id AS id",
            request_id=request_id,
            tenant_id=tenant_id,
            status=status,
            received=first_received_at,
            reasons=excluded,
            supported=supported,
            revision_id=revision_id,
        )
    ).consume()
    if supported and not excluded:
        current = await (await tx.run(
            "MATCH (r:Request {id:$request_id,tenant_id:$tenant_id}) "
            "RETURN r.active_run_id AS active_run_id",
            request_id=request_id, tenant_id=tenant_id,
        )).single(strict=True)
        await start_run_in_tx(tx, tenant_id, request_id, revision_id, "normal",
                              expected_active_run_id=current["active_run_id"])
    elif supported and excluded:
        # An otherwise supported revision waits for the requester to resolve rejected files.
        pass
    return {"request_id": request_id, "revision": revision_number, "status": status}


async def create_request(
    tenant_id: str,
    user_id: str,
    text: str,
    attachments: list[dict[str, Any]],
    key: str,
    payload_hash: str,
    received_at: str,
    org_ids: tuple[str, ...] | list[str] = (),
) -> dict[str, Any]:
    request_id, revision_id = new_id("request"), new_id("revision")

    async def op(tx):
        async def create(tx):
            await (
                await tx.run(
                    "CREATE (r:Request {id:$id,tenant_id:$tenant_id,created_by:$user_id,"
                    "created_at:datetime(),status:'received',org_ids:$org_ids})",
                    id=request_id,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    org_ids=list(org_ids),
                )
            ).consume()
            supported = bool(text.strip() or any(a["status"] == "ok" for a in attachments))
            result = await _create_input(
                tx,
                tenant_id=tenant_id,
                user_id=user_id,
                request_id=request_id,
                revision_id=revision_id,
                revision_number=1,
                text=text,
                attachments=attachments,
                supported=supported,
                first_received_at=received_at,
            )
            if supported and not any(a["status"] == "rejected" for a in attachments):
                result["status"] = "judgment_pending"
            return result

        return await get_or_create_in_tx(
            tx, tenant_id, "POST:/api/requests", key, payload_hash, create
        )

    return await write_tx(tenant_id, op)


async def get_request_meta(tenant_id: str, request_id: str) -> dict[str, Any] | None:
    async def op(tx):
        result = await tx.run(
            "MATCH (r:Request {id:$id,tenant_id:$tenant_id}) RETURN r",
            id=request_id,
            tenant_id=tenant_id,
        )
        row = await result.single()
        return dict(row["r"]) if row else None

    return await read_tx(tenant_id, op)


async def list_requests(
    tenant_id: str, predicate: str, params: dict[str, Any]
) -> list[dict[str, Any]]:
    async def op(tx):
        result = await tx.run(
            f"MATCH (r:Request) WHERE {predicate} RETURN r ORDER BY r.created_at DESC "
            "SKIP $skip LIMIT $limit",
            **params,
        )
        return [dict(row["r"]) async for row in result]

    return await read_tx(tenant_id, op)


async def request_detail(tenant_id: str, request_id: str) -> dict[str, Any] | None:
    async def op(tx):
        result = await tx.run(
            "MATCH (r:Request {id:$id,tenant_id:$tenant_id}) "
            "OPTIONAL MATCH (r)-[:HAS_REVISION]->(i:InputRevision) "
            "OPTIONAL MATCH (i)-[:HAS_ATTACHMENT]->(a:Attachment) "
            "OPTIONAL MATCH (active:Run {id:r.active_run_id,tenant_id:$tenant_id}) "
            "RETURN r,collect(DISTINCT i) AS revisions,collect(DISTINCT a) AS attachments,active",
            id=request_id,
            tenant_id=tenant_id,
        )
        row = await result.single()
        if not row:
            return None
        return {
            "request": dict(row["r"]),
            "revisions": [dict(x) for x in row["revisions"] if x],
            "attachments": [dict(x) for x in row["attachments"] if x],
            "active_run": dict(row["active"]) if row["active"] else None,
            "latest_judgment_summary": None,
        }

    return await read_tx(tenant_id, op)


async def get_evidence(tenant_id: str, request_id: str, span_id: str) -> dict[str, Any] | None:
    async def op(tx):
        result = await tx.run(
            "MATCH (e:EvidenceSpan {id:$span_id,request_id:$request_id,tenant_id:$tenant_id}) "
            "RETURN e",
            span_id=span_id,
            request_id=request_id,
            tenant_id=tenant_id,
        )
        row = await result.single()
        return dict(row["e"]) if row else None

    return await read_tx(tenant_id, op)


async def resolve_files(
    tenant_id: str,
    request_id: str,
    user_id: str,
    expected_revision: int,
    exclude: list[str],
    key: str,
    payload_hash: str,
) -> dict[str, Any]:
    async def op(tx):
        r = await lock_node_in_tx(tx, tenant_id, "Request", request_id)
        rid = new_id("revision")

        async def create(tx):
            if not r or r.get("revision_number") != expected_revision:
                raise ValueError("stale_revision")
            old = await tx.run(
                "MATCH (i:InputRevision {id:$revision,tenant_id:$tenant_id}) "
                "OPTIONAL MATCH (i)-[:HAS_ATTACHMENT]->(a:Attachment) "
                "OPTIONAL MATCH (i)-[:HAS_EVIDENCE]->(e:EvidenceSpan {attachment_id:a.id}) "
                "RETURN i,collect(DISTINCT a) AS attachments,collect(DISTINCT e) AS spans",
                revision=r["latest_revision_id"],
                tenant_id=tenant_id,
            )
            row = await old.single(strict=True)
            failed_ids = {a["id"] for a in row["attachments"] if a and a["status"] == "rejected"}
            if set(exclude) != failed_ids:
                raise ValueError("all rejected attachments must be excluded or reattached")
            attachments = []
            for a in row["attachments"]:
                if a:
                    old_id = a["id"]
                    item = dict(a)
                    item["id"] = new_id("event").replace("evt_", "att_")
                    item["status"] = "excluded" if old_id in exclude else item["status"]
                    item["units"] = [
                        {
                            "location": json.loads(span["location_json"]),
                            "char_start": span["char_start"],
                            "char_end": span["char_end"],
                            "text": span["source_text"],
                            "text_hash": span["text_hash"],
                        }
                        for span in row["spans"]
                        if span and span["attachment_id"] == old_id
                    ]
                    attachments.append(item)
            await _create_input(
                tx,
                tenant_id=tenant_id,
                user_id=user_id,
                request_id=request_id,
                revision_id=rid,
                revision_number=expected_revision + 1,
                text=row["i"].get("text", ""),
                attachments=attachments,
                supported=True,
            )
            return {
                "request_id": request_id,
                "revision": expected_revision + 1,
                "status": "judgment_pending",
            }

        return await get_or_create_in_tx(
            tx,
            tenant_id,
            "POST:/api/requests/file-decision/" + request_id,
            key,
            payload_hash,
            create,
        )

    return await write_tx(tenant_id, op)


async def add_revision(
    tenant_id: str,
    request_id: str,
    user_id: str,
    expected_revision: int,
    text: str,
    attachments: list[dict[str, Any]],
    key: str,
    payload_hash: str,
) -> dict[str, Any]:
    revision_id = new_id("revision")

    async def op(tx):
        request = await lock_node_in_tx(tx, tenant_id, "Request", request_id)

        async def create(tx):
            if request.get("revision_number") != expected_revision:
                raise ValueError("stale_revision")
            # Carry forward the prior conversation and eligible source references.
            prev = await tx.run(
                "MATCH (i:InputRevision {id:$id,tenant_id:$tenant_id}) "
                "OPTIONAL MATCH (i)-[:HAS_ATTACHMENT]->(a:Attachment) "
                "OPTIONAL MATCH (i)-[:HAS_EVIDENCE]->(e:EvidenceSpan {attachment_id:a.id}) "
                "RETURN i.text AS text,collect(DISTINCT a) AS old_attachments,collect(DISTINCT e) AS spans",
                id=request["latest_revision_id"],
                tenant_id=tenant_id,
            )
            previous = await prev.single()
            carried = []
            if previous:
                for old in previous["old_attachments"]:
                    if not old:
                        continue
                    item = dict(old)
                    old_id = item["id"]
                    item["id"] = new_id("event").replace("evt_", "att_")
                    item["units"] = [
                        {
                            "location": json.loads(span["location_json"]),
                            "char_start": span["char_start"],
                            "char_end": span["char_end"],
                            "text": span["source_text"],
                            "text_hash": span["text_hash"],
                        }
                        for span in previous["spans"]
                        if span and span["attachment_id"] == old_id
                    ]
                    carried.append(item)
            all_attachments = carried + attachments
            if len(all_attachments) > 5:
                raise ValueError("too_many_attachments")
            combined = (
                (previous["text"] + "\n" + text)
                if previous and previous["text"] and text
                else text or (previous["text"] if previous else "")
            )
            result = await _create_input(
                tx,
                tenant_id=tenant_id,
                user_id=user_id,
                request_id=request_id,
                revision_id=revision_id,
                revision_number=expected_revision + 1,
                text=combined,
                attachments=all_attachments,
                supported=True,
            )
            result["status"] = (
                ("배정 완료" if request.get("assignment_id") else "judgment_pending")
                if not any(a["status"] == "rejected" for a in all_attachments)
                else "needs_file_decision"
            )
            return result

        return await get_or_create_in_tx(
            tx, tenant_id, "POST:/api/requests/revisions/" + request_id, key, payload_hash, create
        )

    return await write_tx(tenant_id, op)
