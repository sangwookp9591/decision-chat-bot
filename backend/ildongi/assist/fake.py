"""Deterministic external-call-free provider, with injectable feature outcomes."""
import json

from ildongi.assist.prompts import validate_output
from ildongi.assist.providers import DEFAULT_MODELS, LlmError, LlmResult, ModelInfo


class FakeProvider:
    def __init__(self, responses=None, *, name="anthropic"):
        self.name = name
        self.responses = responses or {}
        self.requests = []

    async def generate(self, request, *, model, timeout):
        self.requests.append(request)
        if request.feature in self.responses:
            parsed = self.responses[request.feature]
            if isinstance(parsed, LlmError):
                raise parsed
        elif request.feature == 'ping':
            parsed = {'ok': True}
        elif request.feature == 'task_description':
            parsed = {'items': [{'draft_task_id': task['draft_task_id'], 'description': '[fake] 업무 설명 초안입니다.'} for task in json.loads(request.data).get('tasks', [])][:12]}
        elif request.feature == 'questions':
            parsed = {'questions': ['[fake] 목적과 필요한 정보를 알려 주세요.']}
        else:
            parsed = {'text': f'[fake] 마스킹된 입력 {len(request.data)}자를 바탕으로 작성한 글입니다.'}
        return LlmResult(validate_output(request.output_type, parsed), self.name, model, len(request.data), 20, 0)

    async def list_models(self, *, timeout):
        return [ModelInfo(id=id, label=label) for id, label in DEFAULT_MODELS[self.name]]
