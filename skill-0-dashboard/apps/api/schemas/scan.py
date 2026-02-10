<<<<<<< Updated upstream
"""Security scan schemas for the Governance Dashboard API"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class SecurityFinding(BaseModel):
    """A single security finding from a scan"""

    rule_id: str
    rule_name: str
    severity: str
    line_number: int = 0
    line_content: str = ""
    file_path: str = ""

    # Context-aware fields (from advanced analyzer)
    original_severity: Optional[str] = None
    adjusted_severity: Optional[str] = None
    severity_changed: bool = False
    context_type: Optional[str] = None  # prose, code_block, heading, etc.
    in_code_block: bool = False
    code_block_language: Optional[str] = None
    adjustment_reason: Optional[str] = None

    # Detection standard reference
    detection_standard: Optional[str] = None
    standard_url: Optional[str] = None
    matched_pattern: Optional[str] = None


class ScanSummary(BaseModel):
    """Summary of a security scan"""

    scan_id: str
    scanned_at: datetime
    risk_level: str
    risk_score: int
    findings_count: int


class ScanDetail(ScanSummary):
    """Detailed view of a security scan with findings"""

    findings: List[SecurityFinding] = []
    files_scanned: int = 0
    blocked: bool = False
    blocked_reason: Optional[str] = None

    # Context-aware stats (from advanced analyzer)
    original_risk_score: Optional[int] = None
    code_blocks_found: int = 0
    findings_in_code_blocks: int = 0
    severity_adjustments: int = 0
    scanner_version: Optional[str] = None


class ScanExport(BaseModel):
    """Exportable scan report"""

    skill_name: str
    skill_id: str
    scan: ScanDetail
    detection_standards: List[dict] = []
    export_date: datetime
    export_format: str = "json"
=======
"""Security scan schemas for the Governance Dashboard API"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class SecurityFinding(BaseModel):
    """A single security finding from a scan"""

    rule_id: str
    rule_name: str
    severity: str
    line_number: int = 0
    line_content: str = ""
    file_path: str = ""

    # Context-aware fields (from advanced analyzer)
    original_severity: Optional[str] = None
    adjusted_severity: Optional[str] = None
    severity_changed: bool = False
    context_type: Optional[str] = None  # prose, code_block, heading, etc.
    in_code_block: bool = False
    code_block_language: Optional[str] = None
    adjustment_reason: Optional[str] = None

    # Detection standard reference
    detection_standard: Optional[str] = None
    standard_url: Optional[str] = None
    matched_pattern: Optional[str] = None


class ScanSummary(BaseModel):
    """Summary of a security scan"""

    scan_id: str
    scanned_at: datetime
    risk_level: str
    risk_score: int
    findings_count: int


class ScanDetail(ScanSummary):
    """Detailed view of a security scan with findings"""

    findings: List[SecurityFinding] = []
    files_scanned: int = 0
    blocked: bool = False
    blocked_reason: Optional[str] = None

    # Context-aware stats (from advanced analyzer)
    original_risk_score: Optional[int] = None
    code_blocks_found: int = 0
    findings_in_code_blocks: int = 0
    severity_adjustments: int = 0
    scanner_version: Optional[str] = None


class ScanExport(BaseModel):
    """Exportable scan report"""

    skill_name: str
    skill_id: str
    scan: ScanDetail
    detection_standards: List[dict] = []
    export_date: datetime
    export_format: str = "json"
>>>>>>> Stashed changes
