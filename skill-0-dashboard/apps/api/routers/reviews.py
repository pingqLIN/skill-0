<<<<<<< Updated upstream
"""Reviews API router"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException

from ..schemas.skill import SkillSummary
from ..schemas.review import ReviewAction
from ..services.governance import GovernanceService
from ..dependencies import get_governance_service

router = APIRouter()


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
    service: GovernanceService = Depends(get_governance_service),
) -> dict:
    """Approve a skill for use"""
    success = service.approve_skill(
        skill_id, reviewer=action.reviewer, reason=action.reason
    )
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Cannot approve skill. It may not exist or is blocked.",
        )
    return {
        "status": "approved",
        "skill_id": skill_id,
        "reviewer": action.reviewer,
        "reason": action.reason,
    }


@router.post("/reviews/{skill_id}/reject")
def reject_skill(
    skill_id: str,
    action: ReviewAction,
    service: GovernanceService = Depends(get_governance_service),
) -> dict:
    """Reject a skill"""
    success = service.reject_skill(
        skill_id, reviewer=action.reviewer, reason=action.reason
    )
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Cannot reject skill. It may not exist.",
        )
    return {
        "status": "rejected",
        "skill_id": skill_id,
        "reviewer": action.reviewer,
        "reason": action.reason,
    }
=======
"""Reviews API router"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException

from ..schemas.skill import SkillSummary
from ..schemas.review import ReviewAction
from ..services.governance import GovernanceService
from ..dependencies import get_governance_service

router = APIRouter()


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
    service: GovernanceService = Depends(get_governance_service),
) -> dict:
    """Approve a skill for use"""
    success = service.approve_skill(
        skill_id, reviewer=action.reviewer, reason=action.reason
    )
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Cannot approve skill. It may not exist or is blocked.",
        )
    return {
        "status": "approved",
        "skill_id": skill_id,
        "reviewer": action.reviewer,
        "reason": action.reason,
    }


@router.post("/reviews/{skill_id}/reject")
def reject_skill(
    skill_id: str,
    action: ReviewAction,
    service: GovernanceService = Depends(get_governance_service),
) -> dict:
    """Reject a skill"""
    success = service.reject_skill(
        skill_id, reviewer=action.reviewer, reason=action.reason
    )
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Cannot reject skill. It may not exist.",
        )
    return {
        "status": "rejected",
        "skill_id": skill_id,
        "reviewer": action.reviewer,
        "reason": action.reason,
    }
>>>>>>> Stashed changes
