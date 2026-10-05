"""QA-C-04 / R9: filtering after LIMIT must not hide an authorized pending review."""
import json
from pathlib import Path
from uuid import uuid4

import pytest

pytestmark = pytest.mark.asyncio(loop_scope='module')
EVIDENCE=Path(__file__).resolve().parents[1]/'evidence'


async def test_authorized_review_survives_newer_other_org_reviews(runtime):
    prefix='starve_'+uuid4().hex[:8]
    await runtime.write(
        "UNWIND range(0,100) AS i "
        "CREATE (q:Request {tenant_id:$tenant,id:$prefix+'_q_'+toString(i),created_by:'other',"
        "org_ids:[],shared_org_ids:[],status:'review_pending',"
        "active_run_id:$prefix+'_run_'+toString(i),latest_revision_id:$prefix+'_rev_'+toString(i)}) "
        "CREATE (v:Review {tenant_id:$tenant,id:$prefix+'_v_'+toString(i),request_id:q.id,"
        "run_id:q.active_run_id,revision_id:q.latest_revision_id,status:'pending',"
        "draft_version:1,review_version:1,reasons:'[]',"
        "created_at:datetime()+duration({seconds:i}),"
        "required_reviewer_org:CASE WHEN i=0 THEN $tenant+'-business' ELSE $tenant+'-unrelated' END})",
        prefix=prefix)
    c=await runtime.login()
    try:
        r=await c.get('/api/reviews')
        assert r.status_code==200
        ids=[item['id'] for item in r.json()['reviews']]
        target=prefix+'_v_0'
        direct=await c.get('/api/reviews/'+target)
        (EVIDENCE/'review-starvation.json').write_text(json.dumps(
            {'tenant':runtime.tenant,'target':target,'seeded':101,'direct_status':direct.status_code,
             'queue_ids':ids},ensure_ascii=False,indent=2))
        assert direct.status_code==200, 'target must be authorized in the detail endpoint'
        assert target in ids, 'authorized review hidden behind newer reviews from another organization'
    finally:
        await runtime.write('MATCH (n {tenant_id:$tenant}) WHERE n.id STARTS WITH $prefix DETACH DELETE n',prefix=prefix)
        await c.aclose()
