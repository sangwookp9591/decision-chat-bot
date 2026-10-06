"""Real Neo4j shadow validation isolation checks."""
import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from ildongi.db.schema import apply_schema
from ildongi.db.tx import read_tx, write_tx
from ildongi.learning.rules import mark_validated
from ildongi.learning.shadow import rule_validations, validate_rules, validation_detail
from ildongi.policy.service import bootstrap_policy

pytestmark=pytest.mark.asyncio(loop_scope="session")

async def test_shadow_stores_validation_without_business_mutation():
    tenant=f"shadow_{uuid4().hex}"
    await apply_schema(); await bootstrap_policy(tenant)
    rid="R-AI_NEED-99"
    rule={"schema":"rule-v1","rule_id":rid,"version":1,"effect":"rule","target":"ai_need","scope":{"all":[]},"action":{"set":"혼합"},"candidate_id":"cand_test","decision_id":"rdec_test"}
    async def seed(tx):
        await (await tx.run("CREATE (:RuleVersion {tenant_id:$tenant,id:$id,body:$body,status:'validating'})",tenant=tenant,id=f"{rid}@1",body=json.dumps(rule))).consume()
        await (await tx.run("CREATE (:Judgment {tenant_id:$tenant,id:'jdg_test',request_id:'req_test',run_id:'run_test',created_at:datetime(),ai_need:'필요',feasibility:'가능',urgency:'일반',lead_org:'AI팀'})",tenant=tenant)).consume()
    await write_tx(tenant,seed)
    start=datetime.now(UTC)-timedelta(minutes=1); end=datetime.now(UTC)+timedelta(minutes=1)
    result=await validate_rules(tenant,"tester",rid,1,start,end)
    assert result["id"].startswith("val_") and result["run_id"].startswith("run_shadow_")
    assert result["id"] != result["run_id"]
    async def linked(tx):
        return await (await tx.run("MATCH (v:ValidationRun {tenant_id:$tenant,id:$id})-[:HAS_SHADOW_RUN]->(r:Run {tenant_id:$tenant,id:$run}) RETURN count(r) AS n", tenant=tenant,id=result["id"],run=result["run_id"])).single(strict=True)
    assert (await read_tx(tenant, linked))["n"] == 1
    assert result["sample_count"]==1 and result["changed_count"]==1 and result["side_effects"]==0 and result["status"]=="completed"
    async def check(tx):
        return await (await tx.run("MATCH (v:ValidationRun {tenant_id:$tenant})-[:VALIDATES]->(r:RuleVersion) RETURN v.run_kind AS kind,v.sample_count AS n,r.id AS rule",tenant=tenant)).single(strict=True)
    row=await read_tx(tenant,check)
    assert row["kind"]=="shadow" and row["n"]==1 and row["rule"]==f"{rid}@1"
    detail=await validation_detail(tenant,result["id"])
    listed=await rule_validations(tenant,rid,1)
    assert detail["id"]==result["id"] and isinstance(detail["created_at"],str)
    assert listed[0]["id"]==result["id"] and isinstance(listed[0]["from_at"],str)
    assert await validation_detail("other_tenant",result["id"]) is None
    async def cleanup(tx): await (await tx.run("MATCH (n {tenant_id:$tenant}) DETACH DELETE n",tenant=tenant)).consume()
    await write_tx(tenant,cleanup)


async def test_human_truth_and_validation_gate():
    tenant=f"shadow_{uuid4().hex}"
    await apply_schema(); await bootstrap_policy(tenant)
    rid="R-AI_NEED-98"
    rule={"schema":"rule-v1","rule_id":rid,"version":1,"effect":"rule","target":"ai_need","scope":{"all":[]},"action":{"set":"혼합"}}
    async def seed(tx):
        await (await tx.run("CREATE (:RuleVersion {tenant_id:$tenant,id:$id,rule_id:$rid,body:$body,status:'validating'})",tenant=tenant,id=f"{rid}@1",rid=rid,body=json.dumps(rule))).consume()
        await (await tx.run("CREATE (:Judgment {tenant_id:$tenant,id:'jdg_1',request_id:'req_1',run_id:'run_1',created_at:datetime(),ai_need:'필요',feasibility:'가능',urgency:'일반',lead_org:'AI팀'})",tenant=tenant)).consume()
        await (await tx.run("CREATE (h:ReviewDecision {tenant_id:$tenant,id:'rdec_1',run_id:'run_1',action:'approve_with_changes'}) CREATE (c:Correction {tenant_id:$tenant,id:'cor_1',run_id:'run_1',field:'ai_need',corrected_value:$value}) CREATE (h)-[:RECORDED]->(c)",tenant=tenant,value=json.dumps("혼합"))).consume()
    await write_tx(tenant,seed)
    start=datetime.now(UTC)-timedelta(minutes=1); end=datetime.now(UTC)+timedelta(minutes=1)
    result=await validate_rules(tenant,"tester",rid,1,start,end)
    assert (result["labeled_count"],result["human_correction_needed_base"],result["human_correction_needed_candidate"]) == (1,1,0)
    validated=await mark_validated(tenant,"tester",rid,1,result["id"],"수치 대조 완료",f"key_{uuid4().hex}")
    assert validated["status"]=="validated"
    async def cleanup(tx): await (await tx.run("MATCH (n {tenant_id:$tenant}) DETACH DELETE n",tenant=tenant)).consume()
    await write_tx(tenant,cleanup)


async def test_context_call_limit_records_failure():
    from ildongi.judgment.ai_client import AiClient
    tenant=f"shadow_{uuid4().hex}"
    revision=f"rev_{uuid4().hex}"
    await apply_schema(); await bootstrap_policy(tenant)
    rid="R-CONTEXT-98"
    rule={"schema":"rule-v1","rule_id":rid,"version":1,"effect":"context","target":"ai_need","scope":{"all":[]},"action":{"set":"혼합"},"context_text":"검증된 기준"}
    async def seed(tx):
        await (await tx.run("CREATE (:RuleVersion {tenant_id:$tenant,id:$id,body:$body,status:'validating'})",tenant=tenant,id=f"{rid}@1",body=json.dumps(rule))).consume()
        await (await tx.run("CREATE (:Judgment {tenant_id:$tenant,id:'jdg_1',request_id:'req_1',revision_id:$revision,run_id:'run_1',created_at:datetime(),ai_need:'필요',feasibility:'가능',urgency:'일반',lead_org:'AI팀'})",tenant=tenant,revision=revision)).consume()
        await (await tx.run("CREATE (:InputRevision {tenant_id:$tenant,id:$revision,request_id:'req_1',text:'업무 요청'})",tenant=tenant,revision=revision)).consume()
    await write_tx(tenant,seed)
    start=datetime.now(UTC)-timedelta(minutes=1); end=datetime.now(UTC)+timedelta(minutes=1)
    result=await validate_rules(tenant,"tester",rid,1,start,end,max_calls=1,client=AiClient(api_key="unused",mode="mock"))
    assert result["calls"]==1 and result["max_calls"]==1 and result["status"]=="failed"
    assert result["failures"][0]["reason"]=="shadow_max_calls_exceeded"
    from ildongi.policy.service import PolicyError
    with pytest.raises(PolicyError, match="부작용 0건인 완료 검증이 필요합니다"):
        await mark_validated(tenant,"tester",rid,1,result["id"],"실패 검증은 불가",f"key_{uuid4().hex}")
    completed=await validate_rules(tenant,"tester",rid,1,start,end,max_calls=20,client=AiClient(api_key="unused",mode="mock"))
    assert completed["status"]=="completed" and completed["calls"]==6
    assert completed["usage"]=={"input_tokens":0,"output_tokens":0}
    async def cleanup(tx): await (await tx.run("MATCH (n {tenant_id:$tenant}) DETACH DELETE n",tenant=tenant)).consume()
    await write_tx(tenant,cleanup)


async def test_protected_snapshot_detects_in_place_changes_and_blocks_validation():
    from ildongi.learning.shadow import _protected_snapshot
    from ildongi.policy.service import PolicyError
    tenant=f"shadow_{uuid4().hex}"
    await apply_schema(); await bootstrap_policy(tenant)
    rid="R-AI_NEED-96"
    async def seed(tx):
        await (await tx.run("CREATE (:RuleVersion {tenant_id:$tenant,id:$id,status:'validating'}) CREATE (:Request {tenant_id:$tenant,id:$request,active_run_id:'run_a'})",tenant=tenant,id=f"{rid}@1",request=f"req_{uuid4().hex}")).consume()
        return await _protected_snapshot(tx,tenant)
    before=await write_tx(tenant,seed)
    async def mutate(tx):
        await (await tx.run("MATCH (q:Request {tenant_id:$tenant}) SET q.active_run_id='run_b'",tenant=tenant)).consume()
        return await _protected_snapshot(tx,tenant)
    after=await write_tx(tenant,mutate)
    assert before["count"]==after["count"] and before["sha256"]!=after["sha256"]
    async def add_validation(tx):
        await (await tx.run("MATCH (r:RuleVersion {tenant_id:$tenant,id:$rule}) CREATE (v:ValidationRun {tenant_id:$tenant,id:$id,status:'completed',side_effects:1})-[:VALIDATES]->(r)",tenant=tenant,rule=f"{rid}@1",id=f"val_{uuid4().hex}")).consume()
        return await (await tx.run("MATCH (v:ValidationRun {tenant_id:$tenant}) RETURN v.id AS id",tenant=tenant)).single()
    row=await write_tx(tenant,add_validation)
    with pytest.raises(PolicyError, match="부작용 0건인 완료 검증이 필요합니다"):
        await mark_validated(tenant,"tester",rid,1,row["id"],"변경 감지",f"key_{uuid4().hex}")
    async def cleanup(tx): await (await tx.run("MATCH (n {tenant_id:$tenant}) DETACH DELETE n",tenant=tenant)).consume()
    await write_tx(tenant,cleanup)
