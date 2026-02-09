"""Audit API router"""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from ..schemas.audit import AuditEvent, AuditListResponse
from ..services.governance import GovernanceService
from ..dependencies import get_governance_service

router = APIRouter()


@router.get("/audit", response_model=AuditListResponse)
def get_audit_log(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    skill_id: Optional[str] = Query(None, description="Filter by skill ID"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    from_date: Optional[str] = Query(None, description="Filter from date (ISO format)"),
    to_date: Optional[str] = Query(None, description="Filter to date (ISO format)"),
    service: GovernanceService = Depends(get_governance_service),
) -> AuditListResponse:
    """Get paginated audit log with optional filters"""
    data = service.get_audit_log(
        page=page,
        page_size=page_size,
        skill_id=skill_id,
        event_type=event_type,
        from_date=from_date,
        to_date=to_date,
    )
    return AuditListResponse(
        items=[AuditEvent(**item) for item in data["items"]],
        total=data["total"],
        page=data["page"],
        page_size=data["page_size"],
    )
