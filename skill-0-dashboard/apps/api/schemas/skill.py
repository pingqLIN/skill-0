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
    source_url: str = ""
    source_type: Optional[str] = None
    version: str = "1.0.0"
    created_at: Optional[datetime] = None
    updated_at: datetime


class SkillDetail(SkillSummary):
    """Detailed view of a skill with all related data"""

    source_path: str = ""
    source_commit: Optional[str] = None
    original_format: Optional[str] = None
    fetched_at: Optional[datetime] = None
    author_email: Optional[str] = None
    author_url: Optional[str] = None
    author_org: Optional[str] = None
    license_url: Optional[str] = None
    requires_attribution: bool = False
    commercial_allowed: bool = True
    modification_allowed: bool = True
    converted_at: Optional[datetime] = None
    converter_version: Optional[str] = None
    target_format: Optional[str] = None
    security_scanned_at: Optional[datetime] = None
    scanner_version: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    equivalence_tested_at: Optional[datetime] = None
    equivalence_passed: Optional[bool] = None
    installed_path: Optional[str] = None
    installed_at: Optional[datetime] = None
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
