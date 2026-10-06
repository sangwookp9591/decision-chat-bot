from fastapi import APIRouter, Depends, HTTPException, Query

from ildongi.auth.core import Principal, require_roles
from ildongi.learning.effects import rule_effects
from ildongi.learning.rule_access import readable_rule
from ildongi.learning.rules import rule_detail

router=APIRouter(prefix="/api/learning/rules",tags=["learning"])
RULE_ADMIN = Depends(require_roles("reviewer", "rule_admin", "operator"))
@router.get("/{rule_id}/effects")
async def effects(rule_id:str,days:int|None=Query(None,ge=1,le=90),principal:Principal=RULE_ADMIN):
    detail = await rule_detail(principal.tenant_id, rule_id)
    if not detail or not readable_rule(principal, detail):
        raise HTTPException(404, detail={"code": "RULE_NOT_FOUND"})
    try:
        return await rule_effects(principal.tenant_id,rule_id,days,principal)
    except LookupError:
        raise HTTPException(404, detail={"code":"RULE_NOT_PUBLISHED"})
