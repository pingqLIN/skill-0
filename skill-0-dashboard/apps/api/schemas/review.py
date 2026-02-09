"""Review action schemas for the Governance Dashboard API"""

from pydantic import BaseModel


class ReviewAction(BaseModel):
    """Request body for approve/reject actions"""

    reason: str
    reviewer: str = "admin"
