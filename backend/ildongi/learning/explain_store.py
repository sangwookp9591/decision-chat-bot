"""Candidate display fields and audit, independent of rule-body persistence."""
import json

from ildongi.db.audit import append_audit_in_tx
from ildongi.db.tx import read_tx, write_tx


async def read_candidate(tenant, candidate_id):
    async def read(tx):
        row = await (await tx.run(
            'MATCH (c:RuleCandidate {tenant_id:$tenant,id:$id}) RETURN c.proposed_body AS body,c.rationale AS rationale',
            tenant=tenant, id=candidate_id)).single()
        return dict(row) if row else None
    return await read_tx(tenant, read)


async def save_explanation(tenant, actor, candidate_id, *, body, text, author, usage):
    async def save(tx):
        row = await (await tx.run(
            'MATCH (c:RuleCandidate {tenant_id:$tenant,id:$id}) WHERE c.proposed_body=$body '
            'SET c.explanation=$text,c.explanation_author=$author,c.explanation_at=datetime(),'
            'c.explanation_usage_json=$usage RETURN c.id AS id',
            tenant=tenant, id=candidate_id, body=body,
            text=text, author=author, usage=json.dumps(usage))).single()
        if not row:
            return False
        await append_audit_in_tx(tx, tenant, actor, 'rule.explanation', 'RuleCandidate', candidate_id,
                                None, {'author': author, 'usage': usage}, '규칙 후보 설명 생성')
        return True
    return await write_tx(tenant, save)
