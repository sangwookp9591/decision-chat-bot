"""QA-C-01/03/05: errors contain diagnostics only and reject unsafe numbers."""
import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel, field_validator

from jevtriage.auth.core import Principal, get_principal
from jevtriage.config import get_settings
from jevtriage.main import create_app

SAMPLE = 'qa-canary@example.invalid'


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv('DATA_DIR', str(tmp_path))
    get_settings.cache_clear()
    async def session(_token):
        return Principal('qa_boundaries', 'reviewer', ('qa_boundaries-it',),
                         frozenset({'requester', 'reviewer', 'operator'})), 'csrf-ok'
    monkeypatch.setattr('jevtriage.auth.core.session_principal', session)
    app = create_app()
    app.dependency_overrides[get_principal] = lambda: Principal(
        'qa_boundaries', 'reviewer', ('qa_boundaries-it',),
        frozenset({'requester', 'reviewer', 'operator'}))
    # Int64 rejection must happen before any database call.
    async def forbidden(*args, **kwargs):
        raise AssertionError('invalid input reached storage')
    monkeypatch.setattr('jevtriage.policy.router.get_version', forbidden)
    monkeypatch.setattr('jevtriage.graph.api.query.collect', forbidden)
    class ContextBody(BaseModel):
        value: str

        @field_validator('value')
        @classmethod
        def reject(cls, value):
            raise ValueError(value)
    # Exposes Pydantic ctx without relying on a particular product validator.
    @app.post('/test/context')
    def context(body: ContextBody):
        return body
    with TestClient(app, raise_server_exceptions=False) as result:
        result.cookies.set('jev_session', 'qa-session')
        result.cookies.set('jev_csrf', 'csrf-ok')
        result.headers['X-CSRF-Token'] = 'csrf-ok'
        yield result
    get_settings.cache_clear()


@pytest.mark.parametrize('path,body', [
    ('/api/auth/login', {'email': 'qa@example.invalid', 'password': {'source': SAMPLE}}),
    ('/api/policy/validate', {'config': [SAMPLE]}),
    ('/api/requests/missing/reanalyze', {'expected_revision': [SAMPLE]}),
    ('/api/reviews/missing/decision', {'action': SAMPLE}),
    ('/api/tasks/missing/transition', {'to': [SAMPLE], 'expected_status': '초안'}),
])
def test_validation_errors_do_not_echo_input(client, path, body):
    response = client.post(path, json=body, headers={'Idempotency-Key': 'qa-test'})
    assert response.status_code == 422
    assert SAMPLE not in response.text
    assert all(set(error) == {'loc', 'type', 'msg'} for error in response.json()['detail'])


def test_validation_context_does_not_echo_input(client):
    response = client.post('/test/context', json={'value': SAMPLE})
    assert response.status_code == 422
    assert SAMPLE not in response.text
    assert 'ctx' not in response.json()['detail'][0]


@pytest.mark.parametrize('number', ['1e1000', 'NaN', 'Infinity', '-Infinity'])
def test_nonfinite_validation_is_4xx(client, number):
    response = client.post('/api/auth/login',
                           content='{"email":'+number+',"password":"qa-only"}',
                           headers={'Content-Type': 'application/json'})
    assert 400 <= response.status_code < 500


@pytest.mark.parametrize('number', [2**63, -(2**63)-1, 2**80])
@pytest.mark.parametrize('path', ['/api/policy/versions/{}',
                                 '/api/graph/judgment?config_version={}'])
def test_db_integer_range_rejected_before_storage(client, number, path):
    assert client.get(path.format(number)).status_code == 422


@pytest.mark.parametrize('number', ['1e1000', 'NaN', 'Infinity', '-Infinity'])
def test_nonfinite_numbers_rejected_inside_arbitrary_config(client, number):
    response = client.post('/api/policy/validate',
                           content='{"config":{"nested":{"value":'+number+'}}}',
                           headers={'Content-Type': 'application/json'})
    assert 400 <= response.status_code < 500
