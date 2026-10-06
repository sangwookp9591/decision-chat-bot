"""Raw AiClient is also a safe transport for future callers."""
import json

from ildongi.judgment.ai_client import AiClient


def test_direct_transport_masks_state_and_question_text(monkeypatch):
    values = ['qa@example.invalid', '010-1234-5678', '900101-1234567',
              '4111 1111 1111 1111', '_'.join(('sk', 'test', 'QACanary'+'0123456789'*3))]
    text = '\n'.join(values)
    sent = []
    client = AiClient('unused', mode='live')
    def invoke(state, questions, timeout):
        sent.append(json.dumps([state, questions]))
        return {'model': client.model, 'answers': {'q': {'type': 'noul', 'noul': 0.5}},
                'usage': {'input_tokens': 1, 'output_tokens': 1}}
    monkeypatch.setattr(client, '_invoke', invoke)
    state = {'chat_text': text, 'future_field': {'nested': [text]}, 'operating_guidance': [text]}
    question = {'q': {'type': 'noul', 'instructions': text, 'criteria': {'true': text}}}
    client.ask(state, question)
    assert sent
    assert all(value not in payload for payload in sent for value in values)
    assert state['chat_text'] == text and question['q']['instructions'] == text


def test_sdk_transport_is_confined_to_guarded_client():
    import ast
    from pathlib import Path
    package = Path(__file__).resolve().parents[2] / 'ildongi'
    allowed = package / 'judgment' / 'ai_client.py'
    for path in package.rglob('*.py'):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.ImportFrom) and (node.module or '').startswith('typesafe_sdk'):
                assert path == allowed, path
            if isinstance(node, ast.Import) and any(
                    alias.name.startswith('typesafe_sdk') for alias in node.names):
                assert path == allowed, path
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == 'system_one'):
                assert path == allowed, path
