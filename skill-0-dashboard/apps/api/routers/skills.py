"""Skills API router"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from ..schemas.skill import RevisionSummary, SkillSummary, SkillDetail, SkillListResponse
from ..schemas.action import (
    ActionJobItem,
    ActionJobRequest,
    ActionJobSummary,
    ActionReadiness,
    ActionResult,
)
from ..auth import require_auth
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


@router.get("/skills/{skill_id}/revisions", response_model=list[RevisionSummary])
def get_skill_revisions(
    skill_id: str,
    service: GovernanceService = Depends(get_governance_service),
) -> list[RevisionSummary]:
    """Get explicit revision history for a skill."""
    data = service.get_skill_revisions(skill_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Skill not found")
    return [RevisionSummary(**item) for item in data]


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
    """Trigger a fidelity test for one or all pending skills"""
    if skill_id:
        result = service.run_test(skill_id)
    else:
        result = service.run_test_batch()
    return ActionResult(**result)


@router.post("/skills/scan-jobs", response_model=ActionJobSummary)
def enqueue_scan_job(
    request: ActionJobRequest,
    user: dict = Depends(require_auth),
    service: GovernanceService = Depends(get_governance_service),
) -> ActionJobSummary:
    """Enqueue an async security scan batch job."""
    data = service.enqueue_action_job(
        job_type="scan_batch",
        skill_ids=request.skill_ids,
        requested_by=user.get("sub", "unknown"),
        selection_mode=request.selection_mode,
        max_attempts=request.max_attempts,
    )
    return ActionJobSummary(**data)


@router.post("/skills/test-jobs", response_model=ActionJobSummary)
def enqueue_test_job(
    request: ActionJobRequest,
    user: dict = Depends(require_auth),
    service: GovernanceService = Depends(get_governance_service),
) -> ActionJobSummary:
    """Enqueue an async fidelity test batch job."""
    data = service.enqueue_action_job(
        job_type="test_batch",
        skill_ids=request.skill_ids,
        requested_by=user.get("sub", "unknown"),
        selection_mode=request.selection_mode,
        max_attempts=request.max_attempts,
    )
    return ActionJobSummary(**data)


@router.get("/skills/action-jobs/{job_id}", response_model=ActionJobSummary)
def get_action_job(
    job_id: str,
    service: GovernanceService = Depends(get_governance_service),
) -> ActionJobSummary:
    """Get async action job status."""
    data = service.get_action_job(job_id)
    if not data:
        raise HTTPException(status_code=404, detail="Action job not found")
    return ActionJobSummary(**data)


@router.get("/skills/action-jobs/{job_id}/items", response_model=list[ActionJobItem])
def list_action_job_items(
    job_id: str,
    service: GovernanceService = Depends(get_governance_service),
) -> list[ActionJobItem]:
    """List async action job items."""
    data = service.get_action_job_items(job_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Action job not found")
    return [ActionJobItem(**item) for item in data]


@router.post("/skills/action-jobs/{job_id}/retry-failures", response_model=ActionJobSummary)
def retry_action_job_failures(
    job_id: str,
    user: dict = Depends(require_auth),
    service: GovernanceService = Depends(get_governance_service),
) -> ActionJobSummary:
    """Retry failed items from a previous async action job."""
    try:
        data = service.retry_action_job_failures(
            job_id=job_id,
            requested_by=user.get("sub", "unknown"),
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Action job not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ActionJobSummary(**data)


@router.post("/skills/action-jobs/{job_id}/items/{item_id}/retry", response_model=ActionJobSummary)
def retry_action_job_item(
    job_id: str,
    item_id: str,
    user: dict = Depends(require_auth),
    service: GovernanceService = Depends(get_governance_service),
) -> ActionJobSummary:
    """Retry a specific failed async action job item."""
    try:
        data = service.retry_action_job_item(
            job_id=job_id,
            item_id=item_id,
            requested_by=user.get("sub", "unknown"),
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Action job item not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ActionJobSummary(**data)
