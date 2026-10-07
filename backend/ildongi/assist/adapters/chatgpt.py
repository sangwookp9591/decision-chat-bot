"""SIWC public Responses HTTP/SSE route; JSON instructions plus local validation."""
import json
import time

import httpx

from ildongi.assist.chatgpt_auth import RESOURCE, access_token
from ildongi.assist.prompts import validate_output, wrap_data
from ildongi.assist.providers import (
    LlmConnectionError,
    LlmInvalidOutput,
    LlmProviderError,
    LlmRefused,
    LlmResult,
    LlmTimeout,
    ModelInfo,
    status_error,
)

ERRORS = {'subscription_sharing_usage_limit_exceeded': 'CHATGPT_USAGE_LIMIT',
          'subscription_sharing_usage_unavailable': 'CHATGPT_USAGE_UNAVAILABLE',
          'subscription_sharing_user_not_eligible': 'CHATGPT_NOT_ELIGIBLE'}


def response_error(body, status=None):
    error = body.get('error', {}) if isinstance(body, dict) else {}
    code = error.get('code') if isinstance(error, dict) else None
    if code in ERRORS:
        return LlmProviderError(ERRORS[code], status=status)
    return status_error(status) if status else LlmProviderError()


async def completed_response(response):
    """Consume SSE frames, including multi-line data, and require the terminal success event."""
    data, completed = [], None
    async for line in response.aiter_lines():
        if line.startswith('data:'):
            data.append(line[5:].lstrip())
        elif not line and data:
            raw = '\n'.join(data)
            data = []
            if raw == '[DONE]':
                continue
            try:
                event = json.loads(raw)
            except ValueError:
                raise LlmInvalidOutput() from None
            kind = event.get('type')
            if kind == 'response.failed':
                raise response_error(event.get('response', {}))
            if kind == 'error':
                raise response_error({'error': event.get('error', event)})
            if kind == 'response.incomplete':
                raise LlmInvalidOutput()
            if kind == 'response.refusal.delta':
                raise LlmRefused()
            if kind == 'response.completed':
                completed = event.get('response')
    if not completed or completed.get('status') != 'completed':
        raise LlmInvalidOutput()
    return completed


class Provider:
    name = 'chatgpt'

    def __init__(self, settings, *, client=None):
        self.settings, self.client = settings, client

    async def list_models(self, *, timeout):
        http = self.client or httpx.AsyncClient(timeout=timeout)
        try:
            token = await access_token(self.settings, client=http)
            response = await http.get(RESOURCE + '/models', headers={'Authorization': 'Bearer ' + token}, timeout=timeout)
            if response.status_code != 200:
                raise response_error(response.json(), response.status_code)
            return [ModelInfo(id=m['slug'], label=m['display_name']) for m in response.json()['models']
                    if m.get('visibility') == 'list']
        except httpx.TimeoutException:
            raise LlmTimeout() from None
        except httpx.HTTPError:
            raise LlmConnectionError() from None
        except (ValueError, KeyError, TypeError):
            raise LlmInvalidOutput() from None
        finally:
            if self.client is None:
                await http.aclose()

    async def generate(self, request, *, model, timeout):
        started = time.monotonic()
        http = self.client or httpx.AsyncClient(timeout=timeout)
        try:
            token = await access_token(self.settings, client=http)
            schema = json.dumps(request.output_type.model_json_schema(), ensure_ascii=False)
            async with http.stream('POST', RESOURCE + '/responses', timeout=timeout,
                headers={'Authorization': 'Bearer ' + token}, json={
                    'model': model, 'instructions': request.system + '\nReturn only JSON matching: ' + schema,
                    'input': [{'role': 'user', 'content': wrap_data(request.data)}],
                    'store': False, 'stream': True}) as response:
                if response.status_code != 200:
                    await response.aread()
                    try:
                        body = response.json()
                    except ValueError:
                        body = {}
                    raise response_error(body, response.status_code)
                result = await completed_response(response)
            parts = [part for item in result.get('output', []) for part in item.get('content', [])]
            if any(p.get('type') == 'refusal' for p in parts):
                raise LlmRefused()
            text = ''.join(p.get('text', '') for p in parts if p.get('type') == 'output_text')
            parsed = validate_output(request.output_type, request.output_type.model_validate_json(text))
            usage = result.get('usage') or {}
            return LlmResult(parsed, self.name, result.get('model', model), usage.get('input_tokens', 0),
                             usage.get('output_tokens', 0), round((time.monotonic() - started) * 1000))
        except httpx.TimeoutException:
            raise LlmTimeout() from None
        except httpx.HTTPError:
            raise LlmConnectionError() from None
        except (ValueError, KeyError, TypeError):
            raise LlmInvalidOutput() from None
        finally:
            if self.client is None:
                await http.aclose()
