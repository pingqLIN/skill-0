"""Skills API router"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from ..schemas.skill import SkillSummary, SkillDetail, SkillListResponse
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


@router.post("/skills/scan")
def trigger_scan(
    skill_id: Optional[str] = Query(
        None, description="Skill ID to scan (or scan all pending)"
    ),
) -> dict:
    """Trigger a security scan (stub - to be implemented)"""
    return {
        "status": "queued",
        "message": f"Security scan queued for {'skill ' + skill_id if skill_id else 'all pending skills'}",
    }


@router.post("/skills/test")
def trigger_test(
    skill_id: Optional[str] = Query(
        None, description="Skill ID to test (or test all pending)"
    ),
) -> dict:
    """Trigger an equivalence test (stub - to be implemented)"""
    return {
        "status": "queued",
        "message": f"Equivalence test queued for {'skill ' + skill_id if skill_id else 'all pending skills'}",
    }
