"""Action schemas for the Governance Dashboard API"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel


class ActionReadiness(BaseModel):
    """Readiness status for governance actions on a skill"""

    skill_id: str
    revision_id: Optional[str] = None
    can_scan: bool
    can_test: bool
    source_path_exists: bool
    installed_path_exists: bool
    reasons: List[str] = []


class ActionResult(BaseModel):
    """Result of a governance action (scan or test)"""

    status: Literal["success", "failed", "noop", "partial"]
    skill_id: Optional[str] = None
    revision_id: Optional[str] = None
    processed: int = 0
    results: List[dict] = []
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    hint: Optional[str] = None


JobType = Literal["scan_batch", "test_batch"]
JobStatus = Literal[
    "queued",
    "running",
    "completed",
    "completed_with_failures",
    "failed",
    "cancelled",
]
ItemStatus = Literal["queued", "running", "succeeded", "failed", "skipped", "retrying", "cancelled"]
SelectionMode = Literal["explicit", "pending", "retry_failures", "retry_item"]


class ActionJobRequest(BaseModel):
    """Request payload for async scan/test job creation."""

    skill_ids: List[str] = []
    selection_mode: SelectionMode = "explicit"
    max_attempts: int = 2


class ActionJobSummaryCounts(BaseModel):
    """Per-status item counts for a governance action job."""

    total: int = 0
    queued: int = 0
    running: int = 0
    succeeded: int = 0
    failed: int = 0
    retrying: int = 0
    skipped: int = 0
    cancelled: int = 0


class ActionJobSummary(BaseModel):
    """Top-level async job status payload."""

    job_id: str
    job_type: JobType
    status: JobStatus
    requested_by: str
    selection_mode: SelectionMode
    queued_items: int = 0
    max_attempts: int = 2
    queued_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancelled_by: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    active_workers: List[str] = []
    active_lease_expires_at: Optional[datetime] = None
    last_item_started_at: Optional[datetime] = None
    last_item_completed_at: Optional[datetime] = None
    summary: ActionJobSummaryCounts


class ActionJobItem(BaseModel):
    """A single job item tracked within an async governance batch."""

    item_id: str
    job_id: str
    skill_id: str
    target_revision_id: Optional[str] = None
    action_type: Literal["scan", "test"]
    status: ItemStatus
    attempt_number: int = 1
    max_attempts: int = 2
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    claimed_by: Optional[str] = None
    lease_expires_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    retry_of_item_id: Optional[str] = None
    suggested_next_step: Optional[str] = None
