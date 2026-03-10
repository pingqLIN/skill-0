"""Action schemas for the Governance Dashboard API"""

from typing import List, Literal, Optional

from pydantic import BaseModel


class ActionReadiness(BaseModel):
    """Readiness status for governance actions on a skill"""

    skill_id: str
    can_scan: bool
    can_test: bool
    source_path_exists: bool
    installed_path_exists: bool
    reasons: List[str] = []


class ActionResult(BaseModel):
    """Result of a governance action (scan or test)"""

    status: Literal["success", "failed", "noop", "partial"]
    skill_id: Optional[str] = None
    processed: int = 0
    results: List[dict] = []
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    hint: Optional[str] = None
