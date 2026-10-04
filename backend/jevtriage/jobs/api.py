"""Judgment job cancellation API."""

from fastapi import APIRouter, Depends, HTTPException

from jevtriage.auth.core import Principal, enforce_csrf, get_principal
from jevtriage.jobs.cancel import cancel_run

router = APIRouter(prefix="/api", tags=["jobs"])


@router.post("/requests/{request_id}/runs/{run_id}/cancel",
             dependencies=[Depends(enforce_csrf)])
async def cancel_request_run(request_id: str, run_id: str,
                             principal: Principal = Depends(get_principal)):  # noqa: B008
    try:
        return await cancel_run(principal, request_id, run_id)
    except LookupError as exc:
        raise HTTPException(404, "Run not found") from exc
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
