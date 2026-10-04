"""HTTP routes for human evaluation labeling."""

from fastapi import APIRouter, Depends

from jevtriage.auth.core import Principal, get_principal
from jevtriage.evaluation import service
from jevtriage.evaluation.service import LabelBody

router = APIRouter(prefix="/api/evaluation", tags=["evaluation"])


@router.get("/candidates")
async def candidates(split: str = "tuning", principal: Principal = Depends(get_principal)):  # noqa: B008
    return await service.candidates(split, principal)


@router.put("/candidates/{split}/{sample_id}")
async def save_label(split: str, sample_id: str, body: LabelBody,
                     principal: Principal = Depends(get_principal)):  # noqa: B008
    return await service.save_label(split, sample_id, body, principal)


@router.post("/candidates/{split}/{sample_id}/consensus")
async def confirm_consensus(split: str, sample_id: str, body: LabelBody,
                            principal: Principal = Depends(get_principal)):  # noqa: B008
    return await service.confirm_consensus(split, sample_id, body, principal)
