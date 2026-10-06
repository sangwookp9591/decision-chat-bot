"""Effects endpoint role and insufficient sample contract."""
from uuid import uuid4

import httpx
import pytest

from ildongi.auth.core import Principal, get_principal
from ildongi.db.schema import apply_schema
from ildongi.db.tx import write_tx
from ildongi.learning.effects import rule_effects
from ildongi.main import create_app
from ildongi.policy.service import bootstrap_policy

pytestmark=pytest.mark.asyncio(loop_scope="session")
async def test_effects_requires_rule_admin():
    app=create_app()
    app.dependency_overrides[get_principal]=lambda:Principal("effects_tenant","user",(),frozenset({"requester"}))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url="http://test") as client:
        response=await client.get("/api/learning/rules/R-ROUTE-01/effects")
    assert response.status_code==403


async def test_effects_known_windows_and_application_groups():
    tenant=f"effects_{uuid4().hex}"
    await apply_schema(); await bootstrap_policy(tenant)
    rid="R-AI_NEED-97"
    async def seed(tx):
        await (await tx.run("CREATE (r:RuleVersion {tenant_id:$tenant,id:$id,rule_id:$rid}) CREATE (c:ConfigVersion {tenant_id:$tenant,id:$cid,version:2,created_at:datetime()}) CREATE (r)-[:PUBLISHED_IN]->(c)",tenant=tenant,id=f"{rid}@1",rid=rid,cid=f"cfg_{tenant}_2")).consume()
        await (await tx.run("UNWIND range(0,39) AS i CREATE (r:Run {tenant_id:$tenant,id:$tenant+'-run_'+toString(i),run_kind:'production',status:CASE WHEN i<20 THEN 'failed' ELSE 'completed' END,started_at:datetime()+duration({hours:CASE WHEN i<20 THEN -1 ELSE 1 END}),first_judgment_committed_at:datetime()+duration({hours:CASE WHEN i<20 THEN -1 ELSE 1 END,seconds:CASE WHEN i<20 THEN 1 ELSE 2 END})}) CREATE (:Judgment {tenant_id:$tenant,id:$tenant+'-jdg_'+toString(i),run_id:r.id}) WITH r,i WHERE i<20 CREATE (:Correction {tenant_id:$tenant,id:$tenant+'-cor_'+toString(i),run_id:r.id})",tenant=tenant)).consume()
        await (await tx.run("UNWIND range(20,39) AS i MATCH (r:Run {tenant_id:$tenant,id:$tenant+'-run_'+toString(i)}) MATCH (rule:RuleVersion {tenant_id:$tenant,id:$id}) CREATE (s:RunStep {tenant_id:$tenant,id:$tenant+'-step_'+toString(i),run_id:r.id}) CREATE (s)-[:APPLIED {outcome:CASE WHEN i<30 THEN 'used' ELSE 'out_of_scope' END,before:'필요',after:CASE WHEN i<30 THEN '혼합' ELSE '필요' END}]->(rule)",tenant=tenant,id=f"{rid}@1")).consume()
        await (await tx.run("UNWIND range(0,39) AS i CREATE (:ReviewDecision {tenant_id:$tenant,id:$tenant+'-dec_'+toString(i),run_id:$tenant+'-run_'+toString(i),action:'approve'})",tenant=tenant)).consume()
    await write_tx(tenant,seed)
    result=await rule_effects(tenant,rid,7)
    before=result["before_after"]["before"]; after=result["before_after"]["after"]
    assert result["effect"]=="improved"
    assert (before["sample_count"],after["sample_count"])==(20,20)
    assert (before["correction_rate"],after["correction_rate"])==(1,0)
    assert (before["failure_rate"],after["failure_rate"])==(1,0)
    assert (result["groups"]["used"]["sample_count"],result["groups"]["used"]["classification_change_rate"])==(10,1)
    assert (result["groups"]["out_of_scope"]["sample_count"],result["groups"]["out_of_scope"]["classification_change_rate"])==(10,0)
    assert before["latency_p50_ms"]==1000 and after["latency_p95_ms"]==2000
    async def cleanup(tx): await (await tx.run("MATCH (n {tenant_id:$tenant}) DETACH DELETE n",tenant=tenant)).consume()
    await write_tx(tenant,cleanup)
