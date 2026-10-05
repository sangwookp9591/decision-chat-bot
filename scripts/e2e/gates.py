"""Generate G05/G06 records from a real auto assignment and direct Neo4j reads."""
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
os.environ['ACC_TENANT'] = os.environ['E2E_TENANT']
os.environ['ACC_API'] = os.environ['E2E_BASE_URL']
from tests.acceptance.acc_e_gates import G, graph_edges, stored_graph
from tests.acceptance.harness import Client

rq, pe = Client('requester', G), Client('policy_editor', G)
active = pe.get('/api/policy/active').json()
config = active['config']
config['auto_assign'] = True
r = pe.post('/api/policy/publish', json={'config': config, 'reason': 'E2E mock 자동 배정 fixture', 'expected_active_version': active['version']})
assert r.status_code == 200, r.text
r = rq.post('/api/requests', data={'text': 'E2E_AUTO_ASSIGN: 승인된 데이터로 시스템 연동 및 조회 화면을 만듭니다.'})
assert r.status_code == 202, r.text
rid = r.json()['request_id']
for _ in range(120):
    g = stored_graph(rid)
    if g['tasks']:
        break
    time.sleep(.5)
assert g['tasks'], rq.get(f'/api/requests/{rid}/judgment').text
assert g['assignments'][0]['pathway'] == 'auto'
g['rid'] = rid
rows = [
 {'name': 'g05_auto_assign', 'data': {'auto_assigned': {'fixture': {'request_id': rid, 'tasks': [t['id'] for t in g['tasks']], 'assigned_to': [[a['task'],a['role'],a['org']] for a in g['assigned_to']], 'precedes': [[p['from'],p['to']] for p in g['precedes']]}}}},
 {'name': 'g06_graph', 'data': {'request_id': rid, 'cypher_edges': list(graph_edges(g)), 'task_nodes': g['tasks'], 'org_nodes': sorted({a['org'] for a in g['assigned_to']}), 'precedes_edges': [[p['from'],p['to'],p['from_title'],p['to_title']] for p in g['precedes']]}}
]
Path(sys.argv[1]).write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
