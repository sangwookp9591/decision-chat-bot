"""SIWC security and wire contracts with real JWT signatures and MockTransport only."""
import asyncio
import json
import stat
import time
from unittest.mock import AsyncMock
from urllib.parse import parse_qs, urlsplit

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from ildongi.assist import chatgpt_api
from ildongi.assist import chatgpt_auth as auth
from ildongi.assist.adapters.chatgpt import Provider
from ildongi.assist.prompts import Ping
from ildongi.assist.providers import (
    LlmAuthError,
    LlmConnectionError,
    LlmInvalidOutput,
    LlmProviderError,
    LlmRequest,
    LlmUnavailable,
)
from ildongi.assist.service import provider_status, safe_response
from ildongi.auth.core import enforce_csrf, get_principal
from ildongi.auth.types import Principal
from ildongi.config import Settings
from ildongi.main import create_app

PRINCIPAL = Principal('test-tenant', 'editor', (), frozenset({'policy_editor'}))
REQUEST = LlmRequest('ping', 'Return JSON', '{}', Ping, 500)


@pytest.fixture
def settings(tmp_path):
    return Settings(data_dir=tmp_path, llm_mode='live', redis_url=None)


@pytest.fixture
def signing():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key()))
    return key, {**jwk, 'kid': 'test-key', 'alg': 'RS256'}


def attempt(settings, browser='browser'):
    url = auth.start(settings, PRINCIPAL, browser)
    params = {k: v[0] for k, v in parse_qs(urlsplit(url).query).items()}
    return params, auth.consume(params['state'], browser)


def tokens(signing, pending, *, scope=auth.SCOPE, **claims):
    key, _ = signing
    identity = {'iss': auth.ISSUER, 'aud': 'oaiapp_test', 'sub': 'subject', 'email': 'test@example.com',
                'iat': int(time.time()), 'exp': int(time.time()) + 3600, 'nonce': pending['nonce'], **claims}
    return {'access_token': 'PRIVATE_ACCESS', 'refresh_token': 'PRIVATE_REFRESH', 'token_type': 'Bearer',
                'id_token': jwt.encode(identity, key, algorithm='RS256', headers={'kid': 'test-key'}),
                'expires_in': 3600, 'scope': scope}


def transport(signing, record):
    async def respond(request):
        if request.url.path.endswith('jwks.json'):
            return httpx.Response(200, json={'keys': [signing[1]]})
        assert request.url == auth.TOKEN
        form = parse_qs(request.content.decode())
        assert form['resource'] == [auth.RESOURCE]
        assert form['client_id'] == ['oaiapp_test']
        assert 'client_secret' not in form
        return httpx.Response(200, json=record)
    return httpx.AsyncClient(transport=httpx.MockTransport(respond))


def saved(settings, **changes):
    record = {'access_token': 'PRIVATE_ACCESS', 'refresh_token': 'PRIVATE_REFRESH',
              'id_token': 'PRIVATE_ID', 'client_id': 'oaiapp_test', 'scopes': auth.SCOPE.split(),
              'expires_at': time.time() + 3600, **changes}
    auth.save(settings, record)
    return record


def test_pkce_state_cookie_expiry_reuse_and_host_id(settings):
    assert auth.pkce_challenge('dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk') == 'E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM'
    query, pending = attempt(settings)
    assert query['client_id'] == 'dynamic_agent_client'
    assert query['agent_name_hint'] == '일동이'
    assert query['ext_agent_host_id'].startswith('urn:uuid:')
    assert query['redirect_uri'] == 'http://127.0.0.1:8000/auth/callback'
    assert query['code_challenge'] == auth.pkce_challenge(pending['verifier'])
    assert query['scope'] == auth.SCOPE and query['nonce'] == pending['nonce']
    with pytest.raises(LlmAuthError):
        auth.consume(query['state'], 'browser')
    later = auth.start(settings, PRINCIPAL, 'browser')
    later_query = parse_qs(urlsplit(later).query)
    assert later_query['ext_agent_host_id'] == [query['ext_agent_host_id']]
    auth._pending[later_query['state'][0]]['expires'] = time.time() - 1
    with pytest.raises(LlmAuthError):
        auth.consume(later_query['state'][0], 'browser')
    url = auth.start(settings, PRINCIPAL, 'browser')
    with pytest.raises(LlmAuthError):
        auth.consume(parse_qs(urlsplit(url).query)['state'][0], 'another-browser')
    with pytest.raises(LlmAuthError):
        auth.consume('unknown', 'browser')


@pytest.mark.asyncio
@pytest.mark.parametrize('scope', [auth.SCOPE, 'openid profile email'])
async def test_code_exchange_identity_permissions_and_no_secret_exposure(settings, signing, scope):
    query, pending = attempt(settings)
    record = tokens(signing, pending, scope=scope)
    async with transport(signing, record) as client:
        await auth.finish(settings, pending, {'code': 'code', 'client_id': 'oaiapp_test'}, client=client)
    state = auth.status(settings)
    assert state['connected'] and state['client_registered']
    assert state['email'] == 'test@example.com' and state['connected_by'] == 'editor'
    assert state['plan_usage_granted'] == (auth.PLAN_SCOPE in scope.split())
    assert stat.S_IMODE((settings.data_dir / 'secrets').stat().st_mode) == 0o700
    assert stat.S_IMODE((settings.data_dir / 'secrets/chatgpt-credentials.json').stat().st_mode) == 0o600
    visible = json.dumps([state, provider_status(settings), safe_response(record['access_token'], settings)])
    assert all(secret not in visible for secret in (record['access_token'], record['refresh_token'], record['id_token']))
    url = auth.start(settings, PRINCIPAL, 'browser')
    query = parse_qs(urlsplit(url).query)
    assert query['client_id'] == ['oaiapp_test'] and 'agent_name_hint' not in query
    assert 'id_token_hint' not in query
    if auth.PLAN_SCOPE not in scope.split():
        with pytest.raises(LlmUnavailable, match='PLAN_USAGE_NOT_GRANTED'):
            await auth.access_token(settings)


@pytest.mark.asyncio
@pytest.mark.parametrize('claims', [{'iss': 'https://evil.invalid'}, {'aud': 'other-client'},
    {'nonce': 'wrong'}, {'exp': int(time.time()) - 10}, {'sub': ''}])
async def test_invalid_identity_never_persisted(settings, signing, claims):
    _, pending = attempt(settings)
    record = tokens(signing, pending, **claims)
    async with transport(signing, record) as client:
        with pytest.raises(LlmAuthError):
            await auth.finish(settings, pending, {'code': 'code', 'client_id': 'oaiapp_test'}, client=client)
    assert not auth.load(settings)


@pytest.mark.asyncio
async def test_invalid_signature_client_and_callback_scope_cannot_grant_usage(settings, signing):
    _, pending = attempt(settings)
    record = tokens(signing, pending, scope='openid email')
    impostor = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    record['id_token'] = jwt.encode({'sub': 'subject'}, impostor, algorithm='RS256', headers={'kid': 'test-key'})
    async with transport(signing, record) as client:
        with pytest.raises(LlmAuthError, match='IDENTITY_INVALID'):
            await auth.finish(settings, pending, {'code': 'code', 'client_id': 'oaiapp_test'}, client=client)
    saved(settings)
    auth.save(settings, {'client_id': 'oaiapp_test', 'subject': 'subject'}, 'chatgpt-registration.json')
    _, pending = attempt(settings)
    with pytest.raises(LlmAuthError, match='CLIENT_INVALID'):
        await auth.finish(settings, pending, {'code': 'code', 'client_id': 'oaiapp_other'})
    with pytest.raises(LlmAuthError):
        await auth.finish(settings, {**pending, 'client_id': None}, {'code': 'code'})


@pytest.mark.asyncio
async def test_refresh_rotates_as_one_record_and_serializes(settings):
    old = saved(settings, expires_at=0)
    calls = 0
    async def respond(request):
        nonlocal calls
        calls += 1
        form = parse_qs(request.content.decode())
        assert form == {'grant_type': ['refresh_token'], 'client_id': ['oaiapp_test'],
                        'refresh_token': ['PRIVATE_REFRESH'], 'resource': [auth.RESOURCE]}
        await asyncio.sleep(.02)
        return httpx.Response(200, json={'access_token': 'NEW_ACCESS', 'refresh_token': 'NEW_REFRESH',
                    'expires_in': 3600, 'token_type': 'Bearer', 'scope': 'openid ' + auth.PLAN_SCOPE})
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        values = await asyncio.gather(auth.access_token(settings, client=client), auth.access_token(settings, client=client))
    assert calls == 1 and values == ['NEW_ACCESS', 'NEW_ACCESS']
    current = auth.load(settings)
    assert current['refresh_token'] == 'NEW_REFRESH' and current['expires_at'] > time.time()
    assert current['scopes'] == ['openid', auth.PLAN_SCOPE]
    assert current['id_token'] == old['id_token']
    assert stat.S_IMODE((settings.data_dir / 'secrets/chatgpt-credentials.json').stat().st_mode) == 0o600


def test_atomic_write_failure_keeps_previous_tokens(settings, monkeypatch):
    old = saved(settings)
    def fail(*args):
        raise OSError('disk failure')
    monkeypatch.setattr(auth.os, 'replace', fail)
    with pytest.raises(OSError):
        auth.save(settings, {**old, 'refresh_token': 'NEW_REFRESH'})
    assert auth.load(settings) == old
    assert sorted(p.name for p in (settings.data_dir / 'secrets').iterdir()) == ['chatgpt-credentials.json']


@pytest.mark.asyncio
@pytest.mark.parametrize('code,terminal', [('invalid_grant', True), ('refresh_token_reused', True), ('server_error', False)])
async def test_refresh_terminal_errors_only_clear_credentials(settings, code, terminal):
    saved(settings, expires_at=0)
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(400, json={'error': code}))) as client:
        with pytest.raises(LlmAuthError if terminal else LlmConnectionError):
            await auth.access_token(settings, client=client)
    assert bool(auth.load(settings)) != terminal


@pytest.mark.asyncio
async def test_disconnect_revokes_refresh_and_keeps_registration_host(settings):
    saved(settings)
    auth.save(settings, {'client_id': 'oaiapp_test'}, 'chatgpt-registration.json')
    auth.save(settings, {'id': 'urn:uuid:test'}, 'chatgpt-host.json')
    def respond(request):
        if request.method == 'GET':
            return httpx.Response(200, json={'revocation_endpoint': auth.ISSUER + '/api/accounts/oauth/revoke'})
        assert parse_qs(request.content.decode()) == {'token': ['PRIVATE_REFRESH'],
            'token_type_hint': ['refresh_token'], 'client_id': ['oaiapp_test']}
        return httpx.Response(200)
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        assert await auth.disconnect(settings, client=client)
    assert not auth.load(settings) and auth.status(settings)['client_registered']
    assert auth.load(settings, 'chatgpt-host.json')['id'] == 'urn:uuid:test'


def sse(events):
    return ''.join('data: ' + json.dumps(event) + '\n\n' for event in events)


@pytest.mark.asyncio
@pytest.mark.parametrize('kind,expected', [('completed', None), ('delta', LlmInvalidOutput),
    ('incomplete', LlmInvalidOutput), ('limit', LlmProviderError), ('unavailable', LlmProviderError)])
async def test_responses_only_completed_success_and_usage_errors(settings, kind, expected):
    saved(settings)
    output = {'status': 'completed', 'model': 'account-model',
              'output': [{'content': [{'type': 'output_text', 'text': '{"ok":true}'}]}],
              'usage': {'input_tokens': 3, 'output_tokens': 4}}
    events = [{'type': 'response.output_text.delta', 'delta': '{"ok":true}'}]
    if kind == 'completed':
        events.append({'type': 'response.completed', 'response': output})
    if kind == 'incomplete':
        events.append({'type': 'response.incomplete', 'response': output})
    if kind in ('limit', 'unavailable'):
        events.append({'type': 'response.failed', 'response': {'error': {'code':
            'subscription_sharing_usage_limit_exceeded' if kind == 'limit' else 'subscription_sharing_usage_unavailable',
            'message': 'PRIVATE_ACCESS'}}})
    def respond(request):
        assert request.url == auth.RESOURCE + '/responses'
        assert request.headers['authorization'] == 'Bearer PRIVATE_ACCESS'
        body = json.loads(request.content)
        assert body['stream'] is True and body['store'] is False and isinstance(body['input'], list)
        assert set(body) == {'model', 'instructions', 'input', 'store', 'stream'}
        return httpx.Response(200, text=sse(events), headers={'content-type': 'text/event-stream'})
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        provider = Provider(settings, client=client)
        if expected:
            with pytest.raises(expected) as caught:
                await provider.generate(REQUEST, model='account-model', timeout=3)
            assert 'PRIVATE_ACCESS' not in str(caught.value)
            if kind in ('limit', 'unavailable'):
                assert caught.value.code == ('CHATGPT_USAGE_LIMIT' if kind == 'limit' else 'CHATGPT_USAGE_UNAVAILABLE')
        else:
            result = await provider.generate(REQUEST, model='account-model', timeout=3)
            assert result.parsed.ok and result.input_tokens == 3 and result.output_tokens == 4


@pytest.mark.asyncio
async def test_models_use_visibility_slug_and_preserve_order(settings):
    saved(settings)
    def respond(request):
        assert request.url == auth.RESOURCE + '/models'
        return httpx.Response(200, json={'models': [{'slug': 'b', 'display_name': 'B', 'visibility': 'list'},
            {'slug': 'hidden', 'display_name': 'Hidden', 'visibility': 'hide'},
            {'slug': 'a', 'display_name': 'A', 'visibility': 'list'}]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        assert [(m.id, m.label) for m in await Provider(settings, client=client).list_models(timeout=3)] == [('b', 'B'), ('a', 'A')]


@pytest.mark.asyncio
async def test_privileged_api_csrf_host_cookie_callback_and_safe_status(settings, monkeypatch):
    monkeypatch.setattr(chatgpt_api, 'get_settings', lambda: settings)
    monkeypatch.setattr(chatgpt_api, 'audit', AsyncMock())
    app = create_app()
    app.dependency_overrides[get_principal] = lambda: PRINCIPAL
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://127.0.0.1:8000') as client:
        assert (await client.post('/api/assist/chatgpt/connect')).status_code == 403
        app.dependency_overrides[enforce_csrf] = lambda: None
        result = await client.post('/api/assist/chatgpt/connect')
        assert result.status_code == 200 and 'HttpOnly' in result.headers['set-cookie']
        state = parse_qs(urlsplit(result.json()['authorize_url']).query)['state'][0]
        assert (await client.get('/auth/callback?state=' + state, headers={'Host': 'localhost:8000'})).status_code == 400
        async def finished(config, pending, params):
            assert pending['principal'] == PRINCIPAL
            assert params['code'] == 'PRIVATE_CODE'
            return saved(config)
        monkeypatch.setattr(auth, 'finish', finished)
        response = await client.get('/auth/callback', params={'state': state, 'code': 'PRIVATE_CODE', 'client_id': 'oaiapp_test'})
        assert response.status_code == 303 and 'chatgpt=ok' in response.headers['location']
        assert (await client.get('/auth/callback', params={'state': state, 'code': 'PRIVATE_CODE'})).headers['location'].endswith('chatgpt=STATE_INVALID')
        response = await client.get('/api/assist/chatgpt/status')
        assert response.json()['connected'] and 'PRIVATE_' not in response.text
        app.dependency_overrides[get_principal] = lambda: Principal('t', 'u', (), frozenset({'operator'}))
        assert (await client.get('/api/assist/chatgpt/status')).status_code == 200
        assert (await client.post('/api/assist/chatgpt/connect')).status_code == 403
        assert (await client.post('/api/assist/chatgpt/disconnect')).status_code == 403
        app.dependency_overrides[get_principal] = lambda: Principal('t', 'u', (), frozenset({'requester'}))
        assert (await client.get('/api/assist/chatgpt/status')).status_code == 403
    chatgpt_api.audit.assert_awaited_once()

@pytest.mark.asyncio
async def test_new_registration_denied_consent_without_client_id(settings):
    _, pending = attempt(settings)
    with pytest.raises(LlmAuthError, match='CONSENT_DENIED'):
        await auth.finish(settings, pending, {'error': 'access_denied'})


@pytest.mark.asyncio
async def test_invalid_grant_retains_issued_client_for_next_attempt(settings):
    _, pending = attempt(settings)
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(400, json={'error': 'invalid_grant'}))) as client:
        with pytest.raises(LlmAuthError):
            await auth.finish(settings, pending, {'code': 'expired-code', 'client_id': 'oaiapp_test'}, client=client)
    query = parse_qs(urlsplit(auth.start(settings, PRINCIPAL, 'browser')).query)
    assert query['client_id'] == ['oaiapp_test'] and 'agent_name_hint' not in query
    assert not auth.status(settings)['connected']

@pytest.mark.asyncio
async def test_identity_only_grant_without_refresh_retains_signin(settings, signing):
    _, pending = attempt(settings)
    record = tokens(signing, pending, scope='openid profile email')
    record.pop('access_token')
    record.pop('refresh_token')
    async with transport(signing, record) as client:
        await auth.finish(settings, pending, {'code': 'code', 'client_id': 'oaiapp_test'}, client=client)
    assert auth.status(settings)['connected'] and not auth.status(settings)['plan_usage_granted']
    with pytest.raises(LlmUnavailable, match='PLAN_USAGE_NOT_GRANTED'):
        await auth.access_token(settings)

@pytest.mark.asyncio
async def test_welcome_is_first_plan_grant_even_after_identity_only_signin(settings, signing):
    for scope, welcome in [('openid email', False), (auth.SCOPE, True), (auth.SCOPE, False)]:
        _, pending = attempt(settings)
        async with transport(signing, tokens(signing, pending, scope=scope)) as client:
            record = await auth.finish(settings, pending, {'code': 'code', 'client_id': 'oaiapp_test'}, client=client)
        assert record.get('welcome_required') is welcome

@pytest.mark.asyncio
async def test_failed_refresh_reports_disconnected_but_preserves_temporary_credentials(settings, monkeypatch):
    saved(settings, expires_at=time.time() + 30)
    monkeypatch.setattr(chatgpt_api, 'get_settings', lambda: settings)
    monkeypatch.setattr(auth, 'access_token', AsyncMock(side_effect=LlmConnectionError('CHATGPT_REFRESH_FAILED')))
    response = await chatgpt_api.connection_status(PRINCIPAL)
    body = json.loads(response.body)
    assert not body['connected'] and body['error_code'] == 'CHATGPT_REFRESH_FAILED'
    assert auth.load(settings)['refresh_token'] == 'PRIVATE_REFRESH'
