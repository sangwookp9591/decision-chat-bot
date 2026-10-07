"""Task state transitions guarded by task ownership and predecessor readiness."""
from __future__ import annotations

from ildongi.auth.core import Principal
from ildongi.auth.policy import can
from ildongi.db.audit import append_audit_in_tx
from ildongi.db.events import append_event_in_tx
from ildongi.db.tx import write_tx
from ildongi.tasks.store import list_tasks, lock_task_in_tx, project_start_readiness


class TaskError(Exception):
    def __init__(self,message:str,status_code:int=422): self.status_code=status_code; super().__init__(message)


async def transition(principal: Principal, task_id: str, target: str, expected: str) -> dict:
    if 'team_member' not in principal.roles: raise TaskError('팀 담당자 권한이 필요합니다',403)
    allowed={('대기','진행'),('막힘','진행'),('진행','완료')}
    if (expected,target) not in allowed: raise TaskError('허용되지 않은 업무 상태 전이입니다')
    tenant=principal.tenant_id
    async def op(tx):
        task=await lock_task_in_tx(tx,tenant,task_id)
        if task is None: raise TaskError('업무를 찾을 수 없습니다',404)
        if task.get('status') != expected: raise TaskError('업무 상태가 변경되었습니다. 최신 상태를 다시 불러오세요.',409)
        orgs=await (await tx.run(
            "MATCH (t:Task {tenant_id:$tenant,id:$id})-[:ASSIGNED_TO]->(o:Org) "
            "RETURN collect(o.id) AS ids",tenant=tenant,id=task_id)).single(strict=True)
        if not set(orgs['ids']).intersection(principal.org_ids): raise TaskError('담당 조직 업무만 변경할 수 있습니다',403)
        if target=='진행':
            row=await (await tx.run(
                "MATCH (t:Task {tenant_id:$tenant,id:$id}) "
                "OPTIONAL MATCH (p:Task {tenant_id:$tenant})-[:PRECEDES]->(t) "
                "RETURN collect({status:p.status,confirmation:p.confirmation_task}) AS predecessors",
                tenant=tenant,id=task_id)).single(strict=True)
            predecessors = [p for p in row['predecessors'] if p['status'] is not None]
            reasons = list(task.get('block_reasons') or [])
            readiness = project_start_readiness({
                **task,
                'predecessor_tasks': [
                    {'status': p['status'], 'confirmation_task': p['confirmation']}
                    for p in predecessors
                ],
            })
            if not readiness['can_start']:
                raise TaskError('선행 업무 완료와 본업무 전제 해결 후 진행할 수 있습니다',409)
            if any(p.get('confirmation') and p.get('status') in ('완료','completed') for p in predecessors):
                reasons = [reason for reason in reasons if reason != 'feasibility_unresolved']
            reasons = [reason for reason in reasons if reason != 'predecessor_incomplete']
        await (await tx.run("MATCH (t:Task {tenant_id:$tenant,id:$id}) SET t.status=$target,t.updated_at=datetime(),t.block_reasons=$reasons",tenant=tenant,id=task_id,target=target,reasons=reasons if target=='진행' else list(task.get('block_reasons') or []))).consume()
        await append_audit_in_tx(tx,tenant,principal.user_id,'task.transition','Task',task_id,
                                 {'status':expected,'block_reasons':list(task.get('block_reasons') or [])},
                                 {'status':target,'block_reasons':reasons if target=='진행' else list(task.get('block_reasons') or [])},
                                 f'{expected} → {target}')
        await append_event_in_tx(tx,tenant,'task.transitioned',{'task_id':task_id,'from':expected,'to':target},request_id=task.get('request_id'))
        return {'id':task_id,'status':target}
    return await write_tx(tenant,op)


def task_visible(p:Principal, task:dict)->bool:
    request=task.get('request') or task
    request.setdefault('tenant_id',p.tenant_id)
    request['shared_org_ids']=request.get('shared_org_ids') or ()
    request['org_ids']=request.get('org_ids') or ()
    return can(p,"view_task",{**request,"task_org_ids":[item["org"] for item in task.get("orgs",[])]})


async def visible_tasks(principal: Principal) -> list[dict]:
    rows = await list_tasks(principal.tenant_id, {})
    return [{**row, "kind": "assigned_task"} for row in rows if task_visible(principal, row)]
