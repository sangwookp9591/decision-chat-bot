"""Persistence and queries for immutable per-run judgments."""
from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from ildongi.db.events import append_event_in_tx
from ildongi.db.tx import read_tx
from ildongi.domain.ids import new_id


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


async def load_input(tenant_id: str, request_id: str, revision_id: str) -> tuple[list[dict], str, bool]:
    async def op(tx):
        result = await tx.run(
            "MATCH (i:InputRevision {tenant_id:$tenant_id,id:$revision_id,request_id:$request_id}) "
            "OPTIONAL MATCH (i)-[:HAS_EVIDENCE]->(e:EvidenceSpan) "
            "OPTIONAL MATCH (i)-[:HAS_ATTACHMENT]->(a:Attachment) "
            "RETURN i.text AS text,collect(DISTINCT e) AS spans,collect(DISTINCT a) AS attachments",
            tenant_id=tenant_id, request_id=request_id, revision_id=revision_id,
        )
        row = await result.single()
        if row is None:
            raise LookupError("input revision absent")
        if any(a and a.get("status") == "rejected" for a in row["attachments"]):
            raise ValueError("input files are not confirmed")
        units = [{"unit_id": s["id"], "text": s["source_text"]} for s in row["spans"] if s]
        units.sort(key=lambda item: item["unit_id"])
        return units, row["text"] or "", True
    return await read_tx(tenant_id, op)


async def save_judgment_in_tx(tx, ctx, result: dict, *, policy_version: int,
                              ai_step_id: str, reasons: list[str], eligible: bool,
                              compare_only: bool = False) -> str:
    """Called only inside ctx.commit(affects_request=True)."""
    tenant_id, request_id, run_id = ctx.tenant_id, ctx.request_id, ctx.run_id
    revision_id = ctx.revision_id
    existing = await (await tx.run(
        "MATCH (j:Judgment {tenant_id:$tenant_id,request_id:$request_id,run_id:$run_id}) "
        "RETURN j.id AS id LIMIT 1",
        tenant_id=tenant_id, request_id=request_id, run_id=run_id,
    )).single()
    if existing:
        return existing["id"]
    judgment_id = f"jdg_{uuid4().hex}"
    draft_id = f"drf_{uuid4().hex}"
    versions = {**result["versions"], "config_version": policy_version}
    classes = result["classifications"]
    answers = result["raw_model_output"]["answers"]
    risk_values = {key: answer["noul"] for key, answer in answers.items()
                   if key in {"clinical_safety", "pharmacovigilance", "regulatory"}}
    risk_clear_max = ctx.policy_snapshot.get("risk_clear_max", 0.2)
    risk_confirmed = len(risk_values) == 3 and all(v <= risk_clear_max for v in risk_values.values())
    await (await tx.run(
        "MATCH (r:Run {tenant_id:$tenant_id,id:$run_id,request_id:$request_id}) "
        "CREATE (j:Judgment {id:$judgment_id,tenant_id:$tenant_id,request_id:$request_id,"
        "revision_id:$revision_id,run_id:$run_id,ai_need:$ai_need,feasibility:$feasibility,"
        "urgency:$urgency,lead_org:$lead_org,risk_confirmed:$risk_confirmed,risks:$risks,"
        "summary:$summary,author:$author,versions:$versions,eligibility_json:$eligibility,"
        "mode:$mode,questions_json:$questions,llm_json:$llm,created_at:datetime()}) "
        "CREATE (r)-[:PRODUCED]->(j)",
        tenant_id=tenant_id, request_id=request_id, revision_id=revision_id, run_id=run_id,
        judgment_id=judgment_id, **classes, risk_confirmed=risk_confirmed,
        risks=_json(risk_values), summary=_json(result["summary"]),
        author=result["summary"].get("author", "code:extractive@1"),
        versions=_json(versions), eligibility=_json({"allowed": eligible, "reasons": reasons}),
        mode=result["usage"]["mode"],
        questions=_json(result["questions"]) if result.get("questions") else None,
        llm=_json(result["llm"]) if result.get("llm") else None,
    )).consume()
    valid_citations = result.get("evidence", {})
    for question_id, answer in answers.items():
        output_id = f"mout_{uuid4().hex}"
        value = answer.get("choice", answer.get("score", answer.get("noul")))
        await (await tx.run(
            "MATCH (j:Judgment {tenant_id:$tenant_id,id:$judgment_id}) "
            "MATCH (s:RunStep {tenant_id:$tenant_id,id:$step_id,run_id:$run_id}) "
            "CREATE (o:ModelOutput {id:$id,tenant_id:$tenant_id,question_id:$question_id,"
            "type:$type,value:$value,confidence:$confidence,probabilities:$probabilities,"
            "noul:$noul,legend:$legend,model:$model,run_id:$run_id}) "
            "CREATE (o)-[:OF_JUDGMENT]->(j) CREATE (s)-[:USED_OUTPUT]->(o)",
            tenant_id=tenant_id, judgment_id=judgment_id, step_id=ai_step_id,
            run_id=run_id, id=output_id, question_id=question_id, type=answer["type"],
            value=value, confidence=answer.get("confidence"),
            probabilities=_json(answer["probabilities"]) if "probabilities" in answer else None,
            noul=answer.get("noul"), legend=_json(answer["legend"]) if "legend" in answer else None,
            model=result["versions"]["model"],
        )).consume()
        for citation in valid_citations.get(question_id, []):
            span_id = citation.get("unit_id")
            # A citation is persisted only when it resolves to a real span of this revision.
            await (await tx.run(
                "MATCH (o:ModelOutput {tenant_id:$tenant_id,id:$output_id}) "
                "MATCH (e:EvidenceSpan {tenant_id:$tenant_id,id:$span_id,request_id:$request_id,revision_id:$revision_id}) "
                "CREATE (o)-[:CITES {prob:$prob}]->(e)",
                tenant_id=tenant_id, output_id=output_id, span_id=span_id,
                request_id=request_id, revision_id=revision_id,
                prob=citation["probability"],
            )).consume()
    await (await tx.run(
        "MATCH (r:Run {tenant_id:$tenant_id,id:$run_id}) "
        "CREATE (d:Draft {id:$draft_id,tenant_id:$tenant_id,request_id:$request_id,"
        "revision_id:$revision_id,draft_version:1,run_id:$run_id,created_at:datetime()}) "
        "CREATE (r)-[:PRODUCED]->(d)",
        tenant_id=tenant_id, run_id=run_id, draft_id=draft_id,
        request_id=request_id, revision_id=revision_id,
    )).consume()
    for task in result["draft_tasks"]:
        await (await tx.run(
            "MATCH (d:Draft {tenant_id:$tenant_id,id:$draft_id}) "
            "CREATE (t:DraftTask {id:$id,tenant_id:$tenant_id,request_id:$request_id,run_id:$run_id,"
            "draft_task_id:$draft_task_id,draft_version:1,title:$title,method:$method,"
            "lead_org:$lead_org,collab_orgs:$collab_orgs,deliverable:$deliverable,"
            "predecessors:$predecessors,status:$status,reason:$reason,author:$author,"
            "description:$description,description_author:$description_author}) "
            "CREATE (t)-[:IN_DRAFT]->(d)",
            tenant_id=tenant_id, draft_id=draft_id, request_id=request_id, run_id=run_id,
            id=f"{draft_id}_{task['draft_task_id']}", draft_task_id=task["draft_task_id"],
            title=task.get("title", "미정"), method=task.get("method", "미정"),
            lead_org=task.get("lead_org", "미정"),
            collab_orgs=_json(task.get("collab_orgs", task.get("collab_org", []))),
            deliverable=task.get("deliverable", "미정"),
            predecessors=_json(task.get("predecessors", [])),
            status="undetermined" if task.get("status") in {"미정", "undetermined"} else "draft",
            description=task.get("description"), description_author=task.get("description_author"),
            reason=task.get("reason"), author=task.get("author", "code:decompose"),
        )).consume()
    status = "auto_assign_eligible" if eligible else "검토 대기"
    if not compare_only:
        # The Request lock held by ctx.commit serializes this transition with
        # review decisions and other runs. Historical reviews remain auditable.
        await (await tx.run(
            "MATCH (v:Review {tenant_id:$tenant_id,request_id:$request_id,status:'pending'}) "
            "WHERE v.run_id <> $run_id "
            "SET v.status='superseded',v.reason='newer_run',"
            "v.superseded_by=$run_id,v.superseded_at=datetime()",
            tenant_id=tenant_id, request_id=request_id, run_id=run_id,
        )).consume()
    if not compare_only and not eligible:
        await (await tx.run(
            "CREATE (:Review {id:$id,tenant_id:$tenant_id,status:'pending',request_id:$request_id,"
            "revision_id:$revision_id,run_id:$run_id,draft_version:1,review_version:1,"
            "reasons:$reasons,required_reviewer_org:$org,created_at:datetime()})",
            id=new_id("review"), tenant_id=tenant_id, request_id=request_id,
            revision_id=revision_id, run_id=run_id, reasons=_json(reasons),
            org=classes.get("lead_org") if classes.get("lead_org") not in {None, "미정", "판단 보류"} else "검토자",
        )).consume()
    await (await tx.run(
        "MATCH (r:Run {tenant_id:$tenant_id,id:$run_id}) "
        "MATCH (q:Request {tenant_id:$tenant_id,id:$request_id}) "
        "SET r.first_judgment_committed_at=coalesce(r.first_judgment_committed_at,datetime()), "
        "r.policy_version=$policy_version,r.config_version=$policy_version",
        tenant_id=tenant_id, run_id=run_id, request_id=request_id, policy_version=policy_version,
    )).consume()
    if compare_only:
        await append_event_in_tx(tx, tenant_id, "reanalysis.compared",
            {"judgment_id": judgment_id, "mode": result["usage"]["mode"]},
            request_id=request_id, run_id=run_id)
    else:
        await (await tx.run(
            "MATCH (q:Request {tenant_id:$tenant_id,id:$request_id}) "
            "SET q.status=$status,q.latest_judgment_id=$judgment_id",
            tenant_id=tenant_id, request_id=request_id,
            status=status, judgment_id=judgment_id,
        )).consume()
        await append_event_in_tx(tx, tenant_id, "judgment_saved",
            {"judgment_id": judgment_id, "status": status, "mode": result["usage"]["mode"],
             "classifications": classes},
            request_id=request_id, run_id=run_id)
    return judgment_id


async def get_judgment(tenant_id: str, request_id: str, run_id: str) -> dict | None:
    async def op(tx):
        row = await (await tx.run(
            "MATCH (j:Judgment {tenant_id:$tenant_id,request_id:$request_id,run_id:$run_id}) "
            "RETURN j ORDER BY j.created_at DESC LIMIT 1",
            tenant_id=tenant_id, request_id=request_id, run_id=run_id,
        )).single()
        if not row:
            return None
        j = dict(row["j"])
        outputs = await (await tx.run(
            "MATCH (o:ModelOutput {tenant_id:$tenant_id,run_id:$run_id})-[:OF_JUDGMENT]->"
            "(j:Judgment {tenant_id:$tenant_id,id:$judgment_id}) "
            "OPTIONAL MATCH (o)-[c:CITES]->(e:EvidenceSpan {tenant_id:$tenant_id}) "
            "RETURN o,collect(CASE WHEN e IS NULL THEN null ELSE {id:e.id,attachment_id:e.attachment_id,"
            "location_json:e.location_json,char_start:e.char_start,char_end:e.char_end,"
            "prob:c.prob,source:e.source,source_text:e.source_text} END) AS citations",
            tenant_id=tenant_id, run_id=run_id, judgment_id=j["id"],
        )).data()
        drafts = await (await tx.run(
            "MATCH (d:Draft {tenant_id:$tenant_id,run_id:$run_id}) "
            "OPTIONAL MATCH (t:DraftTask {tenant_id:$tenant_id})-[:IN_DRAFT]->(d) "
            "WITH d,t ORDER BY t.id RETURN d,collect(t) AS tasks ORDER BY d.draft_version",
            tenant_id=tenant_id, run_id=run_id,
        )).data()
        review = await (await tx.run(
            "MATCH (v:Review {tenant_id:$tenant_id,request_id:$request_id,run_id:$run_id}) "
            "RETURN v ORDER BY v.created_at DESC LIMIT 1",
            tenant_id=tenant_id, request_id=request_id, run_id=run_id,
        )).single()
        return {"judgment": j, "outputs": outputs, "drafts": drafts,
                "review": dict(review["v"]) if review else None}
    return await read_tx(tenant_id, op)


async def list_runs(tenant_id: str, request_id: str) -> list[dict]:
    async def op(tx):
        return await (await tx.run(
            "MATCH (r:Run {tenant_id:$tenant_id,request_id:$request_id}) "
            "RETURN r ORDER BY r.created_at DESC",
            tenant_id=tenant_id, request_id=request_id,
        )).data()
    return await read_tx(tenant_id, op)
