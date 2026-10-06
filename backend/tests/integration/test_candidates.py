"""Rule-candidate generation persistence checks against Neo4j."""
from __future__ import annotations

from uuid import uuid4

import pytest

from ildongi.db.schema import apply_schema
from ildongi.db.tx import read_tx, write_tx
from ildongi.learning.candidates import generate_candidates
from ildongi.policy.service import bootstrap_policy, get_active_snapshot

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest.fixture
async def tenant():
    value = f"candidate_{uuid4().hex}"
    await apply_schema()
    await bootstrap_policy(value)
    yield value
    async def cleanup(tx):
        await (await tx.run("MATCH (n {tenant_id:$tenant}) DETACH DELETE n", tenant=value)).consume()
    await write_tx(value, cleanup)


async def seed_corrections(tenant: str, count: int):
    async def seed(tx):
        for index in range(count):
            request, run = f"req_{uuid4().hex}", f"run_{uuid4().hex}"
            judgment = f"jdg_{uuid4().hex}"
            decision, correction = f"rdec_{uuid4().hex}", f"cor_{uuid4().hex}"
            await (await tx.run(
                "CREATE (:Request {id:$request,tenant_id:$tenant,created_by:'user',org_ids:[],created_at:datetime()}) "
                "CREATE (:Run {id:$run,tenant_id:$tenant,request_id:$request,created_at:datetime()}) "
                "CREATE (:Judgment {id:$judgment,tenant_id:$tenant,request_id:$request,run_id:$run,"
                "ai_need:'정보 부족',feasibility:'조건부 가능',urgency:'일반',lead_org:'IT팀'}) "
                "CREATE (h:ReviewDecision {id:$decision,tenant_id:$tenant,request_id:$request,run_id:$run,"
                "action:'approve_with_changes',actor_id:'reviewer',created_at:datetime()}) "
                "CREATE (c:Correction {id:$correction,tenant_id:$tenant,request_id:$request,run_id:$run,"
                "field:'feasibility',ai_value:'\"조건부 가능\"',corrected_value:'\"가능\"',"
                "corrected_by:'reviewer',corrected_at:datetime(),config_version:1,evidence_span_ids:'[]'}) "
                "CREATE (h)-[:RECORDED]->(c)", tenant=tenant, request=request, run=run,
                judgment=judgment, decision=decision, correction=correction,
            )).consume()
    await write_tx(tenant, seed)


async def seed_unchanged_approval(tenant: str):
    request, run, decision = f"req_{uuid4().hex}", f"run_{uuid4().hex}", f"rdec_{uuid4().hex}"
    async def seed(tx):
        await (await tx.run(
            "CREATE (:Request {id:$request,tenant_id:$tenant,created_by:'user',org_ids:[],created_at:datetime()}) "
            "CREATE (:Judgment {id:$judgment,tenant_id:$tenant,request_id:$request,run_id:$run,"
            "ai_need:'정보 부족',feasibility:'조건부 가능',urgency:'일반',lead_org:'IT팀'}) "
            "CREATE (:ReviewDecision {id:$decision,tenant_id:$tenant,request_id:$request,run_id:$run,"
            "action:'approve',actor_id:'reviewer',created_at:datetime()})",
            tenant=tenant,request=request,run=run,decision=decision,judgment=f"jdg_{uuid4().hex}",
        )).consume()
    await write_tx(tenant, seed)


async def test_three_support_cases_generate_idempotent_candidate_without_config_write(tenant):
    await seed_corrections(tenant, 3)
    before = await get_active_snapshot(tenant)
    first = await generate_candidates(tenant)
    second = await generate_candidates(tenant)
    after = await get_active_snapshot(tenant)
    assert len(first) == len(second) == 1
    assert first[0]["id"] == second[0]["id"]
    assert first[0]["support_count"] == 3
    assert first[0]["status"] == "제안"
    assert first[0]["proposed_body"]["scope"]["all"]
    assert before == after
    async def stored(tx):
        return (await (await tx.run(
            "MATCH (c:RuleCandidate {tenant_id:$tenant}) RETURN count(c) AS n",
            tenant=tenant,
        )).single(strict=True))["n"]
    assert await read_tx(tenant, stored) == 1


async def test_two_support_cases_are_marked_insufficient(tenant):
    await seed_corrections(tenant, 2)
    result = await generate_candidates(tenant)
    assert result[0]["status"] == "자료 부족"
    assert result[0]["support_count"] == 2


async def test_unchanged_approval_in_matching_scope_is_counterexample(tenant):
    await seed_corrections(tenant, 3)
    await seed_unchanged_approval(tenant)
    result = await generate_candidates(tenant)
    assert result[0]["counter_count"] == 1
    assert result[0]["uncertainty"]["counter_count"] == 1
