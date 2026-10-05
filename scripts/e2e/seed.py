"""Prepare isolated accounts and populated layout data; no external model calls."""
import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'backend'), str(ROOT / 'backend/tests/acceptance')]
from jevtriage.auth.core import hash_password
from jevtriage.db.driver import close_driver
from jevtriage.db.tx import write_tx
from provision import provision


async def main():
    tenant = os.environ['E2E_TENANT']
    await provision((tenant, tenant + 'f', tenant + 'g', tenant + 'b'))
    async def seed(tx):
        await (await tx.run('''MATCH (o:Org {tenant_id:$t}) WHERE o.name <> 'other'
MERGE (u:User {tenant_id:$t,id:$uid}) SET u.email=$email,u.password_hash=$ph,u.disabled=false
MERGE (u)-[:MEMBER_OF {role:'labeler'}]->(o)''', t=tenant, uid=f'usr_{tenant}_labeler', email=f'labeler@{tenant}.dev', ph=hash_password('dev-only-change-me'))).consume()
        await (await tx.run('''UNWIND range(1,30) AS i
MERGE (q:Request {tenant_id:$t,id:$t+'-layout-'+toString(i)})
SET q.title='레이아웃 스크롤 표본 '+toString(i), q.preview='목록 스크롤 검증용 저장 표본',
q.created_by=$uid,q.org_ids=[$org],q.status='취소됨',q.created_at=datetime()''', t=tenant, uid=f'usr_{tenant}_requester',org=f'{tenant}-it')).consume()
    await write_tx(tenant, seed)
    await close_driver()


asyncio.run(main())
