"""Statistics API router"""

from typing import List

from fastapi import APIRouter, Depends

from ..schemas.stats import (
    StatsOverview,
    RiskDistribution,
    StatusDistribution,
    FindingsByRule,
)
from ..services.governance import GovernanceService
from ..dependencies import get_governance_service

router = APIRouter()


@router.get("/stats", response_model=StatsOverview)
def get_stats_overview(
    service: GovernanceService = Depends(get_governance_service),
) -> StatsOverview:
    """Get overview statistics for the dashboard"""
    data = service.get_stats_overview()
    return StatsOverview(**data)


@router.get("/stats/risk-distribution", response_model=RiskDistribution)
def get_risk_distribution(
    service: GovernanceService = Depends(get_governance_service),
) -> RiskDistribution:
    """Get distribution of skills by risk level"""
    data = service.get_risk_distribution()
    return RiskDistribution(**data)


@router.get("/stats/status-distribution", response_model=StatusDistribution)
def get_status_distribution(
    service: GovernanceService = Depends(get_governance_service),
) -> StatusDistribution:
    """Get distribution of skills by status"""
    data = service.get_status_distribution()
    return StatusDistribution(**data)


@router.get("/stats/findings-by-rule", response_model=List[FindingsByRule])
def get_findings_by_rule(
    service: GovernanceService = Depends(get_governance_service),
) -> List[FindingsByRule]:
    """Get security findings aggregated by rule"""
    data = service.get_findings_by_rule()
    return [FindingsByRule(**item) for item in data]
