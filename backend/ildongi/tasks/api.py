"""Authorized task list, detail, and state transition endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict

from ildongi.auth.core import Principal, get_principal
from ildongi.auth.policy import can
from ildongi.tasks.service import TaskError, transition, visible_tasks
from ildongi.tasks.service import task_visible as _visible
from ildongi.tasks.store import get_task

router=APIRouter(prefix='/api/tasks',tags=['tasks'])

class TransitionCommand(BaseModel):
    model_config=ConfigDict(extra='forbid')
    to:str
    expected_status:str

@router.get('')
async def tasks(org:str|None=None,role:str|None=None,method:str|None=None,
                status:str|None=None,request_id:str|None=None,
                principal:Principal=Depends(get_principal)):  # noqa: B008
    visible=await visible_tasks(principal)
    if org: visible=[r for r in visible if org==r.get('lead_org') or org in r.get('collab_orgs',[])]
    if role=='lead': visible=[r for r in visible if r.get('lead_org')==org] if org else [r for r in visible if r.get('lead_org')]
    if role=='collab': visible=[r for r in visible if org in r.get('collab_orgs',[])] if org else [r for r in visible if r.get('collab_orgs')]
    if method: visible=[r for r in visible if r.get('method')==method]
    if status: visible=[r for r in visible if r.get('status')==status]
    if request_id: visible=[r for r in visible if r.get('request_id')==request_id]
    return {'tasks':[{**item,'kind':'assigned_task'} for item in visible]}

@router.get('/{task_id}')
async def task_detail(task_id:str,principal:Principal=Depends(get_principal)):  # noqa: B008
    task=await get_task(principal.tenant_id,task_id)
    if not task or not _visible(principal,task): raise HTTPException(404,'Task not found')
    return {'task':task}

@router.post('/{task_id}/transition')
async def task_transition(task_id:str,command:TransitionCommand,principal:Principal=Depends(get_principal)):  # noqa: B008
    task=await get_task(principal.tenant_id,task_id)
    if not task: raise HTTPException(404,'Task not found')
    request=task.get('request') or task
    meta={**request,'tenant_id':principal.tenant_id,'task_org_ids':[item['org'] for item in task.get('orgs',[])]}
    if not can(principal,'transition_task',meta): raise HTTPException(403,'담당 조직 업무만 변경할 수 있습니다')
    try:return await transition(principal,task_id,command.to,command.expected_status)
    except TaskError as exc:raise HTTPException(exc.status_code,str(exc)) from exc
