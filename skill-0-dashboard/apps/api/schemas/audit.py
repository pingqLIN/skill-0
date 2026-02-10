<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
"""Audit event schemas for the Governance Dashboard API"""

from datetime import datetime
from typing import List, Optional, Any

from pydantic import BaseModel


class AuditEvent(BaseModel):
    """An audit log event"""

    event_id: str
    timestamp: datetime
    event_type: str
    skill_id: Optional[str] = None
    skill_name: Optional[str] = None
    actor: str
    details: Optional[dict[str, Any]] = None


class AuditListResponse(BaseModel):
    """Paginated list of audit events"""

    items: List[AuditEvent]
    total: int
    page: int
    page_size: int
=======
=======
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
"""Audit event schemas for the Governance Dashboard API"""

from datetime import datetime
from typing import List, Optional, Any

from pydantic import BaseModel


class AuditEvent(BaseModel):
    """An audit log event"""

    event_id: str
    timestamp: datetime
    event_type: str
    skill_id: Optional[str] = None
    skill_name: Optional[str] = None
    actor: str
    details: Optional[dict[str, Any]] = None


class AuditListResponse(BaseModel):
    """Paginated list of audit events"""

    items: List[AuditEvent]
    total: int
    page: int
    page_size: int
<<<<<<< Updated upstream
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
