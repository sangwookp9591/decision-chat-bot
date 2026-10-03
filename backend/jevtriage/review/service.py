"""Atomic review decisions, corrections, and assignment creation."""
from __future__ import annotations

import hashlib
import json
from typing import Any

from jevtriage.auth.core import Principal, can_review
from jevtriage.db.audit import append_audit_in_tx
from jevtriage.db.events import append_event_in_tx
from jevtriage.db.idempotency import IdempotencyConflict, get_or_create_in_tx
from jevtriage.db.locks import lock_node_in_tx
from jevtriage.db.requests import assert_active_run_in_tx
from jevtriage.db.tx import write_tx
from jevtriage.domain.ids import new_id
from jevtriage.judgment.eligibility import evaluate_auto_assign
from jevtriage.policy.service import DEFAULT_CONFIG


class ReviewError(Exception):
    def __init__(self, message: str, status_code: int = 422, latest: dict | None = None):
        self.status_code, self.latest = status_code, latest
        super().__init__(message)


def org_key(tenant: str, value: str) -> str:
    names = {"AI팀": "ai", "IT팀": "it", "현업": "business"}
    if value in names:
        return f"{tenant}-{names[value]}"
    return value


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


CLASS_VALUES = {
    "ai_need":{"필요", "불필요", "혼합", "정보 부족"},
    "feasibility":{"가능", "조건부 가능", "현재 불가", "정보 부족"},
    "urgency":{"긴급", "일반", "판단 보류"},
}


def _draft_task(node) -> dict:
    task = dict(node)
    task["collab_orgs"] = json.loads(task.get("collab_orgs") or "[]")
    task["predecessors"] = json.loads(task.get("predecessors") or "[]")
    return task


async def draft_tasks_in_tx(tx, tenant: str, run_id: str, draft_version: int) -> list[dict]:
    rows = await (await tx.run(
        "MATCH (d:Draft {tenant_id:$tenant,run_id:$run,draft_version:$version}) "
        "MATCH (t:DraftTask {tenant_id:$tenant})-[:IN_DRAFT]->(d) RETURN t ORDER BY t.draft_task_id",
        tenant=tenant, run=run_id, version=draft_version,
    )).data()
    return [_draft_task(row["t"]) for row in rows]


async def validate_tasks_in_tx(tx, tenant: str, tasks: list[dict]) -> dict[str, str]:
    if not tasks:
        raise ReviewError("업무 초안이 없습니다")
    ids = [t["draft_task_id"] for t in tasks]
    if len(set(ids)) != len(ids):
        raise ReviewError("중복 초안 업무")
    orgs = {row["id"] for row in await (await tx.run(
        "MATCH (o:Org {tenant_id:$tenant}) RETURN o.id AS id", tenant=tenant,
    )).data()}
    resolved = {}
    for task in tasks:
        for value in [task.get("lead_org"), *(task.get("collab_orgs") or [])]:
            if not value or org_key(tenant, value) not in orgs:
                raise ReviewError("담당 조직이 tenant 범위에 없습니다")
            resolved[value] = org_key(tenant, value)
        if (not task.get("title") or task.get("method") not in {"AI", "일반 기술", "사람"}
                or not task.get("deliverable")):
            raise ReviewError("업무 필수 필드가 없습니다")
        if any(p not in ids for p in task["predecessors"]):
            raise ReviewError("존재하지 않는 선행 업무")
    visiting, visited = set(), set()
    by_id = {t["draft_task_id"]: t for t in tasks}
    def visit(task_id: str):
        if task_id in visiting:
            raise ReviewError("순환 선행 업무")
        if task_id in visited:
            return
        visiting.add(task_id)
        for predecessor in by_id[task_id]["predecessors"]:
            visit(predecessor)
        visiting.remove(task_id)
        visited.add(task_id)
    for task_id in ids:
        visit(task_id)
    return resolved


async def assign_in_tx(tx, tenant: str, request_id: str, run_id: str, revision_id: str,
                       draft_version: int, *, pathway: str, review_id: str | None = None,
                       policy: dict | None = None) -> dict:
    """Call with Request already locked; approval also holds the Review lock."""
    await assert_active_run_in_tx(tx, tenant, request_id, run_id, revision_id)
    request = await (await tx.run(
        "MATCH (q:Request {tenant_id:$tenant,id:$request}) RETURN q",
        tenant=tenant, request=request_id,
    )).single(strict=True)
    if pathway == "review":
        row = await (await tx.run(
            "MATCH (v:Review {tenant_id:$tenant,id:$id,request_id:$request,run_id:$run}) "
            "RETURN v.status AS status,v.draft_version AS draft_version",
            tenant=tenant, id=review_id, request=request_id, run=run_id,
        )).single()
        if row is None or row["status"] != "approved" or row["draft_version"] != draft_version:
            raise ReviewError("승인 검토가 완료되지 않았습니다", 409)
    elif pathway == "auto":
        if request["q"].get("status") != "auto_assign_eligible":
            raise ReviewError("자동 배정 대상이 아닙니다", 409)
        judgment = await (await tx.run(
            "MATCH (j:Judgment {tenant_id:$tenant,request_id:$request,run_id:$run}) RETURN j",
            tenant=tenant, request=request_id, run=run_id,
        )).single(strict=True)
        j = dict(judgment["j"])
        if any(value in {None, "미정", "판단 보류", "정보 부족"} for value in
               (j.get("ai_need"), j.get("feasibility"), j.get("urgency"), j.get("lead_org"))):
            raise ReviewError("미정 분류의 자동 배정은 금지됩니다", 409)
        if j.get("feasibility") != "가능" or j.get("urgency") == "긴급" or not j.get("risk_confirmed"):
            raise ReviewError("필수 검토 대상입니다", 409)
        versions = json.loads(j.get("versions") or "{}")
        config_version = versions.get("config_version")
        if config_version:
            config_row = await (await tx.run(
                "MATCH (c:ConfigVersion {tenant_id:$tenant,version:$version}) RETURN c.config_json AS config",
                tenant=tenant, version=config_version,
            )).single()
            if config_row is None:
                raise ReviewError("실행 고정 정책이 없습니다", 409)
            policy = json.loads(config_row["config"])
        else:
            policy = DEFAULT_CONFIG
        if not policy.get("auto_assign"):
            raise ReviewError("실행 고정 정책이 자동 배정을 허용하지 않습니다", 409)
        risk = json.loads(j.get("risks") or "{}")
        if any(risk.get(k, 1) > policy.get("risk_clear_max", .2) for k in
               ("clinical_safety", "pharmacovigilance", "regulatory")):
            raise ReviewError("위험 필수 검토 대상입니다", 409)
        outputs = await (await tx.run(
            "MATCH (o:ModelOutput {tenant_id:$tenant,run_id:$run}) RETURN o.question_id AS id,"
            "o.confidence AS confidence,o.noul AS noul",
            tenant=tenant, run=run_id,
        )).data()
        signals = {r["id"]: r["noul"] for r in outputs if r["noul"] is not None}
        confidences = {r["id"]: r["confidence"] for r in outputs if r["confidence"] is not None}
        evidence = await (await tx.run(
            "MATCH (o:ModelOutput {tenant_id:$tenant,run_id:$run})-[:CITES]->"
            "(:EvidenceSpan {tenant_id:$tenant,revision_id:$revision}) RETURN count(*) AS n",
            tenant=tenant, run=run_id, revision=revision_id,
        )).single(strict=True)
        input_row = await (await tx.run(
            "MATCH (i:InputRevision {tenant_id:$tenant,id:$revision}) "
            "OPTIONAL MATCH (i)-[:HAS_ATTACHMENT]->(a:Attachment) "
            "RETURN collect(a.status) AS statuses", tenant=tenant, revision=revision_id,
        )).single(strict=True)
        tasks = await draft_tasks_in_tx(tx, tenant, run_id, draft_version)
        allowed, reasons = evaluate_auto_assign(
            {**{k:j.get(k) for k in ("ai_need", "feasibility", "urgency", "lead_org")},
             "risk_signals":risk, "risk_confirmed":j.get("risk_confirmed"),
             "signals":signals, "choice_confidences":confidences, "draft_tasks":tasks}, policy,
            {"input_confirmed":"rejected" not in input_row["statuses"],
             "latest_run":True, "evidence_complete":evidence["n"] > 0,
             "already_assigned":False},
        )
        if not allowed:
            raise ReviewError("자동 배정 조건 미충족: " + ", ".join(reasons), 409)
    else:
        raise ValueError("unknown assignment pathway")
    existing = await (await tx.run(
        "MATCH (a:Assignment {tenant_id:$tenant,request_id:$request}) RETURN a.id AS id",
        tenant=tenant, request=request_id,
    )).single()
    if existing:
        raise ReviewError("이미 배정된 요청입니다", 409)
    tasks = await draft_tasks_in_tx(tx, tenant, run_id, draft_version)
    orgs = await validate_tasks_in_tx(tx, tenant, tasks)
    judgment_row = await (await tx.run(
        "MATCH (j:Judgment {tenant_id:$tenant,run_id:$run}) "
        "RETURN j.feasibility AS feasibility",
        tenant=tenant, run=run_id,
    )).single(strict=True)
    unresolved_feasibility = judgment_row["feasibility"] != "가능"
    assignment_id = new_id("assignment")
    await (await tx.run(
        "MATCH (q:Request {tenant_id:$tenant,id:$request}) "
        "CREATE (a:Assignment {id:$id,tenant_id:$tenant,request_id:$request,"
        "run_id:$run,revision_id:$revision,draft_version:$version,pathway:$pathway,"
        "review_id:$review_id,created_at:datetime()}) "
        "CREATE (q)-[:HAS_ASSIGNMENT]->(a) SET q.status='배정 완료',q.assignment_id=$id",
        tenant=tenant, request=request_id, id=assignment_id, run=run_id,
        revision=revision_id, version=draft_version, pathway=pathway, review_id=review_id,
    )).consume()
    task_ids = {}
    for draft in tasks:
        task_id = new_id("task")
        task_ids[draft["draft_task_id"]] = task_id
        confirmation_task = (not draft["predecessors"] and
                             (draft.get("method") == "사람" or
                              any(term in draft["title"] for term in ("확인", "검토", "확정"))))
        blocked = bool(draft.get("reason") or draft["predecessors"] or
                       draft.get("status") == "undetermined" or
                       (unresolved_feasibility and not confirmation_task))
        await (await tx.run(
            "MATCH (q:Request {tenant_id:$tenant,id:$request}) "
            "MATCH (a:Assignment {tenant_id:$tenant,id:$assignment}) "
            "CREATE (t:Task {id:$id,tenant_id:$tenant,request_id:$request,"
            "assignment_id:$assignment,draft_task_id:$draft_task_id,run_id:$run,"
            "draft_version:$version,title:$title,method:$method,lead_org:$lead_org,"
            "collab_orgs:$collab_orgs,deliverable:$deliverable,predecessors:$predecessors,"
            "reason:$reason,status:$status,created_at:datetime()}) "
            "CREATE (q)-[:HAS_TASK]->(t) CREATE (a)-[:HAS_TASK]->(t)",
            tenant=tenant, request=request_id, assignment=assignment_id, id=task_id,
            draft_task_id=draft["draft_task_id"], run=run_id, version=draft_version,
            title=draft["title"], method=draft["method"], lead_org=draft["lead_org"],
            collab_orgs=_json(draft["collab_orgs"]), deliverable=draft["deliverable"],
            predecessors=_json(draft["predecessors"]), reason=draft.get("reason"),
            status="막힘" if blocked else "대기",
        )).consume()
        for role, name in [("lead", draft["lead_org"]),
                           *(("collab", x) for x in draft["collab_orgs"] if x != draft["lead_org"])]:
            await (await tx.run(
                "MATCH (t:Task {tenant_id:$tenant,id:$task}) "
                "MATCH (o:Org {tenant_id:$tenant,id:$org}) "
                "CREATE (t)-[:ASSIGNED_TO {role:$role}]->(o)",
                tenant=tenant, task=task_id, org=orgs[name], role=role,
            )).consume()
    for draft in tasks:
        for predecessor in draft["predecessors"]:
            await (await tx.run(
                "MATCH (before:Task {tenant_id:$tenant,id:$before}) "
                "MATCH (after:Task {tenant_id:$tenant,id:$after}) "
                "CREATE (before)-[:PRECEDES]->(after)",
                tenant=tenant, before=task_ids[predecessor], after=task_ids[draft["draft_task_id"]],
            )).consume()
    return {"assignment_id": assignment_id, "task_ids": task_ids}


async def decide(principal: Principal, review_id: str, command: dict, key: str) -> dict:
    tenant = principal.tenant_id
    digest = hashlib.sha256(_json(command).encode()).hexdigest()
    async def op(tx):
        request_id = command["request_id"]
        try:
            request = await lock_node_in_tx(tx, tenant, "Request", request_id)
        except LookupError as exc:
            raise ReviewError("검토를 찾을 수 없습니다", 404) from exc
        try:
            review = await lock_node_in_tx(tx, tenant, "Review", review_id)
        except LookupError as exc:
            raise ReviewError("검토를 찾을 수 없습니다", 404) from exc
        if review.get("request_id") != request_id:
            raise ReviewError("검토를 찾을 수 없습니다", 404)
        meta = dict(request)
        reviewer_org = org_key(tenant, review.get("required_reviewer_org") or "")
        if review.get("required_reviewer_org") == "검토자":
            reviewer_org = next(iter(principal.org_ids), "")
        meta["org_ids"] = list(set(meta.get("org_ids") or []) | {reviewer_org})
        if not can_review(principal, meta) or reviewer_org not in principal.org_ids:
            raise ReviewError("검토 권한이 없습니다", 403)
        async def create(tx):
            latest_row = await (await tx.run(
                "MATCH (v:Review {tenant_id:$tenant,request_id:$request,run_id:$run}) "
                "RETURN v.id AS id,v.draft_version AS draft_version,"
                "v.review_version AS review_version,v.status AS status "
                "ORDER BY v.created_at DESC LIMIT 1",
                tenant=tenant, request=request_id, run=request.get("active_run_id"),
            )).single()
            latest = {"request_id":request_id, "input_revision":request.get("latest_revision_id"),
                      "run_id":request.get("active_run_id"),
                      "review_id":latest_row["id"] if latest_row else None,
                      "draft_version":latest_row["draft_version"] if latest_row else None,
                      "review_version":latest_row["review_version"] if latest_row else None,
                      "status":latest_row["status"] if latest_row else request.get("status")}
            if (review.get("status") != "pending" or
                any(command[k] != latest[k] for k in
                    ("input_revision", "run_id", "draft_version", "review_version")) or
                review.get("revision_id") != command["input_revision"] or
                review.get("run_id") != command["run_id"]):
                raise ReviewError("검토 대상이 변경되었습니다", 409, latest)
            await assert_active_run_in_tx(tx, tenant, request_id, command["run_id"], command["input_revision"])
            changes = command.get("changes") or {}
            action = command["action"]
            if action in {"reject", "approve_with_changes"} and not (command.get("reason") or "").strip():
                raise ReviewError("사유가 필요합니다")
            if action == "request_info" and not (command.get("reason") or "").strip():
                raise ReviewError("필요한 정보를 적어야 합니다")
            if action != "approve_with_changes" and changes:
                raise ReviewError("수정은 수정 승인에서만 허용됩니다")
            if action == "approve_with_changes" and not changes:
                raise ReviewError("수정 승인에는 변경 항목이 필요합니다")
            if set(changes) - {"classifications", "draft_tasks"}:
                raise ReviewError("허용되지 않은 수정 항목")
            needed_info = command.get("needed_info") or ([command["reason"]] if action == "request_info" else [])
            if action != "request_info" and needed_info:
                raise ReviewError("필요 정보 목록은 정보 요청에서만 허용됩니다")
            if any(not isinstance(item, str) or not item.strip() for item in needed_info):
                raise ReviewError("필요 정보 목록을 확인해 주세요")
            tasks = await draft_tasks_in_tx(tx, tenant, command["run_id"], command["draft_version"])
            if action.startswith("approve"):
                await validate_tasks_in_tx(tx, tenant, tasks)
            judgment_row = await (await tx.run(
                "MATCH (j:Judgment {tenant_id:$tenant,run_id:$run}) RETURN j",
                tenant=tenant, run=command["run_id"],
            )).single(strict=True)
            judgment = dict(judgment_row["j"])
            new_version = command["draft_version"]
            if changes:
                new_version += 1
                for name, value in (changes.get("classifications") or {}).items():
                    if name not in {"ai_need", "feasibility", "urgency", "lead_org"} or not isinstance(value, str) or not value:
                        raise ReviewError("허용되지 않은 분류 수정")
                    if name in CLASS_VALUES and value not in CLASS_VALUES[name]:
                        raise ReviewError("허용되지 않은 분류값")
                    if name == "lead_org" and org_key(tenant, value) not in principal.org_ids:
                        raise ReviewError("담당 조직이 검토자 범위에 없습니다", 403)
                task_edits = changes.get("draft_tasks") or []
                by_id = {t["draft_task_id"]:dict(t) for t in tasks}
                for edit in task_edits:
                    task_id = edit.get("draft_task_id")
                    if task_id not in by_id:
                        raise ReviewError("없는 초안 업무 수정")
                    if set(edit) - {"draft_task_id", "title", "method", "lead_org", "collab_orgs", "deliverable", "predecessors", "reason"}:
                        raise ReviewError("허용되지 않은 업무 수정")
                    by_id[task_id].update(edit)
                tasks = list(by_id.values())
                await validate_tasks_in_tx(tx, tenant, tasks)
                draft_id = f"drf_{new_id('event')[4:]}"
                await (await tx.run(
                    "MATCH (r:Run {tenant_id:$tenant,id:$run}) "
                    "CREATE (d:Draft {id:$id,tenant_id:$tenant,request_id:$request,"
                    "revision_id:$revision,run_id:$run,draft_version:$version,"
                    "created_at:datetime(),author:$actor}) CREATE (r)-[:PRODUCED]->(d)",
                    tenant=tenant, run=command["run_id"], request=request_id,
                    revision=command["input_revision"], id=draft_id,
                    version=new_version, actor=principal.user_id,
                )).consume()
                for task in tasks:
                    await (await tx.run(
                        "MATCH (d:Draft {tenant_id:$tenant,id:$draft}) "
                        "CREATE (t:DraftTask {id:$id,tenant_id:$tenant,request_id:$request,"
                        "run_id:$run,draft_task_id:$task_id,draft_version:$version,"
                        "title:$title,method:$method,lead_org:$lead_org,collab_orgs:$collab,"
                        "deliverable:$deliverable,predecessors:$predecessors,status:$status,"
                        "reason:$reason,author:$actor}) CREATE (t)-[:IN_DRAFT]->(d)",
                        tenant=tenant, draft=draft_id, id=f"{draft_id}_{task['draft_task_id']}",
                        request=request_id, run=command["run_id"], task_id=task["draft_task_id"],
                        version=new_version, title=task["title"], method=task["method"],
                        lead_org=task["lead_org"], collab=_json(task["collab_orgs"]),
                        deliverable=task["deliverable"], predecessors=_json(task["predecessors"]),
                        status=task.get("status", "draft"), reason=task.get("reason"),
                        actor=principal.user_id,
                    )).consume()
            decision_id = f"rdec_{new_id('event')[4:]}"
            status = {"approve":"approved", "approve_with_changes":"approved",
                      "reject":"rejected", "request_info":"info_requested"}[action]
            await (await tx.run(
                "MATCH (v:Review {tenant_id:$tenant,id:$review}) "
                "CREATE (h:ReviewDecision {id:$id,tenant_id:$tenant,request_id:$request,"
                "review_id:$review,revision_id:$revision,run_id:$run,action:$action,"
                "reason:$reason,needed_info:$needed_info,actor_id:$actor,review_version:$review_version,"
                "draft_version:$draft_version,created_at:datetime()}) "
                "CREATE (v)-[:HAS_DECISION]->(h) "
                "SET v.status=$status,v.review_version=v.review_version+1,v.draft_version=$new_version,"
                "v.decided_at=datetime(),v.decided_by=$actor",
                tenant=tenant, review=review_id, id=decision_id, request=request_id,
                revision=command["input_revision"], run=command["run_id"], action=action,
                reason=command.get("reason"), actor=principal.user_id,
                needed_info=_json(needed_info),
                review_version=command["review_version"], draft_version=command["draft_version"],
                status=status, new_version=new_version,
            )).consume()
            correction_ids = []
            if changes:
                old_tasks = {t["draft_task_id"]:t for t in await draft_tasks_in_tx(
                    tx, tenant, command["run_id"], command["draft_version"])}
                fields = []
                for field, value in (changes.get("classifications") or {}).items():
                    fields.append((field, judgment.get(field), value, None))
                for task in tasks:
                    for field in ("title", "method", "lead_org", "collab_orgs", "deliverable", "predecessors", "reason"):
                        old = old_tasks[task["draft_task_id"]].get(field)
                        if old != task.get(field):
                            fields.append((f"draft_tasks.{task['draft_task_id']}.{field}", old, task.get(field), task["draft_task_id"]))
                if not any(old != new for _, old, new, _ in fields):
                    raise ReviewError("실제 수정 항목이 없습니다")
                version_info = json.loads(judgment.get("versions") or "{}")
                for field, old, new, task_id in fields:
                    if old == new:
                        continue
                    question_id = field if task_id is None else None
                    output = await (await tx.run(
                        "MATCH (o:ModelOutput {tenant_id:$tenant,run_id:$run,question_id:$question}) "
                        "OPTIONAL MATCH (o)-[:CITES]->(e:EvidenceSpan {tenant_id:$tenant}) "
                        "RETURN o.id AS id,collect(e.id) AS spans LIMIT 1",
                        tenant=tenant, run=command["run_id"], question=question_id,
                    )).single() if question_id else None
                    # Draft fields have no direct ModelOutput if decomposition was catalog authored.
                    model_id = output["id"] if output else None
                    spans = output["spans"] if output else []
                    correction_id = new_id("correction")
                    await (await tx.run(
                        "MATCH (h:ReviewDecision {tenant_id:$tenant,id:$decision}) "
                        "CREATE (c:Correction {id:$id,tenant_id:$tenant,request_id:$request,"
                        "revision_id:$revision,run_id:$run,review_id:$review,field:$field,"
                        "ai_value:$ai,corrected_value:$corrected,reason:$reason,"
                        "evidence_span_ids:$spans,corrected_by:$actor,corrected_at:datetime(),"
                        "config_version:$config_version,created_at:datetime()}) "
                        "CREATE (h)-[:RECORDED]->(c)",
                        tenant=tenant, decision=decision_id, id=correction_id,
                        request=request_id, revision=command["input_revision"],
                        run=command["run_id"], review=review_id, field=field,
                        ai=_json(old), corrected=_json(new), reason=command["reason"],
                        spans=spans, actor=principal.user_id,
                        config_version=version_info.get("config_version", 0),
                    )).consume()
                    if model_id:
                        await (await tx.run(
                            "MATCH (c:Correction {tenant_id:$tenant,id:$correction}) "
                            "MATCH (o:ModelOutput {tenant_id:$tenant,id:$output}) "
                            "CREATE (c)-[:CORRECTS]->(o)",
                            tenant=tenant, correction=correction_id, output=model_id,
                        )).consume()
                    correction_ids.append(correction_id)
            assignment = None
            if action.startswith("approve"):
                assignment = await assign_in_tx(tx, tenant, request_id, command["run_id"],
                                                command["input_revision"], new_version,
                                                pathway="review", review_id=review_id)
            else:
                await (await tx.run(
                    "MATCH (q:Request {tenant_id:$tenant,id:$request}) "
                    "SET q.status=$status,q.info_requested=$info,q.needed_info=$needed_info",
                    tenant=tenant, request=request_id,
                    status="반려" if action == "reject" else "보완 필요",
                    info=command.get("reason") if action == "request_info" else None,
                    needed_info=_json(needed_info) if action == "request_info" else None,
                )).consume()
            result = {"review_id":review_id,"decision_id":decision_id,"action":action,
                      "status":status,"review_version":command["review_version"]+1,
                      "draft_version":new_version,"assignment":assignment,
                      "correction_ids":correction_ids,"needed_info":needed_info}
            await append_audit_in_tx(tx, tenant, principal.user_id, f"review.{action}",
                                     "Review", review_id,
                                     {"status":"pending","review_version":command["review_version"]},
                                     result, command.get("reason") or action)
            await append_event_in_tx(tx, tenant, "review_decided", result,
                                     request_id=request_id, run_id=command["run_id"])
            return result
        return await get_or_create_in_tx(tx, tenant, f"review:{review_id}", key, digest, create)
    try:
        return await write_tx(tenant, op)
    except IdempotencyConflict as exc:
        raise ReviewError(str(exc), 409) from exc


async def auto_assign_after_judgment_in_tx(tx, ctx, *, eligible: bool) -> dict | None:
    if not eligible:
        return None
    # ctx.commit already verified Job ownership and active run in this transaction.
    existing = await (await tx.run(
        "MATCH (a:Assignment {tenant_id:$tenant,request_id:$request}) RETURN a.id AS id",
        tenant=ctx.tenant_id, request=ctx.request_id,
    )).single()
    if existing:
        await (await tx.run(
            "MATCH (q:Request {tenant_id:$tenant,id:$request}) "
            "SET q.status='배정 완료',q.assignment_id=$assignment",
            tenant=ctx.tenant_id, request=ctx.request_id, assignment=existing["id"],
        )).consume()
        return None
    try:
        assigned = await assign_in_tx(tx, ctx.tenant_id, ctx.request_id, ctx.run_id,
                                      ctx.revision_id, 1, pathway="auto",
                                      policy=ctx.policy_snapshot)
    except ReviewError as exc:
        # An invalid draft or a tightened gate becomes a human review without
        # discarding the already completed first judgment.
        await (await tx.run(
            "MATCH (j:Judgment {tenant_id:$tenant,run_id:$run}) "
            "MATCH (q:Request {tenant_id:$tenant,id:$request}) "
            "CREATE (:Review {id:$review_id,tenant_id:$tenant,status:'pending',"
            "request_id:$request,revision_id:$revision,run_id:$run,draft_version:1,"
            "review_version:1,reasons:$reasons,required_reviewer_org:$org,"
            "created_at:datetime()}) SET q.status='검토 대기'",
            tenant=ctx.tenant_id, request=ctx.request_id, run=ctx.run_id,
            revision=ctx.revision_id, review_id=new_id("review"),
            reasons=_json([str(exc)]), org="검토자",
        )).consume()
        await append_event_in_tx(tx, ctx.tenant_id, "auto_assignment_deferred",
                                 {"reason":str(exc)}, request_id=ctx.request_id,
                                 run_id=ctx.run_id)
        return None
    await append_audit_in_tx(tx, ctx.tenant_id, "system:judgment", "assignment.auto",
                             "Assignment", assigned["assignment_id"], None, assigned,
                             "실행 고정 정책의 자동 배정 조건 충족")
    await append_event_in_tx(tx, ctx.tenant_id, "assignment_created", assigned,
                             request_id=ctx.request_id, run_id=ctx.run_id)
    return assigned
