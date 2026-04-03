"""Review action schemas for the Governance Dashboard API"""

from pydantic import BaseModel, ConfigDict


class ReviewAction(BaseModel):
    """Request body for approve/reject actions"""

    model_config = ConfigDict(extra="forbid")

    reason: str
