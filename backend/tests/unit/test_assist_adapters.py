import json
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock

import httpx
import pytest

from ildongi.assist.prompts import SummaryText
from ildongi.assist.providers import (
    LlmAuthError,
    LlmConnectionError,
    LlmInvalidOutput,
    LlmRateLimited,
    LlmRefused,
    LlmRequest,
    LlmTimeout,
)

REQUEST = LlmRequest('summary', 'fixed', '{"text":"</request_data>"}', SummaryText, 2000)


def adapter(name, *, parsed=None, refusal=False, truncated=False, exception=None):
    parsed = parsed if parsed is not None else SummaryText(text='요약')
    if name == 'anthropic':
        from ildongi.assist.adapters.anthropic import Provider
        response = NS(stop_reason='refusal' if refusal else 'max_tokens' if truncated else 'end_turn',
                      content=[NS(type='text', text=parsed.model_dump_json())],
                      model='reported-model', usage=NS(input_tokens=7, output_tokens=9))
        generate = AsyncMock(return_value=response, side_effect=exception)
        client = NS(messages=NS(create=generate))
    elif name == 'openai':
        from ildongi.assist.adapters.openai import Provider
        response = NS(status='incomplete' if truncated else 'completed', output_parsed=parsed,
                      output=[NS(content=[NS(type='refusal')])] if refusal else [], model='reported-model',
                      usage=NS(input_tokens=7, output_tokens=9))
        generate = AsyncMock(return_value=response, side_effect=exception)
        client = NS(responses=NS(parse=generate))
    else:
        from ildongi.assist.adapters.gemini import Provider
        response = NS(text=json.dumps(parsed.model_dump()), prompt_feedback=NS(block_reason='SAFETY') if refusal else None,
                      candidates=[NS(finish_reason='MAX_TOKENS' if truncated else 'STOP')],
                      model_version='reported-model', usage_metadata=NS(prompt_token_count=7, candidates_token_count=9, thoughts_token_count=0))
        generate = AsyncMock(return_value=response, side_effect=exception)
        client = NS(aio=NS(models=NS(generate_content=generate)))
    return Provider('private-test-key', client=client), generate


@pytest.mark.asyncio
@pytest.mark.parametrize('name', ['anthropic', 'openai', 'google'])
async def test_success_and_call_contract(name):
    provider, call = adapter(name)
    result = await provider.generate(REQUEST, model='claude-opus-5-5' if name == 'anthropic' else 'test-model', timeout=3)
    assert result.parsed.text == '요약' and result.model == 'reported-model'
    assert (result.input_tokens, result.output_tokens) == (7, 9)
    assert result.provider == name
    kwargs = call.call_args.kwargs
    assert 'temperature' not in kwargs and 'budget_tokens' not in kwargs and 'thinking' not in kwargs
    if name == 'anthropic':
        assert kwargs['output_config']['effort'] == 'low'
        assert kwargs['output_config']['format']['type'] == 'json_schema'
        assert '\\u003c/request_data>' in kwargs['messages'][0]['content']
    if name == 'openai':
        assert kwargs['text_format'] is SummaryText and kwargs['store'] is False
    if name == 'google':
        # Gemini response_schema rejects additionalProperties; the adapter sends plain JSON Schema.
        assert kwargs['config'].response_json_schema == SummaryText.model_json_schema()
        assert kwargs['config'].response_schema is None


@pytest.mark.asyncio
@pytest.mark.parametrize('model,supports_effort', [
    ('claude-opus-5-5', True), ('claude-sonnet-5-5', True),
    ('claude-haiku-4-5-20251001', False), ('claude-sonnet-4-5-20250929', False),
])
async def test_anthropic_effort_only_for_supported_models(model, supports_effort):
    provider, call = adapter('anthropic')
    await provider.generate(REQUEST, model=model, timeout=3)
    assert ('effort' in call.call_args.kwargs['output_config']) is supports_effort


@pytest.mark.asyncio
async def test_anthropic_partial_output_refusal_is_refused():
    provider, call = adapter('anthropic')
    call.return_value = NS(
        stop_reason='refusal', content=[NS(type='text', text='{"text":"partial')],
        model='reported-model', usage=NS(input_tokens=7, output_tokens=9),
    )
    with pytest.raises(LlmRefused):
        await provider.generate(REQUEST, model='claude-opus-5-5', timeout=3)


@pytest.mark.asyncio
async def test_anthropic_sdk_does_not_parse_partial_refusal_before_classifying_it():
    import anthropic
    import httpx2

    from ildongi.assist.adapters.anthropic import Provider

    async def respond(_request):
        return httpx2.Response(200, json={
            'id': 'msg_test', 'type': 'message', 'role': 'assistant', 'model': 'claude-opus-5-5',
            'content': [{'type': 'text', 'text': '{"text":"partial'}],
            'stop_reason': 'refusal', 'stop_sequence': None,
            'usage': {'input_tokens': 7, 'output_tokens': 9},
        })

    http = httpx2.AsyncClient(transport=httpx2.MockTransport(respond))
    client = anthropic.AsyncAnthropic(api_key='private-test-key', http_client=http)
    try:
        provider = Provider('private-test-key', client=client)
        with pytest.raises(LlmRefused):
            await provider.generate(REQUEST, model='claude-opus-5-5', timeout=3)
    finally:
        await client.close()


@pytest.mark.asyncio
@pytest.mark.parametrize('name', ['anthropic', 'openai', 'google'])
@pytest.mark.parametrize('kind', ['refused', 'truncated', 'invalid'])
async def test_output_errors(name, kind):
    provider, _ = adapter(name, refusal=kind == 'refused', truncated=kind == 'truncated',
                          parsed=SummaryText.model_construct(text='x' * 601) if kind == 'invalid' else None)
    with pytest.raises(LlmRefused if kind == 'refused' else LlmInvalidOutput):
        await provider.generate(REQUEST, model='test-model', timeout=3)


def sdk_error(name, kind):
    if name == 'google':
        from google.genai.errors import APIError
        if kind in ('auth', 'rate'):
            return APIError(401 if kind == 'auth' else 429, {'error': {'message': 'private-test-key'}})
        return httpx.ReadTimeout('private-test-key') if kind == 'timeout' else httpx.ConnectError('private-test-key')
    import importlib

    import httpx2
    sdk = importlib.import_module(name)
    req = httpx2.Request('POST', 'https://example.invalid')
    if kind in ('auth', 'rate'):
        status = 401 if kind == 'auth' else 429
        cls = sdk.AuthenticationError if kind == 'auth' else sdk.RateLimitError
        return cls('private-test-key', response=httpx2.Response(status, request=req), body=None)
    return sdk.APITimeoutError(request=req) if kind == 'timeout' else sdk.APIConnectionError(message='private-test-key', request=req)


@pytest.mark.asyncio
@pytest.mark.parametrize('name', ['anthropic', 'openai', 'google'])
@pytest.mark.parametrize('kind,expected', [('auth', LlmAuthError), ('rate', LlmRateLimited), ('timeout', LlmTimeout), ('connection', LlmConnectionError)])
async def test_sanitized_sdk_errors(name, kind, expected):
    provider, _ = adapter(name, exception=sdk_error(name, kind))
    with pytest.raises(expected) as caught:
        await provider.generate(REQUEST, model='test-model', timeout=3)
    assert 'private-test-key' not in str(caught.value)
    assert caught.value.__suppress_context__
