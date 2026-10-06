"""Opt-in: one Ping and one model listing for each configured provider."""
import os

import pytest

from ildongi.assist.prompts import Ping
from ildongi.assist.providers import DEFAULT_MODELS, KEY_FIELDS, get_provider
from ildongi.assist.service import _request
from ildongi.config import Settings


@pytest.mark.asyncio
@pytest.mark.parametrize('name', list(DEFAULT_MODELS))
async def test_live_ping_and_models(name):
    settings = Settings(llm_mode='live')
    if os.getenv('LLM_LIVE_TEST') != '1' or not getattr(settings, KEY_FIELDS[name]).get_secret_value():
        pytest.skip('requires explicit LLM_LIVE_TEST=1 and server key')
    provider = get_provider(name, settings, max_retries=0)
    result = await provider.generate(_request('ping', Ping, {'text': '연결 확인'}, {}), model=DEFAULT_MODELS[name][0][0], timeout=10)
    assert result.parsed.ok
    assert await provider.list_models(timeout=10)
