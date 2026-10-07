"""Display-only candidate explanation, separate from executable rule bodies."""
import json

from fastapi import APIRouter, Depends, HTTPException

from ildongi.assist.providers import LlmError
from ildongi.assist.service import explain_rule, safe_response
from ildongi.auth.core import require_roles
from ildongi.config import get_settings
from ildongi.learning.candidates_store import list_orgs
from ildongi.learning.explain_store import read_candidate, save_explanation
from ildongi.policy.service import get_active_snapshot

router = APIRouter(prefix='/api/learning', tags=['learning'])


@router.post('/candidates/{candidate_id}/explanation')
async def explanation(candidate_id: str,
                      principal=Depends(require_roles('rule_admin'))):  # noqa: B008
    candidate = await read_candidate(principal.tenant_id, candidate_id)
    if candidate is None:
        raise HTTPException(404, 'Candidate not found')
    _, policy = await get_active_snapshot(principal.tenant_id)
    settings = get_settings()
    usage = {}
    try:
        text, author = await explain_rule(
            proposed_body=json.loads(candidate['body']), rationale=candidate['rationale'] or '',
            llm_config=policy.get('llm') or {}, policy=policy, settings=settings, usage=usage,
            org_names={org['id']: org['name'] for org in await list_orgs(principal.tenant_id)})
    except Exception as exc:  # noqa: BLE001 - expose only a sanitized code
        code = exc.code if isinstance(exc, LlmError) else ('TIMEOUT' if isinstance(exc, TimeoutError) else 'PROVIDER_ERROR')
        raise HTTPException(422, detail={'code': code, 'reason': '규칙 설명을 작성하지 못했습니다.'}) from None
    saved = await save_explanation(
        principal.tenant_id, principal.user_id, candidate_id, body=candidate['body'],
        text=text, author=author, usage=usage)
    if not saved:
        raise HTTPException(409, 'Candidate changed; retry')
    return safe_response({'candidate_id': candidate_id, 'explanation': text, 'author': author}, settings)
