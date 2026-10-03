from fastapi import APIRouter, Depends, HTTPException, Query

from jevtriage.auth.core import Principal, require_roles
from jevtriage.learning.effects import rule_effects

router=APIRouter(prefix="/api/learning/rules",tags=["learning"])
RULE_ADMIN = Depends(require_roles("rule_admin"))
@router.get("/{rule_id}/effects")
async def effects(rule_id:str,days:int|None=Query(None,ge=1,le=90),principal:Principal=RULE_ADMIN):
    try:
        return await rule_effects(principal.tenant_id,rule_id,days)
    except LookupError:
        raise HTTPException(404, detail={"code":"RULE_NOT_PUBLISHED"})
