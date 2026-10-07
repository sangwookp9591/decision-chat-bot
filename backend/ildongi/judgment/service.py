"""Execute one judgment run under a leased JobContext."""
from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException

from ildongi.assist import service as assist
from ildongi.auth.policy import can, redact_source
from ildongi.auth.types import Principal
from ildongi.config import get_settings
from ildongi.db.events import append_event_in_tx
from ildongi.db.pinning import pin_config_for_run_in_tx
from ildongi.db.tx import read_tx
from ildongi.domain.drafts import draft_created_by, draft_source
from ildongi.domain.rules import apply_rules, context_rules_for
from ildongi.domain.serialize import json_value
from ildongi.ingest.service import request_meta as get_request_meta
from ildongi.judgment.ai_client import MODEL_VERSION, AiClient
from ildongi.judgment.catalog import CATALOG_VERSION
from ildongi.judgment.eligibility import evaluate_auto_assign
from ildongi.judgment.masking import MaskingClient, MaskingSession
from ildongi.judgment.pipeline import (
    SCHEMA_VERSION,
    assemble,
    build_evidence,
    build_tasks,
    classify,
)
from ildongi.judgment.progress_store import get_progress
from ildongi.judgment.questions import QSET_VERSION
from ildongi.judgment.store import get_judgment, load_input, save_judgment_in_tx
from ildongi.policy.service import DEFAULT_CONFIG, get_version
from ildongi.review.service import auto_assign_after_judgment_in_tx


async def load_input_for_shadow(tenant_id: str, request_id: str, revision_id: str):
    """Public read boundary for learning validation runs."""
    return await load_input(tenant_id, request_id, revision_id)


async def _fixed_policy(ctx) -> tuple[int, dict]:
    async def pin(tx):
        version = await pin_config_for_run_in_tx(tx, ctx.tenant_id, ctx.run_id)
        row = await (await tx.run(
            "MATCH (r:Run {tenant_id:$tenant,id:$run}) RETURN r.versions_json AS versions",
            tenant=ctx.tenant_id, run=ctx.run_id,
        )).single(strict=True)
        versions = json.loads(row["versions"] or "{}")
        for key, value in (("model", MODEL_VERSION), ("qset", QSET_VERSION),
                           ("catalog", CATALOG_VERSION), ("schema", SCHEMA_VERSION)):
            if versions.get(key) is None:
                versions[key] = value
        await (await tx.run(
            "MATCH (r:Run {tenant_id:$tenant,id:$run}) SET r.versions_json=$versions",
            tenant=ctx.tenant_id, run=ctx.run_id, versions=json.dumps(versions),
        )).consume()
        return version, versions

    version, ctx.versions = await ctx.commit(pin, affects_request=True)
    if version == 0:
        return 0, DEFAULT_CONFIG.copy()
    historical = await get_version(ctx.tenant_id, version)
    if historical is None:
        raise LookupError("fixed policy version is unavailable")
    return version, historical["config"]


async def execute_judgment(ctx, client=None) -> str:
    policy_version, policy = await _fixed_policy(ctx)
    ctx.policy_snapshot = policy
    async with ctx.step("입력 정리", kind="code"):
        units, chat_text, input_confirmed = await load_input(
            ctx.tenant_id, ctx.request_id, ctx.revision_id)
    settings = get_settings()
    client = client or AiClient(
        api_key=settings.ai_api_key.get_secret_value(), mode=settings.ai_mode,
        deadline=120,
    )
    rules_snapshot = policy.get("rules", [])
    async def requester_orgs(tx):
        row = await (await tx.run(
            "MATCH (q:Request {tenant_id:$tenant,id:$request}) RETURN q.org_ids AS org_ids",
            tenant=ctx.tenant_id, request=ctx.request_id,
        )).single()
        return row["org_ids"] if row and row["org_ids"] else []
    org_ids = await read_tx(ctx.tenant_id, requester_orgs)
    guidance = context_rules_for(rules_snapshot, {"requester_orgs": org_ids, "text_units": units})
    mask_session = MaskingSession()
    client = MaskingClient(client, policy, session=mask_session, guidance=guidance)
    mask_summary = {}
    try:
        async with ctx.step(f"{settings.ai_name} 판단", kind="ai", output_summary=mask_summary) as ai_step_id:
            # Chat text is already represented by persisted EvidenceSpan units. Passing it
            # separately would create ephemeral chat:n citations with no resolvable span.
            selected, state, model_output, classifications = await asyncio.to_thread(
                classify, units, "", policy, client, chat_context_text=chat_text)
            mask_summary.update({"mask_input_chars": mask_session.input_chars,
                                 "mask_output_chars": mask_session.output_chars,
                                 "mask_count": mask_session.count,
                                 "mask_calls": mask_session.calls})
        confidences = {key: model_output.answers[key]["confidence"] for key in classifications}
        risk_flags = {key: model_output.answers[key]["noul"] >= 0.5 for key in
                      ("clinical_safety", "pharmacovigilance", "regulatory")}

        async def save_partial(tx):
            row = await (await tx.run(
                "MATCH (q:Request {tenant_id:$tenant,id:$request}) "
                "MATCH (r:Run {tenant_id:$tenant,id:$run}) "
                "SET r.preliminary_json=$preliminary,r.preliminary_at=datetime() "
                "RETURN q.first_received_at AS received,r.preliminary_at AS saved",
                tenant=ctx.tenant_id, request=ctx.request_id, run=ctx.run_id,
                preliminary=json.dumps({"classifications": classifications,
                                        "confidences": confidences, "risk_flags": risk_flags},
                                       ensure_ascii=False),
            )).single(strict=True)
            await append_event_in_tx(tx, ctx.tenant_id, "judgment.partial",
                {"request_id": ctx.request_id, "run_id": ctx.run_id,
                 "classifications": classifications, "confidences": confidences,
                 "risk_flags": risk_flags, "preliminary": True},
                request_id=ctx.request_id, run_id=ctx.run_id)
            return max(0, row["saved"].to_native().timestamp() * 1000 -
                       row["received"].to_native().timestamp() * 1000)

        preliminary_ms = round(await ctx.commit(save_partial, affects_request=True))
        ctx.journal.append({"event_id": f"event_{uuid4().hex}",
                            "attempt_id": ctx.attempt_id, "request_id": ctx.request_id,
                            "run_id": ctx.run_id, "tenant_id": ctx.tenant_id,
                            "kind": "judgment_preliminary", "ts": datetime.now(UTC).isoformat(),
                            "time_to_preliminary_ms": preliminary_ms})
        ctx.record_usage(input_tokens=model_output.usage["input_tokens"],
                         output_tokens=model_output.usage["output_tokens"],
                         latency_ms=model_output.latency_ms,
                         attempts=model_output.attempts, mode=model_output.mode)

        async def evidence_phase():
            async with ctx.step("근거 연결", kind="ai"):
                evidence = await asyncio.to_thread(
                    build_evidence, selected, classifications, client, policy)
            valid_units = {unit["unit_id"] for unit in units}
            for citations in evidence.values():
                for citation in citations:
                    if citation["unit_id"] not in valid_units or not 0 <= citation["probability"] <= 1:
                        raise ValueError("invalid evidence link")
            async def save(tx):
                await (await tx.run(
                    "MATCH (r:Run {tenant_id:$tenant,id:$run}) "
                    "SET r.evidence_count=$count,r.evidence_json=$evidence,"
                    "r.evidence_ready_at=datetime()",
                    tenant=ctx.tenant_id, run=ctx.run_id,
                    count=sum(map(len, evidence.values())),
                    evidence=json.dumps({key: [
                        {field: citation[field] for field in ("unit_id", "probability", "author")}
                        for citation in citations] for key, citations in evidence.items()},
                        ensure_ascii=False),
                )).consume()
                await append_event_in_tx(tx, ctx.tenant_id, "judgment.evidence_ready",
                    {"request_id": ctx.request_id, "run_id": ctx.run_id,
                     "evidence_count": sum(map(len, evidence.values()))},
                    request_id=ctx.request_id, run_id=ctx.run_id)
            await ctx.commit(save, affects_request=True)
            return evidence

        async def tasks_phase():
            async with ctx.step("업무 분해", kind="ai"):
                tasks, decomposition = await asyncio.to_thread(
                    build_tasks, state, model_output, client, policy)
            for task in tasks:
                if not all(key in task for key in ("draft_task_id", "title", "method",
                                                  "lead_org", "deliverable", "predecessors")):
                    raise ValueError("invalid draft task")
            async def save(tx):
                await (await tx.run(
                    "MATCH (r:Run {tenant_id:$tenant,id:$run}) "
                    "SET r.task_count=$count,r.tasks_json=$tasks,r.tasks_ready_at=datetime()",
                    tenant=ctx.tenant_id, run=ctx.run_id, count=len(tasks),
                    tasks=json.dumps(tasks, ensure_ascii=False),
                )).consume()
                await append_event_in_tx(tx, ctx.tenant_id, "judgment.tasks_ready",
                    {"request_id": ctx.request_id, "run_id": ctx.run_id,
                     "task_count": len(tasks)},
                    request_id=ctx.request_id, run_id=ctx.run_id)
            await ctx.commit(save, affects_request=True)
            return tasks, decomposition

        evidence, (tasks, decomposition) = await asyncio.gather(
            evidence_phase(), tasks_phase())
        result = assemble(selected, model_output, classifications, evidence,
                          tasks, decomposition, policy)
        async with ctx.step("규칙 적용", kind="rule") as rule_step_id:
            answers = result["raw_model_output"]["answers"]
            result, applications = apply_rules(result, rules_snapshot, features={
                "signals": {key: value["noul"] for key, value in answers.items()
                            if value.get("type") == "noul"},
                "requester_orgs": org_ids,
                "text_units": units,
            })
            for application in applications:
                application["config_version"] = policy_version
        async with ctx.step("자동 배정 조건 검사", kind="rule"):
            answers = result["raw_model_output"]["answers"]
            classifications = result["classifications"]
            risks = {key: answers[key]["noul"] for key in
                     ("clinical_safety", "pharmacovigilance", "regulatory")}
            risk_clear_max = policy.get("risk_clear_max", 0.2)
            assessment = {**classifications,
                          "risk_signals": risks,
                          "risk_confirmed": all(value <= risk_clear_max for value in risks.values()),
                          "signals": {key: answers[key]["noul"] for key in
                                      ("ai_team_involvement", "it_team_involvement", "business_involvement")},
                          "choice_confidences": {key: answers[key]["confidence"] for key in classifications},
                          "draft_tasks": result["draft_tasks"]}
            allowed, reasons = evaluate_auto_assign(assessment, policy, {
                "input_confirmed": input_confirmed, "latest_run": True,
                "evidence_complete": bool(result["evidence"]) and
                    any(result["evidence"].values()), "already_assigned": False,
            })
            reasons.extend(result.get("rule_review_reasons", []))
            allowed = allowed and not result.get("rule_review_reasons")
            result["review_reasons"] = reasons
            result["eligibility"] = {"allowed": allowed, "reasons": reasons}
        assist_summary = {}
        async with ctx.step("글 다듬기", kind="external", output_summary=assist_summary):
            outcome = await assist.write_run_texts(
                units=units, result=result, llm_config=policy.get("llm") or {},
                policy=policy, mask_session=mask_session, settings=settings)
            if ctx.lost.is_set():
                raise asyncio.CancelledError()
            result = assist.apply_texts(result, outcome)
            assist_summary.update(calls=outcome.calls, llm=outcome.llm_version)
            ctx.journal.append({
                "event_id": f"event_{uuid4().hex}", "attempt_id": ctx.attempt_id,
                "request_id": ctx.request_id, "run_id": ctx.run_id, "tenant_id": ctx.tenant_id,
                "kind": "llm_assist", "ts": datetime.now(UTC).isoformat(),
                "validity": json.dumps({
                    "outcomes": {call["feature"]: call["outcome"] for call in outcome.calls},
                    "input_tokens": sum(call["input_tokens"] for call in outcome.calls),
                    "output_tokens": sum(call["output_tokens"] for call in outcome.calls),
                }, separators=(",", ":")),
            })
        async with ctx.step("결과 저장", kind="code"):
            async def save_and_assign(tx):
                assignment = await (await tx.run(
                    "MATCH (q:Request {tenant_id:$tenant,id:$request}) "
                    "OPTIONAL MATCH (a:Assignment {tenant_id:$tenant,request_id:$request}) "
                    "RETURN q.assignment_id AS assignment_id,count(a) AS assignment_count",
                    tenant=ctx.tenant_id, request=ctx.request_id,
                )).single(strict=True)
                compare_only = bool(assignment["assignment_id"] or assignment["assignment_count"])
                eligible = allowed and any(
                    citation.get("unit_id") in {unit["unit_id"] for unit in units}
                    for citations in result["evidence"].values() for citation in citations)
                stored_reasons = reasons if eligible or not allowed else [*reasons, "영속 근거 미완료"]
                judgment_id = await save_judgment_in_tx(
                    tx, ctx, result, policy_version=policy_version,
                    ai_step_id=ai_step_id, reasons=stored_reasons, eligible=eligible,
                    compare_only=compare_only)
                await (await tx.run(
                    "MATCH (j:Judgment {tenant_id:$tenant,id:$judgment}) "
                    "SET j.rule_effects=$effects",
                    tenant=ctx.tenant_id, judgment=judgment_id,
                    effects=json.dumps(applications, ensure_ascii=False),
                )).consume()
                for application in applications:
                    await (await tx.run(
                        "MATCH (s:RunStep {tenant_id:$tenant,id:$step,run_id:$run}) "
                        "MATCH (r:RuleVersion {tenant_id:$tenant,id:$rule}) "
                        "MERGE (s)-[a:APPLIED]->(r) "
                        "SET a.outcome=$outcome,a.before=$before,a.after=$after,a.rule_version=$rule,a.source=$source",
                        tenant=ctx.tenant_id, step=rule_step_id, run=ctx.run_id,
                        source=application.get("source"), rule=application["rule_version"], outcome=application["outcome"],
                        before=json.dumps(application["before"], ensure_ascii=False),
                        after=json.dumps(application["after"], ensure_ascii=False),
                    )).consume()
                if not compare_only:
                    await auto_assign_after_judgment_in_tx(tx, ctx, eligible=eligible)
                return judgment_id

            return await ctx.commit(save_and_assign, affects_request=True)
    except (Exception, asyncio.CancelledError) as exc:
        # System errors stay distinct from a valid judgment requiring human review.
        if ctx.lost.is_set():
            raise
        error_class = type(exc).__name__
        async def fail_request(tx):
            await (await tx.run(
                "MATCH (q:Request {tenant_id:$tenant_id,id:$request_id,active_run_id:$run_id}) "
                "SET q.status='실패'",
                tenant_id=ctx.tenant_id, request_id=ctx.request_id, run_id=ctx.run_id,
            )).consume()
            await append_event_in_tx(tx, ctx.tenant_id, "judgment_failed",
                {"error_class": error_class}, request_id=ctx.request_id,
                run_id=ctx.run_id)
        await ctx.commit(fail_request, affects_request=True)
        raise
    finally:
        mask_summary.update({"mask_input_chars": mask_session.input_chars,
                             "mask_output_chars": mask_session.output_chars,
                             "mask_count": mask_session.count,
                             "mask_calls": mask_session.calls})
        ctx.journal.append({
            "event_id": f"event_{uuid4().hex}", "attempt_id": ctx.attempt_id,
            "request_id": ctx.request_id, "run_id": ctx.run_id,
            "kind": "external_masking", "ts": datetime.now(UTC).isoformat(),
            "status_code": "recorded", "tenant_id": ctx.tenant_id,
            "validity": json.dumps(mask_summary, separators=(",", ":")),
        })


def _date(value):
    return json_value(value)


async def visible_request(principal: Principal, request_id: str) -> dict:
    meta = await get_request_meta(principal.tenant_id, request_id)
    if meta is None or not can(principal, "view_request", meta):
        raise HTTPException(status_code=404, detail="Request not found")
    return meta


async def visible_judgment(principal: Principal, request_id: str, run_id: str | None = None):
    meta = await visible_request(principal, request_id)
    chosen_run = run_id or meta.get("active_run_id")
    if not chosen_run:
        raise HTTPException(status_code=404, detail="Judgment not found")
    data = await get_judgment(principal.tenant_id, request_id, chosen_run)
    if data is None:
        raise HTTPException(status_code=404, detail="Judgment not found")
    j = data["judgment"]
    outputs = []
    for row in data["outputs"]:
        o = dict(row["o"])
        item = {"id": o["id"], "question_id": o["question_id"], "type": o["type"],
                "value": o["value"], "model": o["model"]}
        if o.get("confidence") is not None:
            item["confidence"] = o["confidence"]
        if o.get("probabilities") is not None:
            item["probabilities"] = json.loads(o["probabilities"])
        if o.get("noul") is not None:
            item["noul"] = o["noul"]
        if o.get("legend") is not None:
            item["legend"] = json.loads(o["legend"])
        item["evidence"] = []
        for citation in row["citations"]:
            if citation is None:
                continue
            evidence = {"id": citation["id"], "source": citation["source"] or
                        ("attachment" if citation["attachment_id"] else "chat"),
                        "attachment_id": citation["attachment_id"],
                        "location": json.loads(citation["location_json"]),
                        "char_start": citation["char_start"], "char_end": citation["char_end"],
                        "probability": citation["prob"]}
            if principal.can_read_source:
                evidence["source_text"] = citation["source_text"]
            item["evidence"].append(evidence)
        outputs.append(item)
    draft_versions = []
    for row in data["drafts"]:
        draft = dict(row["d"])
        nodes = [dict(t) for t in row["tasks"] if t is not None]
        draft_versions.append({
            "draft_version": draft["draft_version"], "source": draft_source(draft["draft_version"]),
            "created_by": draft_created_by(draft, nodes), "created_at": _date(draft.get("created_at")),
            "tasks": [{key: task.get(key) for key in ("id", "draft_task_id", "draft_version",
                       "title", "method", "lead_org", "deliverable", "status", "reason", "author",
                       "description", "description_author")}
                      | {"collab_orgs": json.loads(task.get("collab_orgs") or "[]"),
                         "predecessors": json.loads(task.get("predecessors") or "[]")}
                      for task in nodes]})
    review = data["review"]
    # 현재 초안 = 승인된 요청은 승인된 버전, 그 외에는 최신 버전. draft_tasks는 현재 버전만 담는다.
    latest_version = max((v["draft_version"] for v in draft_versions), default=None)
    current_version = (review["draft_version"] if review and review["status"] == "approved"
                       and any(v["draft_version"] == review["draft_version"] for v in draft_versions)
                       else latest_version)
    tasks = next((v["tasks"] for v in draft_versions if v["draft_version"] == current_version), [])
    return redact_source(principal, {"id": j["id"], "request_id": request_id, "revision_id": j["revision_id"],
            "run_id": chosen_run, "classifications": {key: j.get(key) for key in
                ("ai_need", "feasibility", "urgency", "lead_org")},
            "risk_confirmed": j["risk_confirmed"], "risks": json.loads(j["risks"]),
            "summary": json.loads(j["summary"]), "author": j["author"],
            "questions": json.loads(j["questions_json"]) if j.get("questions_json") else None,
            "llm": json.loads(j["llm_json"]) if j.get("llm_json") else None,
            "versions": json.loads(j["versions"]), "mode": j["mode"],
            "rule_effects": json.loads(j.get("rule_effects") or "[]"),
            "created_at": _date(j["created_at"]), "outputs": outputs, "draft_tasks": tasks,
            "current_draft_version": current_version, "draft_versions": draft_versions,
            "review_reasons": json.loads(review["reasons"]) if review else [],
            "review": {"id": review["id"], "status": review["status"],
                       "required_reviewer_org": review["required_reviewer_org"]} if review else None})


async def visible_progress(principal: Principal, request_id: str, run_id: str | None = None):
    await visible_request(principal, request_id)
    return await get_progress(principal.tenant_id, request_id, run_id)
