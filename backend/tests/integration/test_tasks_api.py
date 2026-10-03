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
