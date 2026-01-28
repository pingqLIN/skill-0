"""Statistics schemas for the Governance Dashboard API"""

from pydantic import BaseModel


class StatsOverview(BaseModel):
    """Overview statistics for the dashboard"""

    total_skills: int
    pending_count: int
    approved_count: int
    rejected_count: int
    blocked_count: int
    high_risk_count: int
    avg_equivalence_score: float


class RiskDistribution(BaseModel):
    """Distribution of skills by risk level"""

    safe: int = 0
    low: int = 0
    medium: int = 0
    high: int = 0
    critical: int = 0
    blocked: int = 0


class StatusDistribution(BaseModel):
    """Distribution of skills by status"""

    pending: int = 0
    approved: int = 0
    rejected: int = 0
    blocked: int = 0


class FindingsByRule(BaseModel):
    """Security findings aggregated by rule"""

    rule_id: str
    rule_name: str
    severity: str
    count: int
