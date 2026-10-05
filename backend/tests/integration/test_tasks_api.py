"""Task query scoping, predecessor guards, and optimistic state updates."""
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from jevtriage.auth.core import Principal, get_principal
from jevtriage.db.schema import apply_schema
from jevtriage.db.tx import write_tx
from jevtriage.main import create_app


@pytest.mark.asyncio
async def test_task_filters_permissions_and_transitions():
    tenant=f"tasks_{uuid4().hex}"
    await apply_schema()
    request=f"req_{uuid4().hex}"; before=f"task_{uuid4().hex}"; target=f"task_{uuid4().hex}"
    async def seed(tx):
        await (await tx.run(
            "CREATE (o:Org {tenant_id:$tenant,id:$org,name:'IT팀'}) "
            "CREATE (q:Request {tenant_id:$tenant,id:$request,created_by:'other',org_ids:[$org],status:'배정 완료'}) "
            "CREATE (p:Task {tenant_id:$tenant,id:$before,request_id:$request,status:'완료',title:'선행'}) "
            "CREATE (t:Task {tenant_id:$tenant,id:$target,request_id:$request,status:'막힘',title:'후행',method:'일반 기술',lead_org:'IT팀',collab_orgs:'[]',predecessors:'[]',deliverable:'보고서'}) "
            "CREATE (q)-[:HAS_TASK]->(p) CREATE (q)-[:HAS_TASK]->(t) "
            "CREATE (p)-[:PRECEDES]->(t) CREATE (t)-[:ASSIGNED_TO {role:'lead'}]->(o)",
            tenant=tenant,org=f"{tenant}-it",request=request,before=before,target=target,
        )).consume()
    await write_tx(tenant,seed)
    app=create_app(); principal=Principal(tenant,'worker',(f'{tenant}-it',),frozenset({'team_member'}))
    app.dependency_overrides[get_principal]=lambda:principal
    try:
        with TestClient(app) as client:
            listed=client.get('/api/tasks?status=막힘')
            assert listed.status_code==200 and [x['id'] for x in listed.json()['tasks']]==[target]
            assert [x['id'] for x in client.get('/api/tasks?org=IT팀&role=lead&method=일반%20기술').json()['tasks']]==[target]
            denied=client.get(f'/api/tasks/{target}')
            assert denied.status_code==200
            bad=client.post(f'/api/tasks/{target}/transition',json={'to':'진행','expected_status':'대기'})
            assert bad.status_code==409
            moved=client.post(f'/api/tasks/{target}/transition',json={'to':'진행','expected_status':'막힘'})
            assert moved.status_code==200 and moved.json()['status']=='진행'
            stale=client.post(f'/api/tasks/{target}/transition',json={'to':'진행','expected_status':'막힘'})
            assert stale.status_code==409
            completed=client.post(f'/api/tasks/{target}/transition',json={'to':'완료','expected_status':'진행'})
            assert completed.status_code==200
            app.dependency_overrides[get_principal]=lambda:Principal(tenant,'outsider',(f'{tenant}-ai',),frozenset({'team_member'}))
            assert client.get(f'/api/tasks/{target}').status_code==404
            assert client.get('/api/tasks').json()['tasks']==[]
    finally:
        app.dependency_overrides.clear()
        async def cleanup(tx):
            await (await tx.run('MATCH (n {tenant_id:$tenant}) DETACH DELETE n',tenant=tenant)).consume()
        await write_tx(tenant,cleanup)


@pytest.mark.asyncio
async def test_task_start_readiness_is_projected_by_server():
    tenant=f"tasks_ready_{uuid4().hex}"
    await apply_schema()
    request=f"req_{uuid4().hex}"
    confirmation=f"task_{uuid4().hex}"
    waiting_confirmation=f"task_{uuid4().hex}"
    ready=f"task_{uuid4().hex}"
    pending=f"task_{uuid4().hex}"
    async def seed(tx):
        await (await tx.run(
            "CREATE (o:Org {tenant_id:$tenant,id:$org,name:'IT팀'}) "
            "CREATE (q:Request {tenant_id:$tenant,id:$request,created_by:'other',org_ids:[$org],status:'배정 완료'}) "
            "CREATE (p:Task {tenant_id:$tenant,id:$confirmation,request_id:$request,status:'완료',title:'확인 완료',confirmation_task:true}) "
            "CREATE (u:Task {tenant_id:$tenant,id:$waiting_confirmation,request_id:$request,status:'진행',title:'확인 대기',confirmation_task:true}) "
            "CREATE (r:Task {tenant_id:$tenant,id:$ready,request_id:$request,status:'막힘',title:'시작 가능',method:'일반 기술',lead_org:'IT팀',collab_orgs:'[]',predecessors:'[]',deliverable:'보고서',block_reasons:['feasibility_unresolved']}) "
            "CREATE (w:Task {tenant_id:$tenant,id:$pending,request_id:$request,status:'막힘',title:'확인 대기',method:'일반 기술',lead_org:'IT팀',collab_orgs:'[]',predecessors:'[]',deliverable:'보고서',block_reasons:['predecessor_incomplete','feasibility_unresolved']}) "
            "CREATE (q)-[:HAS_TASK]->(p) CREATE (q)-[:HAS_TASK]->(u) CREATE (q)-[:HAS_TASK]->(r) CREATE (q)-[:HAS_TASK]->(w) "
            "CREATE (p)-[:PRECEDES]->(r) CREATE (u)-[:PRECEDES]->(w) "
            "CREATE (r)-[:ASSIGNED_TO {role:'lead'}]->(o) CREATE (w)-[:ASSIGNED_TO {role:'lead'}]->(o)",
            tenant=tenant,org=f'{tenant}-it',request=request,confirmation=confirmation,waiting_confirmation=waiting_confirmation,ready=ready,pending=pending,
        )).consume()
    await write_tx(tenant,seed)
    app=create_app(); principal=Principal(tenant,'worker',(f'{tenant}-it',),frozenset({'team_member'}))
    app.dependency_overrides[get_principal]=lambda:principal
    try:
        with TestClient(app) as client:
            listed={item['id']:item for item in client.get('/api/tasks').json()['tasks']}
            assert listed[ready]['can_start'] is True
            assert listed[ready]['start_blockers'] == []
            assert listed[pending]['can_start'] is False
            assert listed[pending]['start_blockers']
            detail=client.get(f'/api/tasks/{ready}').json()['task']
            assert detail['can_start'] is True
            assert detail['start_blockers'] == []
            assert client.post(f'/api/tasks/{ready}/transition',json={'to':'진행','expected_status':'막힘'}).status_code==200
            blocked=client.post(f'/api/tasks/{pending}/transition',json={'to':'진행','expected_status':'막힘'})
            assert blocked.status_code==409
    finally:
        app.dependency_overrides.clear()
        async def cleanup(tx):
            await (await tx.run('MATCH (n {tenant_id:$tenant}) DETACH DELETE n',tenant=tenant)).consume()
        await write_tx(tenant,cleanup)
