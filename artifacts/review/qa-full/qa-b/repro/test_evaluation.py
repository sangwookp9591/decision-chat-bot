"""Run with QA-B API alive: backend/.venv/bin/pytest -q this_file."""
import os
from contextlib import contextmanager
from pathlib import Path

import httpx
import pytest

BASE = os.environ.get('QA_B_API', 'http://127.0.0.1:11391')
TENANT = os.environ.get('E2E_TENANT') or (Path(__file__).parents[1] / 'runtime/tenant.txt').read_text().strip()


@contextmanager
def client(role):
    api = httpx.Client(base_url=BASE, timeout=45)
    response = api.post('/api/auth/login', json={'email': f'{role}@{TENANT}.dev', 'password': 'dev-only-change-me'})
    assert response.status_code == 200
    api.headers['X-CSRF-Token'] = api.cookies['jev_csrf']
    try:
        yield api
    finally:
        api.close()


def candidates(api):
    response = api.get('/api/evaluation/candidates?split=tuning')
    assert response.status_code == 200
    return response.json()


@pytest.mark.parametrize('labels', [
    {'ai_need': 'INVALID', 'feasibility': 'INVALID', 'urgency': 'INVALID', 'team_set': 'not-array', 'risk_areas': 123},
    {'ai_need': None, 'feasibility': None, 'urgency': None, 'team_set': [], 'risk_areas': []},
])
def test_invalid_label_values_rejected(labels):
    with client('labeler') as api:
        row = candidates(api)['candidates'][-1]
        result = api.put(f"/api/evaluation/candidates/tuning/{row['id']}", json={'labels': labels, 'confidence': 0.8, 'status': 'confirmed'})
        assert result.status_code == 422, f'invalid labels were persisted: HTTP {result.status_code} {result.text}'


def test_consensus_preserves_completed_progress():
    with client('labeler') as labeler, client('reviewer') as reviewer:
        row = candidates(labeler)['candidates'][-2]
        labels = row['proposed_labels']
        other = {**labels, 'ai_need': '필요' if labels['ai_need'] != '필요' else '불필요'}
        path = f"/api/evaluation/candidates/tuning/{row['id']}"
        for api, value in [(labeler, labels), (reviewer, other)]:
            assert api.put(path, json={'labels': value, 'confidence': 0.8}).status_code == 200
        before = candidates(labeler)['progress']
        result = labeler.post(path + '/consensus', json={'labels': labels, 'confidence': 0.9})
        assert result.status_code == 200, result.text
        after_data = candidates(labeler)
        item = next(item for item in after_data['candidates'] if item['id'] == row['id'])
        assert item['consensus'] == 'resolved'
        assert after_data['progress']['confirmed'] >= before['confirmed'], (before, after_data['progress'])


def test_team_set_order_does_not_create_disagreement():
    with client('labeler') as labeler, client('reviewer') as reviewer:
        row = candidates(labeler)['candidates'][-3]
        labels = {**row['proposed_labels'], 'team_set': ['AI팀', 'IT팀']}
        reversed_labels = {**labels, 'team_set': ['IT팀', 'AI팀']}
        path = f"/api/evaluation/candidates/tuning/{row['id']}"
        for api, value in [(labeler, labels), (reviewer, reversed_labels)]:
            result = api.put(path, json={'labels': value, 'confidence': 0.8})
            assert result.status_code == 200, result.text
        item = next(item for item in candidates(labeler)['candidates'] if item['id'] == row['id'])
        assert item['consensus'] == 'agreed', item['consensus']
