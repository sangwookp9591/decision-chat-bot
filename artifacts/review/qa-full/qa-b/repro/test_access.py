"""7 roles × read / mutation HTTP authorization matrix, isolated QA-B tenant."""
from uuid import uuid4

import pytest
from test_evaluation import client

ROLES = ['requester', 'reviewer', 'team_member', 'operator', 'policy_editor', 'rule_admin', 'labeler']
READS = {
    '/api/requests': ROLES,
    '/api/tasks': ROLES,
    '/api/policy/active': ROLES,
    '/api/policy/versions': ROLES,
    '/api/graph/judgment': ['reviewer', 'operator', 'rule_admin'],
    '/api/learning/candidates': ['reviewer', 'operator', 'rule_admin'],
    '/api/learning/rules': ['reviewer', 'operator', 'rule_admin'],
    '/api/learning/corrections': ['reviewer', 'operator', 'rule_admin'],
    '/api/evaluation/candidates?split=final': ['labeler', 'reviewer'],
    '/api/monitoring/summary': ['operator'],
    '/api/monitoring/alerts': ['operator'],
    '/api/monitoring/slo': ['operator'],
}

@pytest.mark.parametrize('role', ROLES)
def test_role_matrix(role):
    with client(role) as api:
        for path, allowed in READS.items():
            response = api.get(path)
            assert response.status_code == (200 if role in allowed else 403), (role, path, response.status_code, response.text[:250])
        if role != 'policy_editor':
            active = api.get('/api/policy/active').json()
            response = api.post('/api/policy/publish', headers={'Idempotency-Key': str(uuid4())}, json={'config': active['config'], 'reason': 'QA permission negative test', 'expected_active_version': active['version']})
            assert response.status_code == 403
        if role != 'rule_admin':
            for path, data in [
                ('/api/learning/candidates/nonexistent/decision', {'action':'approve','reason':'QA'}),
                ('/api/learning/rules/nonexistent/versions/1/publish', {'expected_active_config_version':1,'reason':'QA'}),
                ('/api/learning/rules/nonexistent/revert', {'expected_active_config_version':1,'reason':'QA','to_version':1}),
                ('/api/learning/rules/nonexistent/versions/1/validate', {}),
            ]:
                response = api.post(path, headers={'Idempotency-Key': str(uuid4())}, json=data)
                assert response.status_code == 403, (role, path, response.status_code)
