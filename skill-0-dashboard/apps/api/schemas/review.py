"""Review action schemas for the Governance Dashboard API"""

from pydantic import BaseModel, ConfigDict, Field


class ReviewAction(BaseModel):
    """Request body for approve/reject actions"""

    model_config = ConfigDict(extra="forbid")

    reason: str


class RuntimeBindingAction(BaseModel):
    """Explicit canonical identity selected by a governance reviewer."""

    model_config = ConfigDict(extra="forbid")

    canonical_skill_id: str = Field(
        pattern=r"^(?:claude|mcp)__[a-z0-9_]+__[a-z0-9][a-z0-9_.-]*$",
        max_length=200,
    )
