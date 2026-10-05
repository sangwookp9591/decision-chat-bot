import asyncio,sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'backend'))
from jevtriage.db.driver import get_driver,close_driver
async def main():
 d=await get_driver()
 async with d.session() as s:
  await (await s.run("""MATCH (q:Request {tenant_id:$t,id:$r}), (o:Org {tenant_id:$t,id:$o}), (source:Task {tenant_id:$t,id:$source})
  CREATE (p:Task) SET p=source{.*,id:'audit_confirmation',draft_task_id:'audit_confirmation'},p.title='감사 시드: 완료된 사전 확인',p.confirmation_task=true,p.status='완료',p.block_reasons=[],p.created_at=datetime()
  CREATE (n:Task) SET n=source{.*,id:'audit_blocked',draft_task_id:'audit_blocked'},n.title='감사 시드: 확인 완료 후 시작',n.status='막힘',n.block_reasons=['feasibility_unresolved'],n.reason=null,n.created_at=datetime(),n.predecessors='["audit_confirmation"]'
  CREATE (q)-[:HAS_TASK]->(p) CREATE (q)-[:HAS_TASK]->(n) CREATE (p)-[:PRECEDES]->(n) CREATE (p)-[:ASSIGNED_TO {role:'lead'}]->(o) CREATE (n)-[:ASSIGNED_TO {role:'lead'}]->(o)
  """,t='t-audit-e2e-1005',r='req_3503948c4b87404cba4714536567406e',o='t-audit-e2e-1005-it',source='task_1e7075ce6eae4128b5ab22d03e59252e')).consume()
 await close_driver()
asyncio.run(main())
print('seeded two Task fixtures inside dedicated tenant only')
