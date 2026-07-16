"""Reviews API router"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_auth
from ..schemas.skill import SkillSummary
from ..schemas.review import ReviewAction, RuntimeBindingAction
from ..services.governance import GovernanceService
from ..dependencies import get_governance_service

router = APIRouter()


@router.post("/reviews/{skill_id}/runtime-bind")
def bind_runtime_artifact(
    skill_id: str,
    action: RuntimeBindingAction,
    user: dict = Depends(require_auth),
    service: GovernanceService = Depends(get_governance_service),
) -> dict:
    reviewer = user.get("sub")
    if not reviewer:
        raise HTTPException(status_code=401, detail="Invalid token")
    try:
        binding = service.bind_runtime_artifact(
            skill_id,
            canonical_skill_id=action.canonical_skill_id,
            reviewer=reviewer,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if binding is None:
        raise HTTPException(
            status_code=404,
            detail="Governance skill or canonical parsed artifact was not found",
        )
    return {"status": "bound", **binding, "reviewer": reviewer}


@router.get("/reviews", response_model=List[SkillSummary])
def list_pending_reviews(
    service: GovernanceService = Depends(get_governance_service),
) -> List[SkillSummary]:
    """Get all skills pending review"""
    data = service.get_pending_reviews()
    return [SkillSummary(**item) for item in data]


@router.post("/reviews/{skill_id}/approve")
def approve_skill(
    skill_id: str,
    action: ReviewAction,
    user: dict = Depends(require_auth),
    service: GovernanceService = Depends(get_governance_service),
) -> dict:
    """Approve a skill for use"""
    reviewer = user.get("sub")
    if not reviewer:
        raise HTTPException(status_code=401, detail="Invalid token")
    success = service.approve_skill(
        skill_id, reviewer=reviewer, reason=action.reason
    )
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Cannot approve skill. It may not exist or is blocked.",
        )
    return {
        "status": "approved",
        "skill_id": skill_id,
        "reviewer": reviewer,
        "reason": action.reason,
    }


@router.post("/reviews/{skill_id}/reject")
def reject_skill(
    skill_id: str,
    action: ReviewAction,
    user: dict = Depends(require_auth),
    service: GovernanceService = Depends(get_governance_service),
) -> dict:
    """Reject a skill"""
    reviewer = user.get("sub")
    if not reviewer:
        raise HTTPException(status_code=401, detail="Invalid token")
    success = service.reject_skill(
        skill_id, reviewer=reviewer, reason=action.reason
    )
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Cannot reject skill. It may not exist.",
        )
    return {
        "status": "rejected",
        "skill_id": skill_id,
        "reviewer": reviewer,
        "reason": action.reason,
    }
