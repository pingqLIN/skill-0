"""SKILL-0 ARD runtime-governance reference scaffold.

This package is additive and dry-run-first. It does not replace the existing
parser, registry, semantic search, governance dashboard, or framework runtime.
"""

from .evidence import build_evidence_summary
from .executor import RuntimeExecutor
from .ledger import RuntimeLedger
from .models import ActionResult, RunResult, RunStatus, RuntimeEvent, RuntimeEventType
from .recovery import RecoveryCoordinator

__all__ = [
    "ActionResult",
    "RecoveryCoordinator",
    "RunResult",
    "RunStatus",
    "RuntimeEvent",
    "RuntimeEventType",
    "RuntimeExecutor",
    "RuntimeLedger",
    "build_evidence_summary",
]
