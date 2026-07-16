"""Skill schemas for the Governance Dashboard API"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from .scan import SecurityFinding, ScanSummary
from .audit import AuditEvent


class TestSummary(BaseModel):
    """Summary of a fidelity test"""

    test_id: str
    revision_id: Optional[str] = None
    tested_at: datetime
    overall_score: float
    fidelity_score: Optional[float] = None
    passed: bool
    semantic_similarity: Optional[float] = None
    structure_similarity: Optional[float] = None
    keyword_similarity: Optional[float] = None


class RevisionSummary(BaseModel):
    """Summary view of a skill revision."""

    revision_id: str
    revision_number: int
    status: str
    version: str = "1.0.0"
    source_commit: Optional[str] = None
    source_path: str = ""
    source_checksum: Optional[str] = None
    artifact_digest: Optional[str] = None
    risk_level: str = "unknown"
    risk_score: int = 0
    equivalence_score: Optional[float] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    is_current: bool = False


class SkillSummary(BaseModel):
    """Summary view of a skill for list display"""

    skill_id: str
    canonical_skill_id: Optional[str] = None
    current_revision_id: Optional[str] = None
    revision_id: Optional[str] = None
    revision_number: Optional[int] = None
    name: str
    status: str
    risk_level: str
    risk_score: int
    fidelity_score: Optional[float] = None
    equivalence_score: Optional[float] = None
    author_name: str
    license_spdx: str
    source_url: str = ""
    source_checksum: Optional[str] = None
    artifact_digest: Optional[str] = None
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
    fidelity_tested_at: Optional[datetime] = None
    security_scanned_at: Optional[datetime] = None
    scanner_version: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    fidelity_passed: Optional[bool] = None
    equivalence_tested_at: Optional[datetime] = None
    equivalence_passed: Optional[bool] = None
    installed_path: Optional[str] = None
    installed_at: Optional[datetime] = None
    security_findings: List[SecurityFinding] = []
    scan_history: List[ScanSummary] = []
    test_history: List[TestSummary] = []
    audit_events: List[AuditEvent] = []
    revision_history: List[RevisionSummary] = []


class SkillListResponse(BaseModel):
    """Paginated list of skills"""

    items: List[SkillSummary]
    total: int
    page: int
    page_size: int
