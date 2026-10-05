"""Review decisions and assignments against a real Neo4j instance."""
from __future__ import annotations

import asyncio
import json
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio

from jevtriage.auth.core import Principal, get_principal
from jevtriage.db.schema import apply_schema
from jevtriage.db.tx import read_tx, write_tx
from jevtriage.ingest.store import get_request_meta
from jevtriage.main import create_app
from jevtriage.review.service import ReviewError, decide
from jevtriage.tasks.service import TaskError, transition

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest_asyncio.fixture
async def tenant():
    tenant_id = f"review_{uuid4().hex}"
    await apply_schema()
    async def setup(tx):
        for name in ("ai", "it", "business"):
            await (await tx.run(
                "CREATE (:Org {id:$id,tenant_id:$tenant,name:$name})",
                id=f"{tenant_id}-{name}", tenant=tenant_id, name=name,
            )).consume()
    await write_tx(tenant_id, setup)
    yield tenant_id
    async def cleanup(tx):
        await (await tx.run("MATCH (n {tenant_id:$tenant}) DETACH DELETE n",
                            tenant=tenant_id)).consume()
    await write_tx(tenant_id, cleanup)


async def sample(tenant: str):
    request_id, revision_id, run_id, review_id = (
        f"req_{uuid4().hex}", f"rev_{uuid4().hex}",
        f"run_{uuid4().hex}", f"rvw_{uuid4().hex}")
    draft_id = f"drf_{uuid4().hex}"
    async def seed(tx):
        await (await tx.run(
            "CREATE (q:Request {id:$request,tenant_id:$tenant,created_by:'requester',"
            "status:'검토 대기',latest_revision_id:$revision,active_run_id:$run,"
            "org_ids:[],created_at:datetime()}) "
            "CREATE (i:InputRevision {id:$revision,tenant_id:$tenant,request_id:$request,"
            "number:1,text:'업무 판단 요청',created_at:datetime()}) "
            "CREATE (r:Run {id:$run,tenant_id:$tenant,request_id:$request,"
            "input_revision_id:$revision,kind:'normal',status:'judgment_saved',"
            "created_at:datetime()}) CREATE (q)-[:HAS_REVISION]->(i)",
            tenant=tenant, request=request_id, revision=revision_id, run=run_id,
        )).consume()
        judgment_id = f"jdg_{uuid4().hex}"
        await (await tx.run(
            "MATCH (r:Run {tenant_id:$tenant,id:$run}) "
            "CREATE (j:Judgment {id:$id,tenant_id:$tenant,request_id:$request,"
            "revision_id:$revision,run_id:$run,ai_need:'정보 부족',"
            "feasibility:'정보 부족',urgency:'판단 보류',lead_org:'미정',"
            "risks:'{}',summary:'{}',versions:$versions,"
            "mode:'mock',author:'test-fixture',risk_confirmed:false,created_at:datetime()}) CREATE (r)-[:PRODUCED]->(j)",
            tenant=tenant, run=run_id, request=request_id, revision=revision_id,
            id=judgment_id, versions=json.dumps({"config_version":0}),
        )).consume()
        for question, value in (("ai_need", "정보 부족"), ("feasibility", "정보 부족"),
                                ("urgency", "판단 보류"), ("lead_org", "미정")):
            await (await tx.run(
                "MATCH (j:Judgment {tenant_id:$tenant,id:$judgment}) "
                "CREATE (o:ModelOutput {id:$id,tenant_id:$tenant,run_id:$run,"
                "question_id:$question,type:'choice',value:$value,confidence:.4,"
                "model:'test-fixture'}) CREATE (o)-[:OF_JUDGMENT]->(j)",
                tenant=tenant, judgment=judgment_id, id=f"mout_{uuid4().hex}",
                run=run_id, question=question, value=value,
            )).consume()
        for question in ("clinical_safety", "pharmacovigilance", "regulatory",
                         "ai_team_involvement", "it_team_involvement", "business_involvement"):
            await (await tx.run(
                "MATCH (j:Judgment {tenant_id:$tenant,id:$judgment}) "
                "CREATE (o:ModelOutput {id:$id,tenant_id:$tenant,run_id:$run,"
                "question_id:$question,type:'noul',value:.5,noul:.5,model:'test-fixture'}) "
                "CREATE (o)-[:OF_JUDGMENT]->(j)",
                tenant=tenant, judgment=judgment_id, id=f"mout_{uuid4().hex}",
                run=run_id, question=question,
            )).consume()
        await (await tx.run(
            "MATCH (r:Run {tenant_id:$tenant,id:$run}) "
            "CREATE (d:Draft {id:$draft,tenant_id:$tenant,request_id:$request,"
            "revision_id:$revision,run_id:$run,draft_version:1,created_at:datetime()}) "
            "CREATE (t:DraftTask {id:$task,tenant_id:$tenant,request_id:$request,"
            "run_id:$run,draft_task_id:'draft-1',draft_version:1,title:'검토 업무',"
            "method:'일반 기술',lead_org:'IT팀',collab_orgs:'[]',"
            "deliverable:'검토 결과',predecessors:'[]',status:'draft',author:'test-fixture'}) "
            "CREATE (r)-[:PRODUCED]->(d) CREATE (t)-[:IN_DRAFT]->(d)",
            tenant=tenant, run=run_id, request=request_id, revision=revision_id,
            draft=draft_id, task=f"{draft_id}_draft-1",
        )).consume()
        await (await tx.run(
            "CREATE (:Review {id:$id,tenant_id:$tenant,status:'pending',"
            "request_id:$request,revision_id:$revision,run_id:$run,"
            "draft_version:1,review_version:1,reasons:'[\"정보 부족\"]',"
            "required_reviewer_org:'IT팀',created_at:datetime()})",
            tenant=tenant, id=review_id, request=request_id,
            revision=revision_id, run=run_id,
        )).consume()
    await write_tx(tenant, seed)
    principal = Principal(tenant, "reviewer", (f"{tenant}-it",), frozenset({"reviewer"}), True)
    command = {"action":"approve", "request_id":request_id, "input_revision":revision_id,
               "run_id":run_id,"draft_version":1,"review_version":1}
    return principal, review_id, command


async def counts(tenant: str, request_id: str):
    async def op(tx):
        row = await (await tx.run(
            "MATCH (q:Request {tenant_id:$tenant,id:$request}) "
            "OPTIONAL MATCH (a:Assignment {tenant_id:$tenant,request_id:$request}) "
            "OPTIONAL MATCH (t:Task {tenant_id:$tenant,request_id:$request}) "
            "RETURN count(DISTINCT a) AS assignments,count(DISTINCT t) AS tasks",
            tenant=tenant, request=request_id,
        )).single(strict=True)
        return dict(row)
    return await read_tx(tenant, op)


async def assigned_task(tenant: str, task_id: str):
    async def op(tx):
        row = await (await tx.run(
            "MATCH (t:Task {tenant_id:$tenant,id:$id}) "
            "RETURN t.status AS status,t.block_reasons AS reasons",
            tenant=tenant, id=task_id,
        )).single(strict=True)
        return dict(row)
    return await read_tx(tenant, op)


@pytest.mark.parametrize("original,corrected,blocked", [
    ("정보 부족", "가능", False),
    ("가능", "조건부 가능", True),
    ("조건부 가능", None, True),
])
async def test_assignment_uses_final_approved_feasibility(tenant, original, corrected, blocked):
    principal, review_id, command = await sample(tenant)
    async def update(tx):
        await (await tx.run(
            "MATCH (j:Judgment {tenant_id:$tenant,run_id:$run}) "
            "SET j.feasibility=$value",
            tenant=tenant, run=command["run_id"], value=original,
        )).consume()
        await (await tx.run(
            "MATCH (t:DraftTask {tenant_id:$tenant,run_id:$run,draft_task_id:'draft-1'}) "
            "SET t.title='본업무 개발'",
            tenant=tenant, run=command["run_id"],
        )).consume()
    await write_tx(tenant, update)
    if corrected:
        command.update(action="approve_with_changes", reason="가능성 확인",
                       changes={"classifications": {"feasibility": corrected}})
    result = await decide(principal, review_id, command, str(uuid4()))
    task_id = result["assignment"]["task_ids"]["draft-1"]
    task = await assigned_task(tenant, task_id)
    assert ("feasibility_unresolved" in task["reasons"]) is blocked
    if blocked:
        assert task["status"] == "막힘"
    else:
        assert task["status"] == "대기"
        worker = Principal(tenant, "worker", (f"{tenant}-it",), frozenset({"team_member"}))
        assert (await transition(worker, task_id, "진행", "대기"))["status"] == "진행"


async def test_predecessor_still_blocks_approved_possible_task(tenant):
    principal, review_id, command = await sample(tenant)
    async def update(tx):
        await (await tx.run(
            "MATCH (j:Judgment {tenant_id:$tenant,run_id:$run}) SET j.feasibility='가능'",
            tenant=tenant, run=command["run_id"],
        )).consume()
        await (await tx.run(
            "MATCH (t:DraftTask {tenant_id:$tenant,run_id:$run,draft_task_id:'draft-1'}) "
            "SET t.predecessors='[\"draft-2\"]' "
            "WITH t MATCH (d:Draft {tenant_id:$tenant,run_id:$run,draft_version:1}) "
            "CREATE (:DraftTask {id:$id,tenant_id:$tenant,request_id:$request,run_id:$run,"
            "draft_task_id:'draft-2',draft_version:1,title:'자료 확인',method:'사람',"
            "lead_org:'IT팀',collab_orgs:'[]',deliverable:'확인 결과',predecessors:'[]',"
            "status:'draft'})-[:IN_DRAFT]->(d)",
            tenant=tenant, run=command["run_id"], request=command["request_id"],
            id=f"dt_{uuid4().hex}",
        )).consume()
    await write_tx(tenant, update)
    result = await decide(principal, review_id, command, str(uuid4()))
    task_id = result["assignment"]["task_ids"]["draft-1"]
    task = await assigned_task(tenant, task_id)
    assert task["status"] == "막힘"
    assert task["reasons"] == ["predecessor_incomplete"]
    worker = Principal(tenant, "worker", (f"{tenant}-it",), frozenset({"team_member"}))
    with pytest.raises(TaskError) as error:
        await transition(worker, task_id, "진행", "막힘")
    assert error.value.status_code == 409


@pytest.mark.parametrize("action,status,request_status", [
    ("approve", "approved", "배정 완료"),
    ("approve_with_changes", "approved", "배정 완료"),
    ("reject", "rejected", "반려"),
    ("request_info", "info_requested", "보완 필요"),
])
async def test_four_decisions_history_audit_and_assignment(tenant, action, status, request_status):
    principal, review_id, command = await sample(tenant)
    command["action"] = action
    if action == "approve_with_changes":
        command["changes"] = {"classifications":{"feasibility":"가능"}}
        command["reason"] = "검토자가 가능성을 확인함"
    elif action in {"reject", "request_info"}:
        command["reason"] = "필요한 자료를 확인해야 합니다"
    result = await decide(principal, review_id, command, str(uuid4()))
    assert result["status"] == status
    assert (await get_request_meta(tenant, command["request_id"]))["status"] == request_status
    db_counts = await counts(tenant, command["request_id"])
    assert db_counts["assignments"] == (1 if action.startswith("approve") else 0)
    assert db_counts["tasks"] >= (1 if action.startswith("approve") else 0)
    async def evidence(tx):
        return (await (await tx.run(
            "MATCH (v:Review {tenant_id:$tenant,id:$id})-[:HAS_DECISION]->(h:ReviewDecision) "
            "RETURN v.review_version AS version,h.action AS action,"
            "count(h) AS decisions", tenant=tenant, id=review_id,
        )).single(strict=True)), (await (await tx.run(
            "MATCH (a:Audit {tenant_id:$tenant,target_id:$id}) RETURN count(a) AS n",
            tenant=tenant, id=review_id,
        )).single(strict=True))["n"]
    history, audit_count = await read_tx(tenant, evidence)
    assert history["version"] == 2 and history["action"] == action
    assert audit_count == 1


async def test_correction_preserves_original_and_relationships(tenant):
    principal, review_id, command = await sample(tenant)
    command.update(action="approve_with_changes", reason="현업 확인",
                   changes={"classifications":{"feasibility":"가능"},
                            "draft_tasks":[{"draft_task_id":"draft-1", "lead_org":"현업"}]})
    result = await decide(principal, review_id, command, "correction-key")
    assert result["draft_version"] == 2
    assert len(result["correction_ids"]) >= 2
    async def check(tx):
        return await (await tx.run(
            "MATCH (v:Review {tenant_id:$tenant,id:$review})-[:HAS_DECISION]->"
            "(h:ReviewDecision)-[:RECORDED]->(c:Correction) "
            "OPTIONAL MATCH (c)-[:CORRECTS]->(o:ModelOutput) "
            "RETURN c.field AS field,c.ai_value AS ai,c.corrected_value AS corrected,"
            "c.reason AS reason,c.evidence_span_ids AS spans,c.corrected_by AS actor,"
            "c.corrected_at AS at,c.request_id AS request_id,c.revision_id AS revision_id,"
            "c.run_id AS run_id,c.config_version AS config_version,o.id AS output",
            tenant=tenant, review=review_id,
        )).data()
    rows = await read_tx(tenant, check)
    feasibility = next(r for r in rows if r["field"] == "feasibility")
    assert json.loads(feasibility["corrected"]) == "가능"
    assert feasibility["output"] and feasibility["actor"] == "reviewer"
    assert feasibility["at"] and feasibility["run_id"] == command["run_id"]
    assert any(r["field"].endswith("lead_org") for r in rows)
    async def original(tx):
        return (await (await tx.run(
            "MATCH (j:Judgment {tenant_id:$tenant,run_id:$run}) RETURN j.feasibility AS feasibility",
            tenant=tenant, run=command["run_id"],
        )).single(strict=True))["feasibility"]
    assert await read_tx(tenant, original) != "가능"


async def test_stale_version_and_revision_rejected_with_latest(tenant):
    principal, review_id, command = await sample(tenant)
    old = {**command, "draft_version":0}
    with pytest.raises(ReviewError) as error:
        await decide(principal, review_id, old, str(uuid4()))
    assert error.value.status_code == 409 and error.value.latest["draft_version"] == 1
    old_revision = {**command, "input_revision":"rev_old"}
    with pytest.raises(ReviewError) as error:
        await decide(principal, review_id, old_revision, str(uuid4()))
    assert error.value.status_code == 409
    assert (await counts(tenant, command["request_id"]))["assignments"] == 0


async def test_concurrent_approvals_one_assignment_and_idempotency(tenant):
    principal, review_id, command = await sample(tenant)
    async def attempt(index):
        try:
            return await decide(principal, review_id, command, f"concurrent-{index}")
        except ReviewError as exc:
            return exc.status_code
    results = await asyncio.gather(*(attempt(i) for i in range(20)))
    assert sum(isinstance(r, dict) for r in results) == 1
    assert all(r == 409 for r in results if isinstance(r, int))
    first = next(r for r in results if isinstance(r, dict))
    repeated = await decide(principal, review_id, command,
                            f"concurrent-{results.index(first)}")
    assert repeated == first
    with pytest.raises(ReviewError) as error:
        await decide(principal, review_id, {**command, "action":"reject", "reason":"수정"},
                     f"concurrent-{results.index(first)}")
    assert error.value.status_code == 409
    assert (await counts(tenant, command["request_id"]))["assignments"] == 1


async def test_permission_tenant_and_cycle(tenant):
    principal, review_id, command = await sample(tenant)
    outsider = Principal(tenant, "outsider", (f"{tenant}-business",), frozenset({"reviewer"}))
    with pytest.raises(ReviewError) as error:
        await decide(outsider, review_id, command, str(uuid4()))
    assert error.value.status_code == 403
    other = Principal("unrelated-tenant", "reviewer", ("unrelated-tenant-it",), frozenset({"reviewer"}))
    with pytest.raises((ReviewError, LookupError)) as error:
        await decide(other, review_id, command, str(uuid4()))
    assert getattr(error.value, "status_code", 404) == 404
    async def cycle(tx):
        await (await tx.run(
            "MATCH (t:DraftTask {tenant_id:$tenant,run_id:$run}) "
            "SET t.predecessors=$predecessors",
            tenant=tenant, run=command["run_id"], predecessors=json.dumps(["draft-1"]),
        )).consume()
    await write_tx(tenant, cycle)
    with pytest.raises(ReviewError) as error:
        await decide(principal, review_id, command, str(uuid4()))
    assert error.value.status_code == 422
    assert (await counts(tenant, command["request_id"]))["assignments"] == 0


async def test_api_scope_and_detail(tenant):
    principal, review_id, _command = await sample(tenant)
    app = create_app()
    app.dependency_overrides[get_principal] = lambda: principal
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        listed = await client.get("/api/reviews?status=pending")
        assert listed.status_code == 200
        assert any(v["id"] == review_id for v in listed.json()["reviews"])
        detail = await client.get(f"/api/reviews/{review_id}")
        assert detail.status_code == 200
        assert detail.json()["review_version"] == 1
        assert detail.json()["judgment"] and detail.json()["outputs"]
        app.dependency_overrides[get_principal] = lambda: Principal(
            tenant, "outsider", (f"{tenant}-business",), frozenset({"reviewer"}))
        assert (await client.get(f"/api/reviews/{review_id}")).status_code == 404


async def test_decision_api_requires_csrf_and_reviewer_session(tenant):
    from jevtriage.auth.core import create_session, session_principal
    _principal, review_id, command = await sample(tenant)
    async def user(tx):
        await (await tx.run(
            "MATCH (o:Org {tenant_id:$tenant,id:$org}) "
            "CREATE (u:User {id:'reviewer',tenant_id:$tenant,disabled:false,"
            "can_read_source:false}) CREATE (u)-[:MEMBER_OF {role:'reviewer'}]->(o)",
            tenant=tenant, org=f"{tenant}-it",
        )).consume()
    await write_tx(tenant, user)
    token = await create_session(tenant, "reviewer")
    csrf = (await session_principal(token))[1]
    app = create_app()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                base_url="http://test") as client:
        client.cookies.set("jev_session", token)
        client.cookies.set("jev_csrf", csrf)
        route = f"/api/reviews/{review_id}/decision"
        denied = await client.post(route, headers={"Idempotency-Key":"csrf-check"}, json=command)
        assert denied.status_code == 403
        approved = await client.post(route, headers={"Idempotency-Key":"csrf-check",
                                                     "X-CSRF-Token":csrf}, json=command)
        assert approved.status_code == 200
        assert approved.json()["assignment"]["assignment_id"]
        detail = await client.get(f"/api/reviews/{review_id}")
        assert detail.status_code == 200
        assert detail.json()["history"][0]["action"] == "approve"


async def test_auto_path_rechecks_mandatory_review_and_infeasibility(tenant):
    from jevtriage.review.service import assign_in_tx
    _principal, _review_id, command = await sample(tenant)
    async def attempt(tx):
        return await assign_in_tx(tx, tenant, command["request_id"], command["run_id"],
                                  command["input_revision"], 1, pathway="auto")
    with pytest.raises(ReviewError) as error:
        await write_tx(tenant, attempt)
    assert error.value.status_code == 409
    async def high_confidence_infeasible(tx):
        await (await tx.run(
            "MATCH (q:Request {tenant_id:$tenant,id:$request}) "
            "SET q.status='auto_assign_eligible'",
            tenant=tenant, request=command["request_id"],
        )).consume()
        await (await tx.run(
            "MATCH (j:Judgment {tenant_id:$tenant,run_id:$run}) "
            "SET j.feasibility='현재 불가',j.risk_confirmed=true",
            tenant=tenant, run=command["run_id"],
        )).consume()
        await (await tx.run(
            "MATCH (o:ModelOutput {tenant_id:$tenant,run_id:$run,question_id:'feasibility'}) "
            "SET o.confidence=0.99",
            tenant=tenant, run=command["run_id"],
        )).consume()
    await write_tx(tenant, high_confidence_infeasible)
    with pytest.raises(ReviewError) as error:
        await write_tx(tenant, attempt)
    assert error.value.status_code == 409
    assert (await counts(tenant, command["request_id"]))["assignments"] == 0


async def test_auto_path_assigns_only_after_full_recheck(tenant):
    from jevtriage.policy.service import DEFAULT_CONFIG
    from jevtriage.review.service import assign_in_tx
    _principal, _review_id, command = await sample(tenant)
    async def eligible_nodes(tx):
        config = {**DEFAULT_CONFIG, "auto_assign":True}
        await (await tx.run(
            "CREATE (:ConfigVersion {id:$id,tenant_id:$tenant,version:23,"
            "config_json:$config,status:'active',created_at:datetime()})",
            id=f"cfg_{uuid4().hex}", tenant=tenant, config=json.dumps(config),
        )).consume()
        await (await tx.run(
            "MATCH (q:Request {tenant_id:$tenant,id:$request}) "
            "SET q.status='auto_assign_eligible'",
            tenant=tenant, request=command["request_id"],
        )).consume()
        await (await tx.run(
            "MATCH (j:Judgment {tenant_id:$tenant,run_id:$run}) "
            "SET j.ai_need='불필요',j.feasibility='가능',j.urgency='일반',"
            "j.lead_org='IT팀',j.risk_confirmed=true,j.risks=$risks,j.versions=$versions",
            tenant=tenant, run=command["run_id"],
            risks=json.dumps({"clinical_safety":.01,"pharmacovigilance":.01,"regulatory":.01}),
            versions=json.dumps({"config_version":23}),
        )).consume()
        for question in ("ai_need", "feasibility", "urgency", "lead_org"):
            await (await tx.run(
                "MATCH (o:ModelOutput {tenant_id:$tenant,run_id:$run,question_id:$question}) "
                "SET o.confidence=.99",
                tenant=tenant, run=command["run_id"], question=question,
            )).consume()
        for question in ("ai_team_involvement", "it_team_involvement", "business_involvement"):
            await (await tx.run(
                "MATCH (o:ModelOutput {tenant_id:$tenant,run_id:$run,question_id:$question}) "
                "SET o.noul=.9",
                tenant=tenant, run=command["run_id"], question=question,
            )).consume()
        await (await tx.run(
            "CREATE (e:EvidenceSpan {id:$id,tenant_id:$tenant,request_id:$request,"
            "revision_id:$revision,location_json:'{}',source_text:'근거'}) "
            "WITH e MATCH (o:ModelOutput {tenant_id:$tenant,run_id:$run,question_id:'feasibility'}) "
            "CREATE (o)-[:CITES {prob:.99}]->(e)",
            id=f"esp_{uuid4().hex}", tenant=tenant, request=command["request_id"],
            revision=command["input_revision"], run=command["run_id"],
        )).consume()
    await write_tx(tenant, eligible_nodes)
    async def assign(tx):
        return await assign_in_tx(tx, tenant, command["request_id"], command["run_id"],
                                  command["input_revision"], 1, pathway="auto")
    result = await write_tx(tenant, assign)
    assert result["assignment_id"]
    assert (await counts(tenant, command["request_id"]))["assignments"] == 1
    async def relations(tx):
        return (await (await tx.run(
            "MATCH (q:Request {tenant_id:$tenant,id:$request})-[:HAS_TASK]->"
            "(t:Task)-[:ASSIGNED_TO {role:'lead'}]->(o:Org) "
            "RETURN count(t) AS tasks,collect(o.id) AS orgs",
            tenant=tenant, request=command["request_id"],
        )).single(strict=True))
    row = await read_tx(tenant, relations)
    assert row["tasks"] >= 1 and set(row["orgs"]) == {f"{tenant}-it"}


async def test_reanalysis_keeps_assigned_tasks_unchanged(tenant):
    principal, review_id, command = await sample(tenant)
    await decide(principal, review_id, command, "first-approval")
    before = await counts(tenant, command["request_id"])
    async def task_ids(tx):
        return [r["id"] for r in await (await tx.run(
            "MATCH (t:Task {tenant_id:$tenant,request_id:$request}) RETURN t.id AS id ORDER BY id",
            tenant=tenant, request=command["request_id"],
        )).data()]
    original_ids = await read_tx(tenant, task_ids)
    next_revision, next_run = f"rev_{uuid4().hex}", f"run_{uuid4().hex}"
    async def reanalyze(tx):
        await (await tx.run(
            "MATCH (q:Request {tenant_id:$tenant,id:$request}) "
            "CREATE (i:InputRevision {id:$revision,tenant_id:$tenant,request_id:$request,"
            "number:2,text:'다시 판단해 주세요.',created_at:datetime()}) "
            "CREATE (r:Run {id:$run,tenant_id:$tenant,request_id:$request,"
            "input_revision_id:$revision,kind:'normal',status:'pending',created_at:datetime()}) "
            "CREATE (q)-[:HAS_REVISION]->(i) "
            "SET q.latest_revision_id=$revision,q.active_run_id=$run,q.status='judgment_pending'",
            tenant=tenant, request=command["request_id"],
            revision=next_revision, run=next_run,
        )).consume()
    await write_tx(tenant, reanalyze)
    meta = await get_request_meta(tenant, command["request_id"])
    assert meta["active_run_id"] != command["run_id"]
    assert await counts(tenant, command["request_id"]) == before
    assert await read_tx(tenant, task_ids) == original_ids
    with pytest.raises(ReviewError) as error:
        await decide(principal, review_id, command, "old-approval")
    assert error.value.status_code == 409
    assert error.value.latest["run_id"] == meta["active_run_id"]


@pytest.mark.parametrize("changes,reviewer_changed", [
    ({"classifications": {"feasibility": "가능"}}, False),
    ({"draft_tasks": [{"draft_task_id": "draft-1", "lead_org": "현업"}]}, True),
])
async def test_judgment_api_shows_only_current_draft_version(tenant, changes, reviewer_changed):
    principal, review_id, command = await sample(tenant)
    app = create_app()
    app.dependency_overrides[get_principal] = lambda: principal
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        command.update(action="approve_with_changes", reason="수정 승인", changes=changes)
        await decide(principal, review_id, command, str(uuid4()))
        app.dependency_overrides[get_principal] = lambda: Principal(
            tenant, "requester", (), frozenset({"requester"}), True)
        response = await client.get(f"/api/requests/{command['request_id']}/judgment")
        assert response.status_code == 200, response.text
        body = response.json()
        app.dependency_overrides[get_principal] = lambda: principal
        review = (await client.get(f"/api/reviews/{review_id}")).json()
    # 같은 업무가 한 번만, 승인된 버전(v2)으로 나온다.
    assert [(t["draft_task_id"], t["draft_version"]) for t in body["draft_tasks"]] == [("draft-1", 2)]
    assert body["current_draft_version"] == 2
    versions = body["draft_versions"]
    assert [v["draft_version"] for v in versions] == [1, 2]
    assert [v["source"] for v in versions] == ["ai", "reviewer"]
    assert versions[1]["created_by"] == "reviewer"
    assert all(len(v["tasks"]) == 1 and v["created_at"] for v in versions)
    assert versions[0]["tasks"][0]["lead_org"] == "IT팀"
    assert versions[1]["tasks"][0]["lead_org"] == ("현업" if reviewer_changed else "IT팀")
    # Review 상세도 원안(v1)과 수정 초안을 구분한다.
    assert review["original_draft"]["draft_version"] == 1
    assert review["original_draft"]["source"] == "ai"
    assert review["current_draft"]["draft_version"] == 2
    assert review["current_draft"]["source"] == "reviewer"
    assert [d["source"] for d in review["drafts"]] == ["ai", "reviewer"]


async def make_undetermined(tenant, run_id):
    async def op(tx):
        await (await tx.run(
            "MATCH (t:DraftTask {tenant_id:$tenant,run_id:$run}) "
            "SET t.lead_org='미정',t.method='미정',t.deliverable='',t.title=''",
            tenant=tenant, run=run_id,
        )).consume()
    await write_tx(tenant, op)


async def test_repair_undetermined_draft_before_validation(tenant):
    principal, review_id, command = await sample(tenant)
    await make_undetermined(tenant, command['run_id'])
    command.update(action='approve_with_changes', reason='미정 필드를 검토하여 보완', changes={
        'classifications': {'feasibility': '가능'},
        'draft_tasks': [{'draft_task_id': 'draft-1', 'lead_org': 'IT팀',
                         'method': '일반 기술', 'title': '검토 업무', 'deliverable': '검토 결과'}],
    })
    result = await decide(principal, review_id, command, 'repair-undetermined')
    assert result['status'] == 'approved'
    assert result['draft_version'] == 2
    assert len(result['correction_ids']) == 5
    assert await counts(tenant, command['request_id']) == {'assignments': 1, 'tasks': 1}


async def test_unresolved_draft_returns_field_errors_without_writes(tenant):
    principal, review_id, command = await sample(tenant)
    await make_undetermined(tenant, command['run_id'])
    app = create_app()
    app.dependency_overrides[get_principal] = lambda: principal
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
        response = await client.post(f'/api/reviews/{review_id}/decision', json=command,
                                     headers={'Idempotency-Key': 'unresolved-draft'})
    assert response.status_code == 422
    errors = response.json()['detail']['details']['field_errors']
    assert {e['field'] for e in errors} == {'lead_org', 'method', 'title', 'deliverable'}
    assert all(e['draft_task_id'] == 'draft-1' and e['message'] for e in errors)
    assert await counts(tenant, command['request_id']) == {'assignments': 0, 'tasks': 0}
