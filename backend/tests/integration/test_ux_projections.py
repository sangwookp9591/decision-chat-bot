"""UX-1 regressions: flow order/edges (P3-04) and validation DTO (P3-06) against real Neo4j."""
import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from jevtriage.db.schema import apply_schema
from jevtriage.db.tx import write_tx
from jevtriage.learning.shadow import rule_validations, validate_rules, validation_detail
from jevtriage.observe.flow import get_flow
from jevtriage.policy.service import bootstrap_policy

pytestmark = pytest.mark.asyncio(loop_scope="session")

NAMES = ["입력 정리", "Jev 판단", "근거 연결", "업무 분해", "규칙 적용", "자동 배정 조건 검사", "결과 저장"]


async def _cleanup(tenant):
    async def op(tx):
        await (await tx.run("MATCH (n {tenant_id:$tenant}) DETACH DELETE n", tenant=tenant)).consume()
    await write_tx(tenant, op)


async def test_flow_nodes_follow_execution_order_with_edges():
    tenant, run_id = f"ux_{uuid4().hex}", f"run_{uuid4().hex}"
    await apply_schema()
    ids = [f"step_{i}_{uuid4().hex}" for i in range(len(NAMES))]

    async def seed(tx):
        await (await tx.run("CREATE (:Run {id:$run,tenant_id:$tenant,request_id:'req_x',status:'succeeded'})", run=run_id, tenant=tenant)).consume()
        # Insert newest first so that storage/collect order is the reverse of execution order.
        for i in reversed(range(len(NAMES))):
            await (await tx.run(
                "MATCH (r:Run {id:$run,tenant_id:$tenant}) CREATE (r)-[:HAS_STEP]->(:RunStep {id:$id,tenant_id:$tenant,run_id:$run,name:$name,kind:'code',actor:'code',"
                "status:'succeeded',started_at:datetime($at),ended_at:datetime($at),predecessor_ids:[],attempt_id:$id})",
                run=run_id, tenant=tenant, id=ids[i], name=NAMES[i], at=(datetime(2026, 1, 1, tzinfo=UTC) + timedelta(seconds=i)).isoformat(),
            )).consume()
    await write_tx(tenant, seed)
    try:
        flow = await get_flow(tenant, run_id)
        assert [n["name"] for n in flow["nodes"]] == NAMES
        pairs = {(e["from"], e["to"]) for e in flow["edges"]}
        assert pairs == {(ids[i], ids[i + 1]) for i in range(len(ids) - 1)}
    finally:
        await _cleanup(tenant)


async def test_flow_predecessor_dag_and_review_node_label():
    tenant, run_id = f"ux_{uuid4().hex}", f"run_{uuid4().hex}"
    await apply_schema()

    async def seed(tx):
        await (await tx.run("CREATE (:Run {id:$run,tenant_id:$tenant,request_id:'req_x',status:'succeeded'})", run=run_id, tenant=tenant)).consume()
        await (await tx.run(
            "MATCH (r:Run {id:$run,tenant_id:$tenant}) "
            "CREATE (r)-[:HAS_STEP]->(:RunStep {id:'c',tenant_id:$tenant,name:'C',kind:'code',status:'succeeded',started_at:datetime('2026-01-01T00:00:00Z'),predecessor_ids:['a','b']}) "
            "CREATE (r)-[:HAS_STEP]->(:RunStep {id:'b',tenant_id:$tenant,name:'B',kind:'code',status:'succeeded',started_at:datetime('2026-01-01T00:00:00Z'),predecessor_ids:[]}) "
            "CREATE (r)-[:HAS_STEP]->(:RunStep {id:'a',tenant_id:$tenant,name:'A',kind:'code',status:'succeeded',started_at:datetime('2026-01-01T00:00:00Z'),predecessor_ids:[]}) "
            "CREATE (:Review {id:'rv1',tenant_id:$tenant,request_id:'req_x',run_id:$run,status:'pending',created_at:datetime('2026-01-01T00:00:05Z')})",
            run=run_id, tenant=tenant,
        )).consume()
    await write_tx(tenant, seed)
    try:
        flow = await get_flow(tenant, run_id)
        order = [n["id"] for n in flow["nodes"]]
        assert order.index("c") > order.index("a") and order.index("c") > order.index("b")
        assert order[-1] == "review:rv1"
        human = flow["nodes"][-1]
        assert human["name"] == "사람 검토"
        assert ("c", "review:rv1") in {(e["from"], e["to"]) for e in flow["edges"]}
    finally:
        await _cleanup(tenant)


async def test_validation_get_and_list_match_post_dto():
    tenant = f"ux_{uuid4().hex}"
    await apply_schema(); await bootstrap_policy(tenant)
    rid = "R-AI_NEED-77"
    rule = {"schema": "rule-v1", "rule_id": rid, "version": 1, "effect": "rule", "target": "ai_need", "scope": {"all": []}, "action": {"set": "혼합"}}

    async def seed(tx):
        await (await tx.run("CREATE (:RuleVersion {tenant_id:$tenant,id:$id,rule_id:$rid,body:$body,status:'validating'})", tenant=tenant, id=f"{rid}@1", rid=rid, body=json.dumps(rule))).consume()
        await (await tx.run("CREATE (:Judgment {tenant_id:$tenant,id:'jdg_t',request_id:'req_t',run_id:'run_t',created_at:datetime(),ai_need:'필요',feasibility:'가능',urgency:'일반',lead_org:'AI팀'})", tenant=tenant)).consume()
    await write_tx(tenant, seed)
    try:
        start, end = datetime.now(UTC) - timedelta(minutes=1), datetime.now(UTC) + timedelta(minutes=1)
        posted = await validate_rules(tenant, "tester", rid, 1, start, end)
        detail = await validation_detail(tenant, posted["id"])
        listed = (await rule_validations(tenant, rid, 1))[0]
        for got in (detail, listed):
            assert isinstance(got["changes_by_value"], dict) and got["changes_by_value"] == posted["changes_by_value"]
            assert got["from"] and got["to"] and got["from"].startswith(str(start.year))
            assert got["failures"] == [] and got["failure_count"] == 0
            assert isinstance(got["usage"], dict)
        assert posted["failure_count"] == 0 and posted["failures"] == []
    finally:
        await _cleanup(tenant)
