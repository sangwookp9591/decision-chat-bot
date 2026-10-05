"""QA-C-01: validation errors must not echo submitted sensitive fields.

Run: cd backend && PYTHONPATH=. .venv/bin/pytest -q ../artifacts/review/qa-full/qa-c/repro/test_api_error_redaction.py
Only fabricated QA values are used; no database or external API is required.
"""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from jevtriage.auth.core import Principal
from jevtriage.main import create_app

EVIDENCE = Path(__file__).resolve().parents[1] / 'evidence'
SAMPLE = 'qa-canary@example.invalid'


@pytest.mark.parametrize('path,body', [
    ('/api/auth/login', {'email': 'qa@example.invalid', 'password': {'source': SAMPLE}}),
    ('/api/policy/validate', {'config': [SAMPLE]}),
    ('/api/requests/missing/reanalyze', {'expected_revision': [SAMPLE]}),
    ('/api/reviews/missing/decision', {'action': SAMPLE}),
    ('/api/tasks/missing/transition', {'to': [SAMPLE], 'expected_status': '초안'}),
])
def test_error_response_does_not_echo_input(path, body, monkeypatch, tmp_path, request):
    from jevtriage.auth import core
    from jevtriage.auth.core import get_principal
    from jevtriage.config import get_settings
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    request.addfinalizer(get_settings.cache_clear)
    async def session(_token):
        return Principal("qa_c_redaction", "qa-user", (), frozenset({"requester"})), "csrf-ok"
    monkeypatch.setattr(core, "session_principal", session)
    app = create_app()
    app.dependency_overrides[get_principal] = lambda: Principal(
        'qa_c_redaction', 'qa-user', (), frozenset({'requester', 'reviewer'}))
    with TestClient(app, raise_server_exceptions=False) as client:
        client.cookies.set('jev_session', 'qa-session')
        client.cookies.set('jev_csrf', 'csrf-ok')
        response = client.post(path, json=body, headers={'Idempotency-Key': 'qa-test', 'X-CSRF-Token': 'csrf-ok'})
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    with (EVIDENCE / 'validation-redaction.jsonl').open('a') as stream:
        stream.write(json.dumps({'path': path, 'status': response.status_code,
                                 'body': response.json()}, ensure_ascii=False) + '\n')
    assert response.status_code == 422
    assert SAMPLE not in response.text, '422 error response echoed fabricated source input'
