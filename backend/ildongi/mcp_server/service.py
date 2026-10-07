"""MCP projections through the same authorized service paths as the web API."""

from ildongi.auth.policy import can, redact_source
from ildongi.auth.types import Principal
from ildongi.domain.ids import new_id
from ildongi.domain.serialize import json_value
from ildongi.ingest import service as ingest
from ildongi.judgment import service as judgment
from ildongi.review.service import visible_reviews
from ildongi.tasks.service import visible_tasks


async def submit_request(principal: Principal, text: str) -> dict:
    if not principal.roles.intersection({"requester", "reviewer", "operator"}):
        raise PermissionError("업무 요청 접수 권한이 없습니다.")
    if not text.strip():
        raise ValueError("업무 요청 내용을 입력하세요.")
    return await ingest.submit(principal.tenant_id, principal.user_id, text, [],
                               new_id("attempt"), org_ids=principal.org_ids)


async def get_request_result(principal: Principal, request_id: str) -> dict:
    detail = await ingest.visible_detail(principal, request_id)
    if detail is None:
        raise LookupError("요청을 찾을 수 없습니다.")
    if not can(principal, "request:read", detail["request"]):
        detail = redact_source(principal, detail)
    progress = await judgment.visible_progress(principal, request_id)
    final = (await judgment.visible_judgment(principal, request_id)
             if progress and progress["final"] else None)
    return json_value({"request_id": request_id, "status": detail["request"]["status"],
                       "request": detail, "progress": redact_source(principal, progress),
                       "judgment": final})


async def list_my_requests(principal: Principal, limit: int) -> dict:
    # Same visible list as /api/requests: authors and authorized shared organization requests.
    return json_value({"items": await ingest.visible_list(principal, limit=limit)})


async def list_review_queue(principal: Principal, limit: int) -> dict:
    return json_value(await visible_reviews(principal, limit=limit))


async def list_tasks(principal: Principal, limit: int) -> dict:
    # ponytail: web service loads tenant tasks; add store pagination when tenant size grows.
    return json_value({"tasks": redact_source(principal, (await visible_tasks(principal))[:limit])})
