"""Privileged provider diagnostics; credentials never leave Settings."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from ildongi.assist.providers import DEFAULT_MODELS
from ildongi.assist.service import list_models, provider_status, safe_response, test_connection
from ildongi.auth.core import require_roles
from ildongi.config import get_settings

router = APIRouter(prefix='/api/assist', tags=['assist'])


class ConnectionTest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    model: str = Field(pattern=r'^[A-Za-z0-9._:/-]{1,100}$')


def known_provider(provider):
    if provider not in DEFAULT_MODELS:
        raise HTTPException(404, 'Provider not found')
    return provider


@router.get('/providers')
async def providers(principal=Depends(require_roles('policy_editor', 'operator'))):  # noqa: B008
    settings = get_settings()
    return safe_response(provider_status(settings), settings)


@router.get('/providers/{provider}/models')
async def models(provider: str, principal=Depends(require_roles('policy_editor', 'operator'))):  # noqa: B008
    return await list_models(known_provider(provider), get_settings())


@router.post('/providers/{provider}/test')
async def test(provider: str, body: ConnectionTest,
               principal=Depends(require_roles('policy_editor'))):  # noqa: B008
    return await test_connection(known_provider(provider), body.model, get_settings())
