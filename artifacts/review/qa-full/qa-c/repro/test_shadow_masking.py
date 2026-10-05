"""QA-C-02: every shadow model payload must be masked, just like normal judgment.

Run with dedicated Neo4j: NEO4J_URI=bolt://localhost:7688 NEO4J_PASSWORD=development-only
JEV_MODE=mock PYTHONPATH=backend backend/.venv/bin/pytest -q artifacts/review/qa-full/qa-c/repro/test_shadow_masking.py
"""
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Lock
from uuid import uuid4

import pytest

from jevtriage.db.schema import apply_schema
from jevtriage.db.tx import write_tx
from jevtriage.judgment.jev_client import JevClient
from jevtriage.learning.shadow import validate_rules
from jevtriage.policy.service import DEFAULT_CONFIG, bootstrap_policy

# Deliberately fabricated, published test values only.
SAMPLES = {'email': 'qa.canary@example.invalid', 'phone': '010-1234-5678',
           'registration': '900101-1234567', 'card': '4111 1111 1111 1111',
           'api_key': 'sk_test_REDACTED'}
TEXT = '\n'.join(f'{key}={value}' for key, value in SAMPLES.items())
EVIDENCE = Path(__file__).resolve().parents[1] / 'evidence'


class CaptureClient(JevClient):
    def __init__(self):
        super().__init__('unused', mode='mock')
        self.payloads = []
        self.lock = Lock()

    def ask(self, state, questions):
        with self.lock:
            self.payloads.append(json.loads(json.dumps({'state': state, 'questions': questions})))
        return super().ask(state, questions)


@pytest.mark.asyncio
async def test_context_shadow_masks_every_outgoing_field():
    tenant = 'qa_c_shadow_' + uuid4().hex[:12]
    await apply_schema()
    await bootstrap_policy(tenant)
    config=json.loads(json.dumps(DEFAULT_CONFIG))
    config['learning']['shadow_max_calls']=100
    rule_id = 'R-CONTEXT-QA-C'
    body = {'schema': 'rule-v1', 'rule_id': rule_id, 'version': 1, 'effect': 'context',
            'target': 'ai_need', 'scope': {'all': []}, 'action': {'set': '혼합'},
            'context_text': TEXT}

    async def seed(tx):
        await (await tx.run(
            "CREATE (:RuleVersion {tenant_id:$tenant,id:$id,body:$body,status:'validating'}) "
            "CREATE (:Request {tenant_id:$tenant,id:'request',org_ids:[]}) "
            "CREATE (:InputRevision {tenant_id:$tenant,id:'revision',request_id:'request',text:$text}) "
            "CREATE (:Judgment {tenant_id:$tenant,id:'judgment',request_id:'request',revision_id:'revision',"
            "run_id:'run',created_at:datetime(),ai_need:'필요',feasibility:'가능',urgency:'일반',lead_org:'AI팀'})",
            tenant=tenant, id=rule_id+'@1', body=json.dumps(body), text=TEXT)).consume()
        await (await tx.run("MATCH (c:ConfigVersion {tenant_id:$tenant,status:'active'}) SET c.config_json=$config",tenant=tenant,config=json.dumps(config))).consume()
    await write_tx(tenant, seed)
    client = CaptureClient()
    try:
        result = await validate_rules(tenant, 'tester', rule_id, 1,
                                    datetime.now(UTC)-timedelta(minutes=1),
                                    datetime.now(UTC)+timedelta(minutes=1), client=client, max_calls=100)
        EVIDENCE.mkdir(parents=True, exist_ok=True)
        leaked = {key: sum(value in json.dumps(payload, ensure_ascii=False)
                           for payload in client.payloads) for key, value in SAMPLES.items()}
        (EVIDENCE / 'shadow-masking.json').write_text(json.dumps(
            {'tenant': tenant, 'calls': len(client.payloads), 'status': result['status'],
             'leaked_sample_counts': leaked, 'fabricated_payloads': client.payloads},
            ensure_ascii=False, indent=2))
        assert client.payloads, 'probe never reached the external model boundary'
        assert not any(leaked.values()), f'shadow external payload leaked fabricated samples: {leaked}'
    finally:
        async def remove(tx):
            await (await tx.run('MATCH (n {tenant_id:$tenant}) DETACH DELETE n', tenant=tenant)).consume()
        await write_tx(tenant, remove)
