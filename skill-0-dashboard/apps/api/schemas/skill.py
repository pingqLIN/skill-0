"""Skill schemas for the Governance Dashboard API"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from .scan import SecurityFinding, ScanSummary
from .audit import AuditEvent


class TestSummary(BaseModel):
    """Summary of an equivalence test"""

    test_id: str
    tested_at: datetime
    overall_score: float
    passed: bool
    semantic_similarity: Optional[float] = None
    structure_similarity: Optional[float] = None
    keyword_similarity: Optional[float] = None


class SkillSummary(BaseModel):
    """Summary view of a skill for list display"""

    skill_id: str
    name: str
    status: str
    risk_level: str
    risk_score: int
    equivalence_score: Optional[float] = None
    author_name: str
    license_spdx: str
    updated_at: datetime


class SkillDetail(SkillSummary):
    """Detailed view of a skill with all related data"""

    version: str = "1.0.0"
    source_type: str
    source_path: str
    source_url: str = ""
    author_email: Optional[str] = None
    created_at: datetime
    security_findings: List[SecurityFinding] = []
    scan_history: List[ScanSummary] = []
    test_history: List[TestSummary] = []
    audit_events: List[AuditEvent] = []


class SkillListResponse(BaseModel):
    """Paginated list of skills"""

    items: List[SkillSummary]
    total: int
    page: int
    page_size: int
