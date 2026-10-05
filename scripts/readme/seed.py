"""Seed three real LIVE requests and scoped learning history through public APIs."""
import json
import os
import time
import uuid
from pathlib import Path
import httpx
OUT = Path(os.environ['README_OUT'])
T = os.environ['README_TENANT']
BASE = 'http://127.0.0.1:10491'
TEXT = '사내 회의실 예약 현황을 부서별로 조회하고 예약 가능 시간을 확인하는 화면이 필요합니다. 데이터 존재 여부와 접근 권한, 품질을 확인해야 합니다. 현업이 수용 기준과 업무 범위를 정하고 IT팀이 데이터 연결과 화면 개발을 담당합니다. 가상 시연 자료이며 민감 정보는 없습니다.'
def client(role):
    c = httpx.Client(base_url=BASE, timeout=60)
    c.post('/api/auth/login',json={'email':f'{role}@{T}.dev','password':'dev-only-change-me'}).raise_for_status()
    return c
def call(c,method,url,body=None):
    r = c.request(method,url,json=body,headers={'X-CSRF-Token':c.cookies.get('jev_csrf',''),'Idempotency-Key':str(uuid.uuid4())})
    r.raise_for_status()
    return r.json()
rq,rev,admin = client('requester'),client('reviewer'),client('rule_admin')
ids=[]
for i in range(3):
    r = rq.post('/api/requests',data={'text':TEXT+f' 가상 사례 {i+1}.'},headers={'X-CSRF-Token':rq.cookies.get('jev_csrf',''),'Idempotency-Key':str(uuid.uuid4())})
    r.raise_for_status(); rid = r.json()['request_id']; ids.append(rid)
    for _ in range(160):
        r = rq.get(f'/api/requests/{rid}/judgment')
        if r.is_success:
            assert r.json()['mode'] == 'live'
            break
        time.sleep(.6)
    else:
        raise RuntimeError('LIVE judgment timeout')
    row = next(x for x in call(rev,'GET','/api/reviews?status=pending')['reviews'] if x['request_id']==rid)
    detail = call(rev,'GET',f"/api/reviews/{row['id']}")
    call(rev,'POST',f"/api/reviews/{row['id']}/decision",{'action':'approve_with_changes','request_id':rid,'input_revision':row['revision_id'],'run_id':row['run_id'],'draft_version':row['draft_version'],'review_version':row['review_version'],'changes':{'classifications':{'ai_need':'불필요' if detail['final_classifications']['ai_need']=='필요' else '필요'}},'reason':'가상 시연: 예약 조회의 업무 범위를 검토하고 담당자의 판단을 반영합니다.'})
    print(f'LIVE correction {i+1}/3',flush=True)
call(admin,'POST','/api/learning/candidates/generate')
candidate = next(x for x in call(admin,'GET','/api/learning/candidates')['candidates'] if x['field']=='ai_need')
reason = '가상 시연: 제한된 표본을 확인하여 전용 범위의 초안으로 보존합니다.'
d = call(admin,'POST',f"/api/learning/candidates/{candidate['id']}/decision",{'action':'approve_with_scope_change','scope':{'all':[{'requester_org':f'{T}-ai'}]},'reason':reason,'acknowledge_insufficient':True})
call(admin,'POST','/api/learning/rules/R-README-01/versions',{'decision_id':d['decision_id'],'body':{},'reason':reason,'acknowledge_insufficient':True})
(OUT/'seed.json').write_text(json.dumps({'tenant':T,'ids':ids,'candidate':candidate['id'],'text':TEXT},ensure_ascii=False))
print('SEED READY',flush=True)
