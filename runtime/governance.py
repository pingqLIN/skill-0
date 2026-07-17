from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sqlite3
from typing import Any, Protocol

from .digest import canonical_digest
from .validators import RuntimeContractValidationError


class RuntimeGovernanceError(RuntimeContractValidationError):
    """Fail-closed governance decision with a stable public reason code."""

    def __init__(self, reason_code: str) -> None:
        self.reason_code = reason_code
        super().__init__(reason_code)


class RuntimeGovernanceGate(Protocol):
    def evaluate(
        self,
        skill_document: dict[str, Any],
        contract: dict[str, Any],
        *,
        canonical_asset_id: str | None = None,
    ) -> dict[str, Any]: ...


class SQLiteRuntimeGovernanceGate:
    """Read-only gate over the revision-aware governance database."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def evaluate(
        self,
        skill_document: dict[str, Any],
        contract: dict[str, Any],
        *,
        canonical_asset_id: str | None = None,
    ) -> dict[str, Any]:
        if not self.path.exists():
            raise RuntimeGovernanceError("GOVERNANCE_DB_UNAVAILABLE")
        canonical_skill_id = str(
            canonical_asset_id or skill_document.get("meta", {}).get("skill_id", "")
        )
        if not canonical_skill_id:
            raise RuntimeGovernanceError("GOVERNANCE_SKILL_ID_MISSING")
        artifact_digest = canonical_digest(skill_document)

        uri = f"{self.path.resolve().as_uri()}?mode=ro"
        try:
            connection = sqlite3.connect(uri, uri=True)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA query_only=ON")
            row = connection.execute(
                """SELECT
                       s.skill_id AS governance_skill_id,
                       s.canonical_skill_id,
                       s.current_revision_id,
                       sr.revision_id,
                       sr.revision_number,
                       sr.status AS revision_status,
                       sr.version,
                       sr.artifact_digest,
                       sr.approved_by,
                       sr.approved_at,
                       sr.is_current
                   FROM skills s
                   LEFT JOIN skill_revisions sr
                     ON sr.revision_id=s.current_revision_id
                    AND sr.skill_id=s.skill_id
                   WHERE s.canonical_skill_id=?""",
                (canonical_skill_id,),
            ).fetchone()
        except sqlite3.DatabaseError as exc:
            raise RuntimeGovernanceError("GOVERNANCE_DB_INVALID") from exc
        finally:
            if "connection" in locals():
                connection.close()

        if row is None:
            raise RuntimeGovernanceError("GOVERNANCE_SKILL_NOT_REGISTERED")
        if not row["current_revision_id"] or not row["revision_id"]:
            raise RuntimeGovernanceError("GOVERNANCE_CURRENT_REVISION_MISSING")
        if row["current_revision_id"] != row["revision_id"] or not bool(
            row["is_current"]
        ):
            raise RuntimeGovernanceError("GOVERNANCE_REVISION_NOT_CURRENT")
        if row["revision_status"] != "approved":
            raise RuntimeGovernanceError("GOVERNANCE_REVISION_NOT_APPROVED")
        if str(row["version"] or "") != str(contract["skill_ref"]["version"]):
            raise RuntimeGovernanceError("GOVERNANCE_VERSION_MISMATCH")

        if row["canonical_skill_id"] != canonical_skill_id:
            raise RuntimeGovernanceError("GOVERNANCE_SKILL_ID_MISMATCH")
        if row["artifact_digest"] != artifact_digest:
            raise RuntimeGovernanceError("GOVERNANCE_ARTIFACT_DIGEST_MISMATCH")
        approved_by = str(row["approved_by"] or "").strip()
        approved_at = str(row["approved_at"] or "").strip()
        if not approved_by or not approved_at:
            raise RuntimeGovernanceError("GOVERNANCE_APPROVAL_PROVENANCE_MISSING")
        try:
            datetime.fromisoformat(approved_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise RuntimeGovernanceError(
                "GOVERNANCE_APPROVAL_PROVENANCE_INVALID"
            ) from exc

        return {
            "policy": "governance.current_revision.approved",
            "canonical_skill_id": canonical_skill_id,
            "governance_skill_id": str(row["governance_skill_id"]),
            "revision_id": str(row["revision_id"]),
            "revision_number": int(row["revision_number"]),
            "artifact_digest": artifact_digest,
            "approved_by": approved_by,
            "approved_at": approved_at,
        }
