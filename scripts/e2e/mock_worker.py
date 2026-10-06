"""Deterministic E2E model boundary; real jobs, policy, graph and APIs remain in use.

Only available with AI_MODE=mock. This is UI fixture data, never model quality evidence.
"""
import json
import os
import runpy
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'backend'))
assert os.environ.get('AI_MODE') == 'mock', 'E2E fixture worker requires mock mode'
from ildongi.judgment.ai_client import AiClient, validate_response


def ask(self, state, questions):
    assert self.mode == 'mock'
    text = json.dumps(state, ensure_ascii=False)
    if any(key.startswith('needed_') for key in questions):
        time.sleep(3)  # Keep provisional cards observable before the final save.
    if 'ai_need' in questions:
        time.sleep(0.4)
    choices = {'ai_need': '불필요', 'feasibility': '정보 부족', 'urgency': '일반', 'lead_org': 'IT팀'}
    if '생성형 AI' in text:
        choices['ai_need'] = '혼합'
    if any(word in text for word in ('오늘', '즉시', '중단됐')):
        choices['urgency'] = '긴급'
    if 'E2E_AUTO_ASSIGN' in text or '고객 문의 분류에 챗봇을 도입' in text:
        choices['feasibility'] = '가능'
    answers = {}
    for key, q in questions.items():
        if q['type'] == 'choice':
            value = choices.get(key, next(iter(q['criteria'])))
            answers[key] = {'type': 'choice', 'choice': value, 'confidence': .99,
                            'probabilities': {option: .99 if option == value else .01 / (len(q['criteria']) - 1) for option in q['criteria']}}
        elif q['type'] == 'noul':
            high = key in {'is_evidence', 'it_team_involvement', 'business_involvement', 'needed_reporting', 'needed_integration'}
            high |= key in {'needed_ai_assessment', 'ai_team_involvement'} and '생성형 AI' in text
            high |= key in {'clinical_safety', 'regulatory'} and '이상반응' in text
            answers[key] = {'type': 'noul', 'noul': .99 if high else .01}
        else:
            answers[key] = {'type': 'score', 'score': 0.0, 'confidence': .99, 'probabilities': {'0': .99, '1': .005, '2': .005}}
    return validate_response({'model': 'e2e-fixture', 'answers': answers, 'usage': {'input_tokens': 0, 'output_tokens': 0}}, questions, mode='mock')


AiClient.ask = ask
runpy.run_module('ildongi.jobs.worker', run_name='__main__')
