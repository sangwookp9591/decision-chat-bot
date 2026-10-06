"""Bounded, independently falling back text generation and pure allow-list merge."""
import asyncio
import json
import time
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime

from ildongi.assist.prompts import (
    INSTRUCTIONS,
    PROMPT_VERSION,
    SYSTEM,
    MissingInfoQuestions,
    Ping,
    RuleExplanation,
    SummaryText,
    TaskDescriptions,
    validate_output,
)
from ildongi.assist.providers import (
    DEFAULT_MODELS,
    KEY_FIELDS,
    LlmError,
    LlmInvalidOutput,
    LlmRequest,
    LlmUnavailable,
    get_provider,
    sdk_available,
)
from ildongi.domain.masking import MaskingSession, mask_for_external


@dataclass
class AssistOutcome:
    summary: dict | None
    descriptions: dict[str, tuple[str, str]]
    questions: dict | None
    calls: list[dict]
    llm_version: str


def _masked(value, policy):
    if isinstance(value, str):
        return mask_for_external(value, policy)
    if isinstance(value, list):
        return [_masked(item, policy) for item in value]
    if isinstance(value, dict):
        return {key: _masked(item, policy) for key, item in value.items()}
    return value


def _request(feature, output_type, data, config):
    return LlmRequest(feature, SYSTEM + ' ' + INSTRUCTIONS[feature],
                      json.dumps(data, ensure_ascii=False), output_type,
                      config.get('max_output_tokens', 2000))


def _error_code(exc):
    if isinstance(exc, LlmError):
        return exc.code
    return 'TIMEOUT' if isinstance(exc, TimeoutError) else type(exc).__name__


def _call(feature, provider, model):
    return {'feature': feature, 'provider': provider, 'model': model, 'outcome': 'skipped',
            'error_code': None, 'input_tokens': 0, 'output_tokens': 0, 'latency_ms': 0}


async def write_run_texts(*, units, result, llm_config, policy, mask_session, settings,
                          provider=None):
    name, model = llm_config.get('provider'), llm_config.get('model')
    features = llm_config.get('features') or {}
    outcome = AssistOutcome(None, {}, None, [], 'off')
    if not any(features.get(feature) for feature in ('summary', 'task_description', 'questions')):
        outcome.calls = [_call(feature, name, model) for feature in ('summary', 'task_description', 'questions')]
        return outcome
    mask_policy = {**policy, '_masking_session': mask_session}
    masked_units = []
    remaining = 4000
    for unit in units:
        if remaining <= 0:
            break
        text = mask_for_external(unit['text'], mask_policy)[:remaining]
        masked_units.append({'unit_id': unit['unit_id'], 'text': text})
        remaining -= len(text)
    uncertain = [{'key': key, 'label': label} for key, label in (
        ('ai_need', 'AI 필요성'), ('feasibility', '개발 가능성'),
        ('urgency', '긴급도'), ('lead_org', '주관 조직'))
        if result.get('classifications', {}).get(key) in ('정보 부족', '판단 보류')]
    tasks = [{key: task.get(key) for key in ('draft_task_id', 'title', 'method', 'lead_org', 'deliverable')}
             for task in result.get('draft_tasks', [])]
    inputs = [('summary', SummaryText, {'units': masked_units}),
              ('task_description', TaskDescriptions, {'units': masked_units, 'tasks': _masked(tasks, mask_policy)}),
              ('questions', MissingInfoQuestions, {'units': masked_units, 'uncertain': uncertain})]

    async def generate(feature, output_type, data, call):
        if not features.get(feature) or (feature == 'questions' and not uncertain):
            return
        started = time.monotonic()
        call.update(outcome='fallback', error_code='TIMEOUT')
        try:
            if settings.llm_mode == 'off':
                raise LlmUnavailable('MODE_OFF')
            if not name or not model:
                raise LlmUnavailable('MODE_OFF')
            if not policy.get('masking', {}).get('enabled', True):
                raise LlmUnavailable('MASKING_DISABLED')
            selected = provider or get_provider(name, settings)
            timeout = llm_config.get('timeout_seconds', 15)
            response = await asyncio.wait_for(selected.generate(
                _request(feature, output_type, data, llm_config), model=model, timeout=timeout), timeout)
            parsed = validate_output(output_type, response.parsed)
            author = f'llm:{response.provider}/{response.model}'
            if feature == 'summary':
                outcome.summary = {'text': parsed.text, 'author': author,
                                   'base': deepcopy(result.get('summary', {}))}
            elif feature == 'task_description':
                valid_ids = {task['draft_task_id'] for task in tasks}
                outcome.descriptions = {item.draft_task_id: (item.description, author)
                                        for item in parsed.items if item.draft_task_id in valid_ids}
            elif parsed.questions:
                outcome.questions = {'items': parsed.questions, 'author': author}
            outcome.llm_version = f'{response.provider}/{response.model}'
            call.update(outcome='ok', error_code=None, model=response.model,
                        input_tokens=response.input_tokens, output_tokens=response.output_tokens)
        except Exception as exc:  # noqa: BLE001 - optional text must fall back on every provider failure
            call['error_code'] = _error_code(exc)
            if isinstance(exc, LlmError) and exc.status is not None:
                call['status'] = exc.status
        finally:
            call['latency_ms'] = round((time.monotonic()-started)*1000)

    jobs = []
    for feature, output_type, data in inputs:
        call = _call(feature, name, model)
        outcome.calls.append(call)
        jobs.append(generate(feature, output_type, data, call))
    try:
        await asyncio.wait_for(asyncio.gather(*jobs), llm_config.get('step_budget_seconds', 20))
    except TimeoutError:
        pass  # Completed features survive; cancelled features already have TIMEOUT fallback records.
    return outcome


def apply_texts(result, outcome):
    merged = deepcopy(result)
    if outcome.summary is not None:
        merged['summary'] = deepcopy(outcome.summary)
    for task in merged.get('draft_tasks', []):
        if task.get('draft_task_id') in outcome.descriptions:
            task['description'], task['description_author'] = outcome.descriptions[task['draft_task_id']]
    merged['questions'] = deepcopy(outcome.questions)
    first = next((call for call in outcome.calls if call["outcome"] == "ok"),
                 outcome.calls[0] if outcome.calls else {})
    merged['llm'] = {'provider': first.get('provider'), 'model': first.get('model'),
                     'prompt_version': PROMPT_VERSION, 'calls': deepcopy(outcome.calls)}
    merged.setdefault('versions', {}).update(llm=outcome.llm_version, assist_prompts=PROMPT_VERSION)
    return merged


async def explain_rule(*, proposed_body, rationale, llm_config, policy, settings, provider=None, usage=None):
    if not llm_config.get('features', {}).get('rule_explanation'):
        raise LlmUnavailable('LLM_DISABLED')
    if not llm_config.get('provider') or not llm_config.get('model'):
        raise LlmUnavailable('LLM_UNAVAILABLE')
    if not policy.get('masking', {}).get('enabled', True):
        raise LlmUnavailable('MASKING_DISABLED')
    data = _masked({'rule': {key: proposed_body.get(key) for key in ('target', 'scope', 'action')},
                    'rationale': rationale[:4000]}, {**policy, '_masking_session': MaskingSession()})
    selected = provider or get_provider(llm_config['provider'], settings)
    timeout = llm_config.get('timeout_seconds', 15)
    response = await asyncio.wait_for(selected.generate(
        _request('rule_explanation', RuleExplanation, data, llm_config),
        model=llm_config['model'], timeout=timeout), timeout)
    if usage is not None:
        usage.update(feature='rule_explanation', provider=response.provider, model=response.model,
                     outcome='ok', error_code=None, input_tokens=response.input_tokens,
                     output_tokens=response.output_tokens, latency_ms=response.latency_ms)
    parsed = validate_output(RuleExplanation, response.parsed)
    return parsed.text, f'llm:{response.provider}/{response.model}'


MESSAGES = {
    'KEY_MISSING': 'API 키가 없습니다. 서버 .env의 {key}를 설정하세요.',
    'AUTH_FAILED': '인증에 실패했습니다. 서버 .env의 {key}를 확인하세요.',
    'MODE_OFF': '서버에서 글쓰기 보조가 꺼져 있습니다.',
    'SDK_MISSING': '서버에 공식 SDK가 설치되지 않았습니다.',
    'RATE_LIMITED': '호출 한도를 초과했습니다. 잠시 후 다시 시도하세요.',
    'TIMEOUT': '연결 확인 제한 시간을 초과했습니다.',
    'CONNECTION': '제공자 서버에 연결할 수 없습니다.',
    'REFUSED': '제공자가 요청을 거절했습니다.',
    'INVALID_OUTPUT': '제공자의 응답 형식이 올바르지 않습니다.',
}


def safe_response(value, settings):
    """Mask all API response strings, including exact secrets with nonstandard formats."""
    secrets = [getattr(settings, field).get_secret_value() for field in KEY_FIELDS.values()]
    def clean(item):
        if isinstance(item, str):
            for secret in secrets:
                if secret:
                    item = item.replace(secret, '[MASKED_API_KEY]')
            return mask_for_external(item, {'masking': {'enabled': True, 'categories': ['api_key']}})
        if isinstance(item, list):
            return [clean(v) for v in item]
        if isinstance(item, dict):
            return {key: clean(v) for key, v in item.items()}
        return item
    return clean(value)


async def test_connection(name, model, settings):
    started = time.monotonic()
    error = None
    try:
        # A missing key stays a visible failure even in fake mode; no external request is made.
        if not getattr(settings, KEY_FIELDS[name]).get_secret_value():
            raise LlmUnavailable('KEY_MISSING')
        provider = get_provider(name, settings, max_retries=0)
        response = await asyncio.wait_for(provider.generate(
            _request('ping', Ping, {'text': '연결 확인'}, {}), model=model, timeout=10), 10)
        if not validate_output(Ping, response.parsed).ok:
            raise LlmInvalidOutput()
    except Exception as exc:  # noqa: BLE001 - optional text must fall back on every provider failure
        error = _error_code(exc)
    return safe_response({'provider': name, 'model': model, 'ok': error is None,
                          'latency_ms': round((time.monotonic()-started)*1000), 'error_code': error,
                          'message': MESSAGES.get(error, '제공자 호출에 실패했습니다.').format(
                              key=KEY_FIELDS[name].upper()) if error else '연결 확인에 성공했습니다.',
                          'tested_at': datetime.now(UTC).isoformat()}, settings)


_model_cache = {}


async def list_models(name, settings):
    cache_key = (name, settings.llm_mode, bool(getattr(settings, KEY_FIELDS[name]).get_secret_value()))
    cached = _model_cache.get(cache_key)
    if cached and time.monotonic()-cached[0] < 600:
        return deepcopy(cached[1])
    error = None
    try:
        if not getattr(settings, KEY_FIELDS[name]).get_secret_value():
            raise LlmUnavailable('KEY_MISSING')
        models = await asyncio.wait_for(get_provider(name, settings, max_retries=0).list_models(timeout=10), 10)
        if not models:
            raise LlmInvalidOutput()
        values = [m.model_dump() for m in models]
    except Exception as exc:  # noqa: BLE001 - optional text must fall back on every provider failure
        error = _error_code(exc)
        values = [{'id': id, 'label': label} for id, label in DEFAULT_MODELS[name]]
    result = safe_response({'provider': name, 'source': 'default' if error else 'api',
                            'models': values, 'error_code': error}, settings)
    _model_cache[cache_key] = (time.monotonic(), result)
    return deepcopy(result)


def provider_status(settings):
    return {'providers': [{'provider': name,
                           'key_configured': bool(getattr(settings, KEY_FIELDS[name]).get_secret_value()),
                           'sdk_available': sdk_available(name), 'default_model': models[0][0]}
                          for name, models in DEFAULT_MODELS.items()]}
