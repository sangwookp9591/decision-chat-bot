"""Privileged SIWC endpoints and a loopback-only callback."""
import secrets
from urllib.parse import urlencode, urlsplit

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse

from ildongi.assist import chatgpt_auth as auth
from ildongi.assist.chatgpt_auth import audit
from ildongi.assist.providers import LlmError
from ildongi.auth.core import enforce_csrf, require_roles
from ildongi.config import get_settings

router = APIRouter(tags=['assist'])
COOKIE = 'ildongi_chatgpt_attempt'


def return_url(settings, result, welcome=False):
    parsed = urlsplit(settings.chatgpt_auth_return_url)
    if parsed.scheme != 'http' or parsed.hostname != '127.0.0.1' or parsed.username or parsed.password:
        raise HTTPException(503, 'ChatGPT return URL must be HTTP loopback')
    return settings.chatgpt_auth_return_url + ('&' if parsed.query else '?') + urlencode({'chatgpt': result, **({'chatgpt_welcome': '1'} if welcome else {})})


@router.post('/api/assist/chatgpt/connect', dependencies=[Depends(enforce_csrf)])
async def connect(principal=Depends(require_roles('policy_editor'))):  # noqa: B008
    settings = get_settings()
    return_url(settings, 'ok')
    browser = secrets.token_urlsafe(32)
    async with auth.session_lock(settings):
        url = auth.start(settings, principal, browser)
    response = JSONResponse({'authorize_url': url}, headers={'Cache-Control': 'no-store'})
    response.set_cookie(COOKIE, browser, httponly=True, samesite='lax',
                        max_age=600, path='/auth/callback')
    return response


@router.get('/auth/callback')
async def callback(request: Request):
    settings = get_settings()
    # The exact Host prevents DNS rebinding; peer check rejects non-loopback callers.
    if (request.headers.get('host') != f'127.0.0.1:{settings.chatgpt_auth_redirect_port}'
            or not request.client or request.client.host != '127.0.0.1'):
        raise HTTPException(400, 'Loopback callback required')
    result = 'ok'
    welcome = False
    try:
        params = request.state.chatgpt_callback_params
        async with auth.session_lock(settings):
            pending = auth.consume(params.get('state'), request.cookies.get(COOKIE))
            record = await auth.finish(settings, pending, params)
        await audit(pending['principal'], 'chatgpt.connect',
                    {'plan_usage_granted': auth.PLAN_SCOPE in record['scopes']})
        welcome = record.get('welcome_required', False)
        if auth.PLAN_SCOPE not in record['scopes']:
            result = 'PLAN_USAGE_NOT_GRANTED'
    except LlmError as exc:
        result = exc.code
    except (OSError, ValueError):
        result = 'CONNECTION_FAILED'
    response = RedirectResponse(return_url(settings, result, welcome and result == 'ok'), status_code=303,
        headers={'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer'})
    response.delete_cookie(COOKIE, path='/auth/callback')
    return response


@router.get('/api/assist/chatgpt/status')
async def connection_status(principal=Depends(require_roles('policy_editor', 'operator'))):  # noqa: B008
    settings = get_settings()
    error = None
    if auth.status(settings)['plan_usage_granted']:
        try:
            await auth.access_token(settings)
        except LlmError as exc:
            error = exc.code
    return JSONResponse({**auth.status(settings), **({'connected': False} if error else {}), 'error_code': error},
                        headers={'Cache-Control': 'no-store'})


@router.post('/api/assist/chatgpt/disconnect', dependencies=[Depends(enforce_csrf)])
async def disconnect(principal=Depends(require_roles('policy_editor'))):  # noqa: B008
    revoked = await auth.disconnect(get_settings())
    await audit(principal, 'chatgpt.disconnect', {'remote_revocation_confirmed': revoked})
    return {'connected': False, 'remote_revocation_confirmed': revoked}
