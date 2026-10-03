"""Execute one judgment run under a leased JobContext."""
from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from uuid import uuid4

from jevtriage.config import get_settings
from jevtriage.db.events import append_event_in_tx
from jevtriage.judgment.catalog import CATALOG_VERSION
from jevtriage.judgment.eligibility import evaluate_auto_assign
from jevtriage.judgment.jev_client import MODEL_VERSION, JevClient
from jevtriage.judgment.masking import MaskingSession, mask_for_external
from jevtriage.judgment.pipeline import SCHEMA_VERSION, run_judgment
from jevtriage.judgment.questions import QSET_VERSION
from jevtriage.judgment.store import load_input, save_judgment_in_tx
from jevtriage.learning.apply import apply_rules
from jevtriage.policy.pinning import pin_config_for_run_in_tx
from jevtriage.policy.service import DEFAULT_CONFIG, get_version


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
    client = client or JevClient(
        api_key=settings.jev_api_key.get_secret_value(), mode=settings.jev_mode,
        deadline=120,
    )
    rules_snapshot = policy.get("rules", [])
    async def requester_orgs(tx):
        row = await (await tx.run(
            "MATCH (q:Request {tenant_id:$tenant,id:$request}) RETURN q.org_ids AS org_ids",
            tenant=ctx.tenant_id, request=ctx.request_id,
        )).single()
        return row["org_ids"] if row and row["org_ids"] else []
    from jevtriage.db.tx import read_tx
    org_ids = await read_tx(ctx.tenant_id, requester_orgs)
    guidance = [r["context_text"] for r in rules_snapshot
                if r.get("effect") == "context" and r.get("context_text")
                and all(clause["requester_org"] in org_ids
                        for clause in r["scope"]["all"])]
    mask_session = MaskingSession()
    mask_policy = {**policy, "_masking_session": mask_session}

    class ExternalClient:
        def __init__(self, inner):
            self.inner = inner

        def ask(self, state, question_map):
            external = {**state}
            if guidance:
                external["operating_guidance"] = guidance
            for key in ("chat_text", "source_unit"):
                if key in external:
                    external[key] = mask_for_external(external[key], mask_policy)
            if "units" in external:
                external["units"] = [
                    {**unit, "text": mask_for_external(unit["text"], mask_policy)}
                    for unit in external["units"]
                ]
            if "operating_guidance" in external:
                external["operating_guidance"] = [
                    mask_for_external(item, mask_policy) for item in external["operating_guidance"]
                ]
            return self.inner.ask(external, question_map)

        def __getattr__(self, name):
            return getattr(self.inner, name)

    client = ExternalClient(client)
    mask_summary = {}
    try:
        async with ctx.step("Jev 판단", kind="ai", output_summary=mask_summary) as jev_step_id:
            # Chat text is already represented by persisted EvidenceSpan units. Passing it
            # separately would create ephemeral chat:n citations with no resolvable span.
            try:
                result = await asyncio.to_thread(run_judgment, units, "", policy, client,
                                                 chat_context_text=chat_text)
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
        ctx.record_usage(**result["usage"])
        async with ctx.step("근거 연결", kind="ai"):
            # Jev calls occur inside run_judgment; check their returned links here.
            valid_units = {unit["unit_id"] for unit in units}
            for citations in result["evidence"].values():
                for citation in citations:
                    if citation["unit_id"] not in valid_units or not 0 <= citation["probability"] <= 1:
                        raise ValueError("invalid evidence link")
        async with ctx.step("업무 분해", kind="ai"):
            # The catalog and Jev calls occur inside run_judgment.
            for task in result["draft_tasks"]:
                if not all(key in task for key in ("draft_task_id", "title", "method",
                                                  "lead_org", "deliverable", "predecessors")):
                    raise ValueError("invalid draft task")
        async with ctx.step("규칙 적용", kind="rule") as rule_step_id:
            answers = result["raw_model_output"]["answers"]
            result, applications = apply_rules(result, rules_snapshot, features={
                "signals": {key: value["noul"] for key, value in answers.items()
                            if value.get("type") == "noul"},
                "requester_orgs": org_ids,
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
        async with ctx.step("결과 저장", kind="code"):
            from jevtriage.review.service import auto_assign_after_judgment_in_tx

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
                    jev_step_id=jev_step_id, reasons=stored_reasons, eligible=eligible,
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
                        "SET a.outcome=$outcome,a.before=$before,a.after=$after,a.rule_version=$rule",
                        tenant=ctx.tenant_id, step=rule_step_id, run=ctx.run_id,
                        rule=application["rule_version"], outcome=application["outcome"],
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
