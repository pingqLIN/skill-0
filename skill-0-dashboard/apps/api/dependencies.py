<<<<<<< Updated upstream
"""Dependency injection for the Governance Dashboard API"""

from functools import lru_cache
from .services.governance import GovernanceService


@lru_cache()
def get_governance_service() -> GovernanceService:
    """Get a cached GovernanceService instance"""
    return GovernanceService()
=======
"""Dependency injection for the Governance Dashboard API"""

from functools import lru_cache
from .services.governance import GovernanceService


@lru_cache()
def get_governance_service() -> GovernanceService:
    """Get a cached GovernanceService instance"""
    return GovernanceService()
>>>>>>> Stashed changes
