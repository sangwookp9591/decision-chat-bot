"""Single local installation SIWC session; no credentials cross the browser boundary."""
import asyncio
import base64
import fcntl
import hashlib
import json
import os
import secrets
import tempfile
import time
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlencode
from uuid import uuid4

import httpx
import jwt

from ildongi.assist.providers import LlmAuthError, LlmConnectionError, LlmUnavailable
from ildongi.db.audit import append_audit_in_tx
from ildongi.db.tx import write_tx

ISSUER = 'https://auth.openai.com'
AUTHORIZE = ISSUER + '/api/accounts/authorize'
TOKEN = ISSUER + '/api/accounts/oauth/token'
RESOURCE = 'https://api.openai.com/v1'
SCOPE = 'openid profile email offline_access resource.invoke chatgpt.tokens.use.direct'
PLAN_SCOPE = 'chatgpt.tokens.use.direct'
TERMINAL_REFRESH = {'invalid_grant', 'invalid_refresh_token', 'token_expired',
                    'refresh_token_expired', 'refresh_token_invalidated', 'refresh_token_reused'}
_pending = {}


def private_dir(settings):
    directory = settings.data_dir / 'secrets'
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    directory.chmod(0o700)
    return directory


def load(settings, name='chatgpt-credentials.json'):
    path = private_dir(settings) / name
    try:
        with path.open() as file:
            path.chmod(0o600)
            return json.load(file)
    except FileNotFoundError:
        return {}


def save(settings, value, name='chatgpt-credentials.json'):
    """Replace the complete rotating token set atomically; temporary files are 0600."""
    directory = private_dir(settings)
    fd, temporary = tempfile.mkstemp(dir=directory)
    try:
        with os.fdopen(fd, 'w') as file:
            json.dump(value, file, ensure_ascii=False)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, directory / name)
    finally:
        Path(temporary).unlink(missing_ok=True)


@asynccontextmanager
async def session_lock(settings):
    # ponytail: one installation-wide lock; per-session locks if multiple accounts are added.
    fd = os.open(private_dir(settings) / 'chatgpt.lock', os.O_CREAT | os.O_RDWR, 0o600)
    try:
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                await asyncio.sleep(0.05)
        yield
    finally:
        os.close(fd)


def pkce_challenge(verifier):
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')


def start(settings, principal, browser):
    credentials = load(settings)
    registration = load(settings, 'chatgpt-registration.json')
    host = load(settings, 'chatgpt-host.json').get('id')
    if not host:
        host = 'urn:uuid:' + str(uuid4())
        save(settings, {'id': host}, 'chatgpt-host.json')
    state, verifier, nonce = (secrets.token_urlsafe(32) for _ in range(3))
    redirect = f'http://127.0.0.1:{settings.chatgpt_auth_redirect_port}/auth/callback'
    client_id = credentials.get('client_id') or registration.get('client_id')
    # Only one outstanding connection attempt per installation; new attempts invalidate old ones.
    _pending.clear()
    _pending[state] = {'verifier': verifier, 'nonce': nonce, 'redirect': redirect,
                          'client_id': client_id, 'subject': credentials.get('subject') or registration.get('subject'), 'host': host,
                          'principal': principal, 'browser': browser, 'expires': time.time() + 600}
    params = {'client_id': client_id or 'dynamic_agent_client', 'ext_agent_host_id': host,
                  'response_type': 'code', 'redirect_uri': redirect, 'scope': SCOPE, 'resource': RESOURCE,
                  'state': state, 'nonce': nonce, 'code_challenge_method': 'S256',
                  'code_challenge': pkce_challenge(verifier)}
    if client_id:
        # Do not return retained ID tokens to browser JavaScript as URL hints.
        if credentials.get('email') or registration.get('email'):
            params['login_hint'] = credentials.get('email') or registration['email']
        if PLAN_SCOPE not in credentials.get('scopes', []):
            params['prompt'] = 'consent'
    else:
        params['agent_name_hint'] = '일동이'
    return AUTHORIZE + '?' + urlencode(params)


def consume(state, browser):
    pending = _pending.pop(state or '', None)
    if (not pending or pending['expires'] <= time.time() or not browser
            or not secrets.compare_digest(pending['browser'], browser)):
        raise LlmAuthError('STATE_INVALID')
    return pending


async def verify_identity(client, token, client_id, nonce):
    try:
        response = await client.get(ISSUER + '/.well-known/jwks.json')
        response.raise_for_status()
        header = jwt.get_unverified_header(token)
        key = next(k for k in response.json()['keys']
                   if k['kid'] == header.get('kid') and k.get('alg') == 'RS256')
        claims = jwt.decode(token, jwt.PyJWK.from_dict(key).key, algorithms=['RS256'],
                            issuer=ISSUER, audience=client_id, leeway=5,
                            options={'require': ['sub', 'exp', 'iat', 'nonce']})
        if not isinstance(claims['sub'], str) or not claims['sub'] or claims['nonce'] != nonce:
            raise ValueError()
        return claims
    except (jwt.PyJWTError, ValueError, KeyError, StopIteration, TypeError):
        raise LlmAuthError('IDENTITY_INVALID') from None


def token_record(tokens, previous):
    if (not isinstance(tokens.get('access_token'), str) or not tokens['access_token']
            or not isinstance(tokens.get('refresh_token'), str) or not tokens['refresh_token']
            or tokens.get('token_type', '').lower() != 'bearer'
            or not isinstance(tokens.get('expires_in'), (int, float)) or tokens['expires_in'] <= 0
            or not isinstance(tokens.get('scope'), str)):
        raise LlmAuthError('TOKEN_INVALID')
    return {**previous, 'access_token': tokens['access_token'],
            'refresh_token': tokens['refresh_token'], 'scopes': tokens['scope'].split(),
            'expires_at': time.time() + tokens['expires_in'],
            'earliest_refresh_at': tokens.get('earliest_refresh_at'),
            'id_token': tokens.get('id_token', previous.get('id_token'))}


async def finish(settings, pending, params, *, client=None):
    if params.get('error'):
        raise LlmAuthError('CONSENT_DENIED')
    client_id = params.get('client_id') or pending['client_id']
    if (not client_id or client_id == 'dynamic_agent_client'
            or (pending['client_id'] and client_id != pending['client_id'])):
        raise LlmAuthError('CLIENT_INVALID')
    if not params.get('code'):
        raise LlmAuthError('CODE_MISSING')
    http = client or httpx.AsyncClient(timeout=15)
    try:
        response = await http.post(TOKEN, data={'grant_type': 'authorization_code',
                'client_id': client_id, 'code': params['code'], 'code_verifier': pending['verifier'],
                'redirect_uri': pending['redirect'], 'resource': RESOURCE})
        if response.status_code != 200:
            error = response.json().get('error')
            code = error.get('code') if isinstance(error, dict) else error
            if code == 'invalid_grant' and not pending['client_id']:
                # A new code must reuse the issued registration, even if the first code expired.
                save(settings, {'client_id': client_id}, 'chatgpt-registration.json')
            raise LlmAuthError('CODE_EXCHANGE_FAILED')
        tokens = response.json()
        identity = await verify_identity(http, tokens['id_token'], client_id, pending['nonce'])
        if pending['subject'] and identity['sub'] != pending['subject']:
            raise LlmAuthError('IDENTITY_MISMATCH')
        principal = pending['principal']
        if not isinstance(tokens.get('scope'), str):
            raise LlmAuthError('TOKEN_INVALID')
        record = {'client_id': client_id, 'subject': identity['sub'],
                  'email': identity.get('email'), 'issuer': ISSUER, 'ext_agent_host_id': pending['host'],
                  'connected_by': principal.user_id, 'connected_tenant': principal.tenant_id,
                  'id_token': tokens['id_token'], 'scopes': tokens['scope'].split(),
                  'expires_at': identity['exp']}
        if PLAN_SCOPE in record['scopes']:
            record = token_record(tokens, record)
        else:
            # Identity-only consent need not return access/refresh credentials. Keep the sign-in.
            record.update({key: tokens[key] for key in ('access_token', 'refresh_token')
                           if isinstance(tokens.get(key), str)})
        registration = load(settings, 'chatgpt-registration.json')
        plan_granted = PLAN_SCOPE in record['scopes']
        welcome = plan_granted and not registration.get('plan_welcome_sent', False)
        save(settings, record)
        save(settings, {**{k: record[k] for k in ('client_id', 'subject', 'email')},
                        'plan_welcome_sent': registration.get('plan_welcome_sent', False) or plan_granted},
             'chatgpt-registration.json')
        return {**record, 'welcome_required': welcome}
    except (KeyError, ValueError, TypeError):
        raise LlmAuthError('TOKEN_INVALID') from None
    except httpx.HTTPError:
        raise LlmConnectionError() from None
    finally:
        if client is None:
            await http.aclose()


async def access_token(settings, *, client=None):
    async with session_lock(settings):
        record = load(settings)
        if not record:
            raise LlmUnavailable('CHATGPT_DISCONNECTED')
        if PLAN_SCOPE not in record.get('scopes', []):
            raise LlmUnavailable('PLAN_USAGE_NOT_GRANTED')
        if not record.get('access_token'):
            raise LlmUnavailable('CHATGPT_DISCONNECTED')
        if record['expires_at'] > time.time() + 60:
            return record['access_token']
        earliest = record.get('earliest_refresh_at')
        if isinstance(earliest, str):
            from datetime import datetime
            earliest = datetime.fromisoformat(earliest).timestamp()
        if earliest and earliest > time.time():
            if record['expires_at'] > time.time():
                return record['access_token']
            raise LlmUnavailable('REFRESH_NOT_YET_ALLOWED')
        http = client or httpx.AsyncClient(timeout=15)
        try:
            response = await http.post(TOKEN, data={'grant_type': 'refresh_token',
                'client_id': record['client_id'], 'refresh_token': record['refresh_token'], 'resource': RESOURCE})
            if response.status_code != 200:
                try:
                    error = response.json().get('error')
                    code = error.get('code') if isinstance(error, dict) else error
                except ValueError:
                    code = None
                if code in TERMINAL_REFRESH:
                    (private_dir(settings) / 'chatgpt-credentials.json').unlink(missing_ok=True)
                    raise LlmAuthError('CHATGPT_RECONNECT_REQUIRED')
                raise LlmConnectionError('CHATGPT_REFRESH_FAILED')
            updated = token_record(response.json(), record)
            save(settings, updated)
            if PLAN_SCOPE not in updated['scopes']:
                raise LlmUnavailable('PLAN_USAGE_NOT_GRANTED')
            return updated['access_token']
        except httpx.HTTPError:
            raise LlmConnectionError() from None
        finally:
            if client is None:
                await http.aclose()


def status(settings):
    record = load(settings)
    return {'connected': bool(record.get('access_token') or record.get('id_token')) and record.get('expires_at', 0) > time.time(), 'email': record.get('email'),
                'plan_usage_granted': PLAN_SCOPE in record.get('scopes', []),
                'expires_at': record.get('expires_at'),
                'client_registered': bool(record.get('client_id') or load(settings, 'chatgpt-registration.json')),
                'connected_by': record.get('connected_by'), 'connected_tenant': record.get('connected_tenant')}


async def disconnect(settings, *, client=None):
    async with session_lock(settings):
        _pending.clear()
        record = load(settings)
        revoked = not bool(record.get('refresh_token'))
        http = client or httpx.AsyncClient(timeout=10)
        try:
            if record.get('refresh_token'):
                discovery = await http.get(ISSUER + '/.well-known/openid-configuration')
                discovery.raise_for_status()
                endpoint = discovery.json()['revocation_endpoint']
                if not endpoint.startswith(ISSUER + '/'):
                    raise ValueError()
                for attempt in range(2):
                    try:
                        result = await http.post(endpoint, data={'token': record['refresh_token'],
                            'token_type_hint': 'refresh_token', 'client_id': record['client_id']})
                        revoked = result.status_code == 200
                        if revoked or result.status_code < 500:
                            break
                    except httpx.HTTPError:
                        pass
                    if attempt == 0:
                        await asyncio.sleep(0.25)
        except (httpx.HTTPError, ValueError, KeyError):
            pass
        finally:
            (private_dir(settings) / 'chatgpt-credentials.json').unlink(missing_ok=True)
            if client is None:
                await http.aclose()
        return revoked


async def audit(principal, action, after):
    async def record(tx):
        await append_audit_in_tx(tx, principal.tenant_id, principal.user_id, action,
            'chatgpt_connection', 'local-installation', None, after, 'ChatGPT 구독 연결 관리')
    await write_tx(principal.tenant_id, record)
