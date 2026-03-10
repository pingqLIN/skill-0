"""Skills API router"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from ..schemas.skill import SkillSummary, SkillDetail, SkillListResponse
from ..schemas.action import ActionReadiness, ActionResult
from ..services.governance import GovernanceService
from ..dependencies import get_governance_service

router = APIRouter()


@router.get("/skills", response_model=SkillListResponse)
def list_skills(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by status"),
    risk_level: Optional[str] = Query(None, description="Filter by risk level"),
    search: Optional[str] = Query(None, description="Search in name and author"),
    sort_by: str = Query("updated_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    service: GovernanceService = Depends(get_governance_service),
) -> SkillListResponse:
    """List skills with pagination and filtering"""
    data = service.list_skills(
        page=page,
        page_size=page_size,
        status=status,
        risk_level=risk_level,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return SkillListResponse(
        items=[SkillSummary(**item) for item in data["items"]],
        total=data["total"],
        page=data["page"],
        page_size=data["page_size"],
    )


@router.get("/skills/{skill_id}/action-readiness", response_model=ActionReadiness)
def get_action_readiness(
    skill_id: str,
    service: GovernanceService = Depends(get_governance_service),
) -> ActionReadiness:
    """Check whether scan and test actions can be executed for a skill"""
    data = service.get_action_readiness(skill_id)
    if not data:
        raise HTTPException(status_code=404, detail="Skill not found")
    return ActionReadiness(**data)


@router.get("/skills/{skill_id}", response_model=SkillDetail)
def get_skill(
    skill_id: str,
    service: GovernanceService = Depends(get_governance_service),
) -> SkillDetail:
    """Get detailed skill information"""
    data = service.get_skill(skill_id)
    if not data:
        raise HTTPException(status_code=404, detail="Skill not found")
    return SkillDetail(**data)


@router.post("/skills/scan", response_model=ActionResult)
def trigger_scan(
    skill_id: Optional[str] = Query(
        None, description="Skill ID to scan (or scan all pending)"
    ),
    service: GovernanceService = Depends(get_governance_service),
) -> ActionResult:
    """Trigger a security scan for one or all pending skills"""
    if skill_id:
        result = service.run_scan(skill_id)
    else:
        result = service.run_scan_batch()
    return ActionResult(**result)


@router.post("/skills/test", response_model=ActionResult)
def trigger_test(
    skill_id: Optional[str] = Query(
        None, description="Skill ID to test (or test all pending)"
    ),
    service: GovernanceService = Depends(get_governance_service),
) -> ActionResult:
    """Trigger an equivalence test for one or all pending skills"""
    if skill_id:
        result = service.run_test(skill_id)
    else:
        result = service.run_test_batch()
    return ActionResult(**result)
