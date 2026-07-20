#!/usr/bin/env python3
"""
Skill Governance Database

SQLite database for tracking skill metadata, security scans, equivalence tests, and audit logs.

Schema Version: 1.0.0
Author: skill-0 project
Created: 2026-01-27
"""

import os
import sys
import json
import re
import sqlite3
import uuid
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from dataclasses import dataclass


# Default database location
DEFAULT_DB_PATH = Path(__file__).parent.parent / "governance" / "db" / "governance.db"


@dataclass
class SkillRecord:
    """A skill record from the database"""

    skill_id: str
    name: str
    version: str
    status: str  # pending, approved, rejected, blocked
    source_type: str
    source_url: str
    source_commit: Optional[str]
    source_path: str
    original_format: Optional[str]
    fetched_at: Optional[str]
    author_name: str
    author_email: Optional[str]
    author_url: Optional[str]
    author_org: Optional[str]
    license_spdx: str
    license_url: Optional[str]
    requires_attribution: bool
    commercial_allowed: bool
    modification_allowed: bool
    converted_at: Optional[str]
    converter_version: Optional[str]
    target_format: Optional[str]
    security_scanned_at: Optional[str]
    scanner_version: Optional[str]
    risk_level: str
    risk_score: int
    approved_by: Optional[str]
    approved_at: Optional[str]
    equivalence_tested_at: Optional[str]
    equivalence_score: Optional[float]
    equivalence_passed: Optional[bool]
    installed_path: Optional[str]
    installed_at: Optional[str]
    created_at: str
    updated_at: str
    current_revision_id: Optional[str] = None
    revision_id: Optional[str] = None
    revision_number: Optional[int] = None
    source_checksum: Optional[str] = None
    canonical_skill_id: Optional[str] = None
    artifact_digest: Optional[str] = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "SkillRecord":
        keys = set(row.keys())
        return cls(
            skill_id=row["skill_id"],
            name=row["name"],
            version=row["version"],
            status=row["status"],
            source_type=row["source_type"],
            source_url=row["source_url"] or "",
            source_commit=row["source_commit"],
            source_path=row["source_path"] or "",
            original_format=row["original_format"],
            fetched_at=row["fetched_at"],
            author_name=row["author_name"] or "Unknown",
            author_email=row["author_email"],
            author_url=row["author_url"],
            author_org=row["author_org"],
            license_spdx=row["license_spdx"] or "UNKNOWN",
            license_url=row["license_url"],
            requires_attribution=bool(row["requires_attribution"]),
            commercial_allowed=bool(row["commercial_allowed"]),
            modification_allowed=bool(row["modification_allowed"]),
            converted_at=row["converted_at"],
            converter_version=row["converter_version"],
            target_format=row["target_format"],
            security_scanned_at=row["security_scanned_at"],
            scanner_version=row["scanner_version"],
            risk_level=row["risk_level"] or "unknown",
            risk_score=row["risk_score"] or 0,
            approved_by=row["approved_by"],
            approved_at=row["approved_at"],
            equivalence_tested_at=row["equivalence_tested_at"],
            equivalence_score=row["equivalence_score"],
            equivalence_passed=bool(row["equivalence_passed"]) if row["equivalence_passed"] is not None else None,
            installed_path=row["installed_path"],
            installed_at=row["installed_at"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            current_revision_id=row["current_revision_id"] if "current_revision_id" in keys else None,
            revision_id=row["revision_id"] if "revision_id" in keys else None,
            revision_number=row["revision_number"] if "revision_number" in keys else None,
            source_checksum=row["source_checksum"] if "source_checksum" in keys else None,
            canonical_skill_id=(
                row["canonical_skill_id"]
                if "canonical_skill_id" in keys
                else None
            ),
            artifact_digest=(
                row["artifact_digest"] if "artifact_digest" in keys else None
            ),
        )


@dataclass
class SkillRevisionRecord:
    """A skill revision record from the database"""

    revision_id: str
    skill_id: str
    revision_number: int
    status: str
    version: str
    source_type: Optional[str]
    source_url: Optional[str]
    source_commit: Optional[str]
    source_path: Optional[str]
    original_format: Optional[str]
    fetched_at: Optional[str]
    converted_at: Optional[str]
    converter_version: Optional[str]
    target_format: Optional[str]
    security_scanned_at: Optional[str]
    scanner_version: Optional[str]
    risk_level: Optional[str]
    risk_score: int
    approved_by: Optional[str]
    approved_at: Optional[str]
    equivalence_tested_at: Optional[str]
    equivalence_score: Optional[float]
    equivalence_passed: Optional[bool]
    installed_path: Optional[str]
    installed_at: Optional[str]
    source_checksum: Optional[str]
    artifact_digest: Optional[str]
    provenance_json: Optional[str]
    is_current: bool
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "SkillRevisionRecord":
        return cls(
            revision_id=row["revision_id"],
            skill_id=row["skill_id"],
            revision_number=row["revision_number"],
            status=row["status"],
            version=row["version"] or "1.0.0",
            source_type=row["source_type"],
            source_url=row["source_url"],
            source_commit=row["source_commit"],
            source_path=row["source_path"],
            original_format=row["original_format"],
            fetched_at=row["fetched_at"],
            converted_at=row["converted_at"],
            converter_version=row["converter_version"],
            target_format=row["target_format"],
            security_scanned_at=row["security_scanned_at"],
            scanner_version=row["scanner_version"],
            risk_level=row["risk_level"],
            risk_score=row["risk_score"] or 0,
            approved_by=row["approved_by"],
            approved_at=row["approved_at"],
            equivalence_tested_at=row["equivalence_tested_at"],
            equivalence_score=row["equivalence_score"],
            equivalence_passed=bool(row["equivalence_passed"]) if row["equivalence_passed"] is not None else None,
            installed_path=row["installed_path"],
            installed_at=row["installed_at"],
            source_checksum=row["source_checksum"],
            artifact_digest=(
                row["artifact_digest"]
                if "artifact_digest" in set(row.keys())
                else None
            ),
            provenance_json=row["provenance_json"],
            is_current=bool(row["is_current"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


class GovernanceTargetError(ValueError):
    """Stable failure for a missing or stale revision-targeted write."""

    def __init__(
        self,
        code: str,
        *,
        skill_id: str,
        target_revision_id: Optional[str] = None,
        current_revision_id: Optional[str] = None,
    ):
        self.code = code
        self.skill_id = skill_id
        self.target_revision_id = target_revision_id
        self.current_revision_id = current_revision_id
        super().__init__(f"{code}: governance target is not writable")


class GovernanceDB:
    """SQLite database for skill governance"""

    SCHEMA_VERSION = "1.3.0"
    SKILL_MUTABLE_FIELDS = {
        "name",
        "author_name",
        "author_email",
        "author_url",
        "author_org",
        "license_spdx",
        "license_url",
        "requires_attribution",
        "commercial_allowed",
        "modification_allowed",
    }
    REVISION_MUTABLE_STATE_FIELDS = {
        "status",
    }

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _table_columns(self, conn: sqlite3.Connection, table: str) -> set[str]:
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table})")
        return {row["name"] for row in cursor.fetchall()}

    def _decode_json_field(self, raw_value: Optional[str], default: Any) -> Any:
        if raw_value in (None, ""):
            return default
        try:
            return json.loads(raw_value)
        except (TypeError, json.JSONDecodeError):
            return default

    def _ensure_column(self, conn: sqlite3.Connection, table: str, definition: str) -> None:
        column_name = definition.split()[0]
        if column_name not in self._table_columns(conn, table):
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {definition}")

    def _compute_source_checksum(self, payload: Dict[str, Any]) -> str:
        checksum_payload = {
            "source_type": payload.get("source_type") or "",
            "source_url": payload.get("source_url") or "",
            "source_commit": payload.get("source_commit") or "",
            "source_path": payload.get("source_path") or "",
            "version": payload.get("version") or "",
            "fetched_at": payload.get("fetched_at") or "",
            "converted_at": payload.get("converted_at") or "",
        }
        encoded = json.dumps(checksum_payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _skill_projection_query(self) -> str:
        return """
            SELECT
                s.skill_id AS skill_id,
                s.canonical_skill_id AS canonical_skill_id,
                s.name AS name,
                COALESCE(sr.version, s.version) AS version,
                COALESCE(sr.status, s.status) AS status,
                COALESCE(sr.source_type, s.source_type) AS source_type,
                COALESCE(sr.source_url, s.source_url) AS source_url,
                COALESCE(sr.source_commit, s.source_commit) AS source_commit,
                COALESCE(sr.source_path, s.source_path) AS source_path,
                COALESCE(sr.original_format, s.original_format) AS original_format,
                COALESCE(sr.fetched_at, s.fetched_at) AS fetched_at,
                s.author_name AS author_name,
                s.author_email AS author_email,
                s.author_url AS author_url,
                s.author_org AS author_org,
                s.license_spdx AS license_spdx,
                s.license_url AS license_url,
                s.requires_attribution AS requires_attribution,
                s.commercial_allowed AS commercial_allowed,
                s.modification_allowed AS modification_allowed,
                COALESCE(sr.converted_at, s.converted_at) AS converted_at,
                COALESCE(sr.converter_version, s.converter_version) AS converter_version,
                COALESCE(sr.target_format, s.target_format) AS target_format,
                COALESCE(sr.security_scanned_at, s.security_scanned_at) AS security_scanned_at,
                COALESCE(sr.scanner_version, s.scanner_version) AS scanner_version,
                COALESCE(sr.risk_level, s.risk_level) AS risk_level,
                COALESCE(sr.risk_score, s.risk_score) AS risk_score,
                COALESCE(sr.approved_by, s.approved_by) AS approved_by,
                COALESCE(sr.approved_at, s.approved_at) AS approved_at,
                COALESCE(sr.equivalence_tested_at, s.equivalence_tested_at) AS equivalence_tested_at,
                COALESCE(sr.equivalence_score, s.equivalence_score) AS equivalence_score,
                COALESCE(sr.equivalence_passed, s.equivalence_passed) AS equivalence_passed,
                COALESCE(sr.installed_path, s.installed_path) AS installed_path,
                COALESCE(sr.installed_at, s.installed_at) AS installed_at,
                s.created_at AS created_at,
                COALESCE(sr.updated_at, s.updated_at) AS updated_at,
                s.current_revision_id AS current_revision_id,
                sr.revision_id AS revision_id,
                sr.revision_number AS revision_number,
                sr.source_checksum AS source_checksum,
                sr.artifact_digest AS artifact_digest
            FROM skills s
            LEFT JOIN skill_revisions sr ON sr.revision_id = s.current_revision_id
        """

    def _resolve_current_target(
        self,
        conn: sqlite3.Connection,
        *,
        skill_id: str,
        revision_id: Optional[str] = None,
    ) -> sqlite3.Row:
        """Resolve one exact current revision inside the caller's write transaction."""
        row = conn.execute(
            """
            SELECT
                s.skill_id,
                s.name,
                s.canonical_skill_id,
                s.current_revision_id,
                sr.revision_id,
                sr.status,
                sr.artifact_digest
            FROM skills s
            LEFT JOIN skill_revisions sr
              ON sr.revision_id = s.current_revision_id
             AND sr.skill_id = s.skill_id
             AND sr.is_current = 1
            WHERE s.skill_id = ?
            """,
            (skill_id,),
        ).fetchone()
        if row is None:
            raise GovernanceTargetError("SKILL_NOT_FOUND", skill_id=skill_id)

        current_revision_id = row["current_revision_id"]
        if not current_revision_id or row["revision_id"] != current_revision_id:
            raise GovernanceTargetError(
                "CURRENT_TARGET_UNAVAILABLE",
                skill_id=skill_id,
                target_revision_id=revision_id,
                current_revision_id=current_revision_id,
            )
        if revision_id is not None and revision_id != current_revision_id:
            raise GovernanceTargetError(
                "STALE_TARGET_REVISION",
                skill_id=skill_id,
                target_revision_id=revision_id,
                current_revision_id=current_revision_id,
            )
        return row

    def _has_prior_authority_failure(
        self,
        conn: sqlite3.Connection,
        *,
        skill_id: str,
        current_revision_id: str,
    ) -> bool:
        """Return whether immutable history records a prior authority failure."""
        projected_failure = conn.execute(
            """SELECT 1 FROM skill_revisions
               WHERE skill_id=? AND revision_id<>?
                 AND status IN ('rejected', 'blocked')
               LIMIT 1""",
            (skill_id, current_revision_id),
        ).fetchone()
        if projected_failure is not None:
            return True

        persisted_block = conn.execute(
            """SELECT 1 FROM security_scans
               WHERE skill_id=? AND revision_id IS NOT NULL AND revision_id<>?
                 AND blocked=1
               LIMIT 1""",
            (skill_id, current_revision_id),
        ).fetchone()
        if persisted_block is not None:
            return True

        events = conn.execute(
            """SELECT event_type, details_json FROM audit_log
               WHERE skill_id=? AND revision_id IS NOT NULL AND revision_id<>?
                 AND event_type IN ('reject', 'scan')""",
            (skill_id, current_revision_id),
        ).fetchall()
        for event in events:
            if event["event_type"] == "reject":
                return True
            details = self._decode_json_field(event["details_json"], {})
            if isinstance(details, dict) and details.get("blocked") is True:
                return True
        return False

    def _fresh_reapproval_evidence(
        self,
        conn: sqlite3.Connection,
        *,
        skill_id: str,
        revision_id: str,
        canonical_skill_id: str,
        artifact_digest: str,
        not_before: Optional[str] = None,
    ) -> Optional[Dict[str, str]]:
        """Resolve server-recorded scan/test evidence created after exact binding."""
        binding = conn.execute(
            """SELECT event_id, timestamp, details_json FROM audit_log
               WHERE skill_id=? AND revision_id=? AND event_type='runtime_bind'
               ORDER BY timestamp DESC LIMIT 1""",
            (skill_id, revision_id),
        ).fetchone()
        if binding is None:
            return None
        binding_details = self._decode_json_field(binding["details_json"], {})
        if (
            not isinstance(binding_details, dict)
            or binding_details.get("canonical_skill_id") != canonical_skill_id
            or binding_details.get("artifact_digest") != artifact_digest
        ):
            return None
        evidence_cutoff = max(
            timestamp
            for timestamp in (binding["timestamp"], not_before)
            if timestamp is not None
        )

        def resolve_evidence(event_type: str, id_field: str, table: str) -> Optional[str]:
            event = conn.execute(
                """SELECT event_id, details_json FROM audit_log
                   WHERE skill_id=? AND revision_id=? AND event_type=? AND timestamp>=?
                   ORDER BY timestamp DESC, rowid DESC LIMIT 1""",
                (skill_id, revision_id, event_type, evidence_cutoff),
            ).fetchone()
            if event is None:
                return None
            details = self._decode_json_field(event["details_json"], {})
            evidence_id = details.get(id_field) if isinstance(details, dict) else None
            if not isinstance(evidence_id, str) or not evidence_id:
                return None
            if table == "security_scans":
                evidence = conn.execute(
                    """SELECT scan_id FROM security_scans
                       WHERE scan_id=? AND skill_id=? AND revision_id=? AND blocked=0""",
                    (evidence_id, skill_id, revision_id),
                ).fetchone()
            else:
                evidence = conn.execute(
                    """SELECT test_id FROM equivalence_tests
                       WHERE test_id=? AND skill_id=? AND revision_id=? AND passed=1""",
                    (evidence_id, skill_id, revision_id),
                ).fetchone()
            return evidence_id if evidence is not None else None

        scan_id = resolve_evidence("scan", "scan_id", "security_scans")
        test_id = resolve_evidence("test", "test_id", "equivalence_tests")
        if scan_id is None or test_id is None:
            return None
        return {
            "policy": "governance.fresh-reapproval.v1",
            "revision_id": revision_id,
            "canonical_skill_id": canonical_skill_id,
            "artifact_digest": artifact_digest,
            "binding_event_id": binding["event_id"],
            "scan_id": scan_id,
            "test_id": test_id,
        }

    def _blocked_remediation_cutoff(
        self,
        conn: sqlite3.Connection,
        *,
        skill_id: str,
        revision_id: str,
    ) -> Optional[str]:
        """Return the latest application-authorized blocked-to-pending reset."""
        events = conn.execute(
            """SELECT timestamp, previous_state_json, new_state_json
               FROM audit_log
               WHERE skill_id=? AND revision_id=?
                 AND event_type='revision_state_update'
               ORDER BY timestamp DESC""",
            (skill_id, revision_id),
        ).fetchall()
        for event in events:
            previous = self._decode_json_field(event["previous_state_json"], {})
            new = self._decode_json_field(event["new_state_json"], {})
            if (
                isinstance(previous, dict)
                and isinstance(new, dict)
                and previous.get("status") == "blocked"
                and new.get("status") == "pending"
            ):
                return event["timestamp"]
        return None

    def _revision_payload_from_row(self, row: sqlite3.Row) -> Dict[str, Any]:
        payload = {
            "version": row["version"] or "1.0.0",
            "status": row["status"] or "pending",
            "source_type": row["source_type"],
            "source_url": row["source_url"],
            "source_commit": row["source_commit"],
            "source_path": row["source_path"],
            "original_format": row["original_format"],
            "fetched_at": row["fetched_at"],
            "converted_at": row["converted_at"],
            "converter_version": row["converter_version"],
            "target_format": row["target_format"],
            "security_scanned_at": row["security_scanned_at"],
            "scanner_version": row["scanner_version"],
            "risk_level": row["risk_level"],
            "risk_score": row["risk_score"] or 0,
            "security_findings": row["security_findings"],
            "approved_by": row["approved_by"],
            "approved_at": row["approved_at"],
            "equivalence_tested_at": row["equivalence_tested_at"],
            "equivalence_score": row["equivalence_score"],
            "semantic_similarity": row["semantic_similarity"],
            "structure_similarity": row["structure_similarity"],
            "keyword_similarity": row["keyword_similarity"],
            "equivalence_passed": row["equivalence_passed"],
            "installed_path": row["installed_path"],
            "installed_at": row["installed_at"],
            "artifact_digest": (
                row["artifact_digest"]
                if "artifact_digest" in set(row.keys())
                else None
            ),
        }
        payload["source_checksum"] = self._compute_source_checksum(payload)
        payload["provenance_json"] = json.dumps(
            {
                "source_type": payload["source_type"],
                "source_url": payload["source_url"],
                "source_commit": payload["source_commit"],
                "source_path": payload["source_path"],
                "fetched_at": payload["fetched_at"],
            }
        )
        return payload

    def _create_revision(
        self,
        conn: sqlite3.Connection,
        skill_id: str,
        payload: Dict[str, Any],
        *,
        revision_number: Optional[int] = None,
        is_current: bool = True,
    ) -> str:
        cursor = conn.cursor()
        if revision_number is None:
            cursor.execute(
                "SELECT COALESCE(MAX(revision_number), 0) + 1 FROM skill_revisions WHERE skill_id = ?",
                (skill_id,),
            )
            revision_number = cursor.fetchone()[0]

        revision_id = self.generate_id()
        now = datetime.now().isoformat()
        checksum = payload.get("source_checksum") or self._compute_source_checksum(payload)
        provenance_json = payload.get("provenance_json")
        if provenance_json is None:
            provenance_json = json.dumps(
                {
                    "source_type": payload.get("source_type"),
                    "source_url": payload.get("source_url"),
                    "source_commit": payload.get("source_commit"),
                    "source_path": payload.get("source_path"),
                    "fetched_at": payload.get("fetched_at"),
                }
            )

        if is_current:
            cursor.execute(
                "UPDATE skill_revisions SET is_current = 0, updated_at = ? WHERE skill_id = ? AND is_current = 1",
                (now, skill_id),
            )

        cursor.execute(
            """
            INSERT INTO skill_revisions (
                revision_id, skill_id, revision_number, version, status,
                source_type, source_url, source_commit, source_path, original_format, fetched_at,
                converted_at, converter_version, target_format,
                security_scanned_at, scanner_version, risk_level, risk_score, security_findings,
                approved_by, approved_at,
                equivalence_tested_at, equivalence_score, semantic_similarity, structure_similarity,
                keyword_similarity, equivalence_passed,
                installed_path, installed_at,
                source_checksum, artifact_digest, provenance_json,
                is_current, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                revision_id,
                skill_id,
                revision_number,
                payload.get("version", "1.0.0"),
                payload.get("status", "pending"),
                payload.get("source_type"),
                payload.get("source_url"),
                payload.get("source_commit"),
                payload.get("source_path"),
                payload.get("original_format"),
                payload.get("fetched_at"),
                payload.get("converted_at"),
                payload.get("converter_version"),
                payload.get("target_format"),
                payload.get("security_scanned_at"),
                payload.get("scanner_version"),
                payload.get("risk_level"),
                payload.get("risk_score", 0),
                payload.get("security_findings"),
                payload.get("approved_by"),
                payload.get("approved_at"),
                payload.get("equivalence_tested_at"),
                payload.get("equivalence_score"),
                payload.get("semantic_similarity"),
                payload.get("structure_similarity"),
                payload.get("keyword_similarity"),
                payload.get("equivalence_passed"),
                payload.get("installed_path"),
                payload.get("installed_at"),
                checksum,
                payload.get("artifact_digest"),
                provenance_json,
                1 if is_current else 0,
                payload.get("created_at", now),
                payload.get("updated_at", now),
            ),
        )

        if is_current:
            cursor.execute(
                """
                UPDATE skills SET
                    current_revision_id = ?,
                    version = ?,
                    status = ?,
                    source_type = ?,
                    source_url = ?,
                    source_commit = ?,
                    source_path = ?,
                    original_format = ?,
                    fetched_at = ?,
                    converted_at = ?,
                    converter_version = ?,
                    target_format = ?,
                    security_scanned_at = ?,
                    scanner_version = ?,
                    risk_level = ?,
                    risk_score = ?,
                    security_findings = ?,
                    approved_by = ?,
                    approved_at = ?,
                    equivalence_tested_at = ?,
                    equivalence_score = ?,
                    semantic_similarity = ?,
                    structure_similarity = ?,
                    keyword_similarity = ?,
                    equivalence_passed = ?,
                    installed_path = ?,
                    installed_at = ?,
                    updated_at = ?
                WHERE skill_id = ?
                """,
                (
                    revision_id,
                    payload.get("version", "1.0.0"),
                    payload.get("status", "pending"),
                    payload.get("source_type"),
                    payload.get("source_url"),
                    payload.get("source_commit"),
                    payload.get("source_path"),
                    payload.get("original_format"),
                    payload.get("fetched_at"),
                    payload.get("converted_at"),
                    payload.get("converter_version"),
                    payload.get("target_format"),
                    payload.get("security_scanned_at"),
                    payload.get("scanner_version"),
                    payload.get("risk_level"),
                    payload.get("risk_score", 0),
                    payload.get("security_findings"),
                    payload.get("approved_by"),
                    payload.get("approved_at"),
                    payload.get("equivalence_tested_at"),
                    payload.get("equivalence_score"),
                    payload.get("semantic_similarity"),
                    payload.get("structure_similarity"),
                    payload.get("keyword_similarity"),
                    payload.get("equivalence_passed"),
                    payload.get("installed_path"),
                    payload.get("installed_at"),
                    now,
                    skill_id,
                ),
            )

        return revision_id

    def _backfill_revisions(self, conn: sqlite3.Connection) -> None:
        """Ensure every skill has at least one immutable revision row."""
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM skills ORDER BY created_at ASC")
        skills = cursor.fetchall()

        for row in skills:
            cursor.execute(
                "SELECT revision_id FROM skill_revisions WHERE skill_id = ? ORDER BY revision_number ASC LIMIT 1",
                (row["skill_id"],),
            )
            existing_revision = cursor.fetchone()
            current_revision_id = row["current_revision_id"] if "current_revision_id" in set(row.keys()) else None

            if existing_revision:
                if not current_revision_id:
                    cursor.execute(
                        "UPDATE skills SET current_revision_id = ?, updated_at = ? WHERE skill_id = ?",
                        (existing_revision["revision_id"], datetime.now().isoformat(), row["skill_id"]),
                    )
                cursor.execute(
                    "UPDATE skill_revisions SET is_current = CASE WHEN revision_id = ? THEN 1 ELSE 0 END WHERE skill_id = ?",
                    (current_revision_id or existing_revision["revision_id"], row["skill_id"]),
                )
                continue

            payload = self._revision_payload_from_row(row)
            payload["created_at"] = row["created_at"]
            payload["updated_at"] = row["updated_at"]
            self._create_revision(
                conn,
                row["skill_id"],
                payload,
                revision_number=1,
                is_current=True,
            )

    def _init_db(self):
        """Initialize database schema"""
        with self.connection() as conn:
            cursor = conn.cursor()

            # Schema version tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version TEXT PRIMARY KEY,
                    applied_at TEXT NOT NULL
                )
            """)

            # Skills table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS skills (
                    skill_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    current_revision_id TEXT,
                    version TEXT DEFAULT '1.0.0',
                    status TEXT DEFAULT 'pending',
                    
                    -- Provenance
                    source_type TEXT,
                    source_url TEXT,
                    source_commit TEXT,
                    source_path TEXT,
                    original_format TEXT,
                    fetched_at TEXT,
                    
                    -- Author
                    author_name TEXT,
                    author_email TEXT,
                    author_url TEXT,
                    author_org TEXT,
                    
                    -- License
                    license_spdx TEXT,
                    license_url TEXT,
                    requires_attribution INTEGER DEFAULT 0,
                    commercial_allowed INTEGER DEFAULT 1,
                    modification_allowed INTEGER DEFAULT 1,
                    
                    -- Conversion
                    converted_at TEXT,
                    converter_version TEXT,
                    target_format TEXT,
                    
                    -- Security
                    security_scanned_at TEXT,
                    scanner_version TEXT,
                    risk_level TEXT,
                    risk_score INTEGER DEFAULT 0,
                    security_findings TEXT,
                    approved_by TEXT,
                    approved_at TEXT,
                    
                    -- Equivalence
                    equivalence_tested_at TEXT,
                    equivalence_score REAL,
                    semantic_similarity REAL,
                    structure_similarity REAL,
                    keyword_similarity REAL,
                    equivalence_passed INTEGER,
                    
                    -- Timestamps
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    
                    -- Installed location
                    installed_path TEXT,
                    installed_at TEXT
                )
            """)
            self._ensure_column(conn, "skills", "current_revision_id TEXT")
            self._ensure_column(conn, "skills", "canonical_skill_id TEXT")

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS skill_revisions (
                    revision_id TEXT PRIMARY KEY,
                    skill_id TEXT NOT NULL,
                    revision_number INTEGER NOT NULL,
                    version TEXT DEFAULT '1.0.0',
                    status TEXT DEFAULT 'pending',
                    source_type TEXT,
                    source_url TEXT,
                    source_commit TEXT,
                    source_path TEXT,
                    original_format TEXT,
                    fetched_at TEXT,
                    converted_at TEXT,
                    converter_version TEXT,
                    target_format TEXT,
                    security_scanned_at TEXT,
                    scanner_version TEXT,
                    risk_level TEXT,
                    risk_score INTEGER DEFAULT 0,
                    security_findings TEXT,
                    approved_by TEXT,
                    approved_at TEXT,
                    equivalence_tested_at TEXT,
                    equivalence_score REAL,
                    semantic_similarity REAL,
                    structure_similarity REAL,
                    keyword_similarity REAL,
                    equivalence_passed INTEGER,
                    installed_path TEXT,
                    installed_at TEXT,
                    source_checksum TEXT,
                    artifact_digest TEXT,
                    provenance_json TEXT,
                    is_current INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (skill_id) REFERENCES skills(skill_id)
                )
            """)
            self._ensure_column(conn, "skill_revisions", "artifact_digest TEXT")

            # Security scans table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS security_scans (
                    scan_id TEXT PRIMARY KEY,
                    skill_id TEXT NOT NULL,
                    revision_id TEXT,
                    scanned_at TEXT NOT NULL,
                    scanner_version TEXT NOT NULL,
                    risk_level TEXT NOT NULL,
                    risk_score INTEGER NOT NULL,
                    files_scanned INTEGER DEFAULT 0,
                    findings_count INTEGER DEFAULT 0,
                    findings_json TEXT,
                    blocked INTEGER DEFAULT 0,
                    blocked_reason TEXT,
                    
                    FOREIGN KEY (skill_id) REFERENCES skills(skill_id)
                )
            """)
            self._ensure_column(conn, "security_scans", "revision_id TEXT")

            # Equivalence tests table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS equivalence_tests (
                    test_id TEXT PRIMARY KEY,
                    skill_id TEXT NOT NULL,
                    revision_id TEXT,
                    tested_at TEXT NOT NULL,
                    tester_version TEXT NOT NULL,
                    original_path TEXT,
                    converted_path TEXT,
                    
                    semantic_similarity REAL,
                    structure_similarity REAL,
                    keyword_similarity REAL,
                    metadata_completeness REAL,
                    overall_score REAL,
                    passed INTEGER DEFAULT 0,
                    
                    details_json TEXT,
                    warnings_json TEXT,
                    errors_json TEXT,
                    
                    FOREIGN KEY (skill_id) REFERENCES skills(skill_id)
                )
            """)
            self._ensure_column(conn, "equivalence_tests", "revision_id TEXT")

            # Audit log table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    event_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    skill_id TEXT,
                    revision_id TEXT,
                    skill_name TEXT,
                    actor TEXT DEFAULT 'system',
                    details_json TEXT,
                    previous_state_json TEXT,
                    new_state_json TEXT
                )
            """)
            self._ensure_column(conn, "audit_log", "revision_id TEXT")

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS action_jobs (
                    job_id TEXT PRIMARY KEY,
                    job_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    requested_by TEXT NOT NULL,
                    selection_mode TEXT NOT NULL,
                    max_attempts INTEGER NOT NULL DEFAULT 2,
                    queued_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    cancelled_at TEXT,
                    cancelled_by TEXT,
                    error_code TEXT,
                    error_message TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            self._ensure_column(conn, "action_jobs", "cancelled_at TEXT")
            self._ensure_column(conn, "action_jobs", "cancelled_by TEXT")

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS action_job_items (
                    item_id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    skill_id TEXT NOT NULL,
                    target_revision_id TEXT,
                    action_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    attempt_number INTEGER NOT NULL,
                    max_attempts INTEGER NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    result_json TEXT,
                    error_code TEXT,
                    error_message TEXT,
                    claimed_by TEXT,
                    lease_expires_at TEXT,
                    retry_of_item_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (job_id) REFERENCES action_jobs(job_id)
                )
            """)
            self._ensure_column(conn, "action_job_items", "claimed_by TEXT")
            self._ensure_column(conn, "action_job_items", "lease_expires_at TEXT")

            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_skills_name ON skills(name)")
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_skills_status ON skills(status)"
            )
            cursor.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_skills_canonical_skill_id "
                "ON skills(canonical_skill_id) WHERE canonical_skill_id IS NOT NULL"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_skills_risk ON skills(risk_level)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_scans_skill ON security_scans(skill_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_tests_skill ON equivalence_tests(skill_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_revisions_skill ON skill_revisions(skill_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_revisions_current ON skill_revisions(skill_id, is_current)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_revisions_artifact_digest "
                "ON skill_revisions(artifact_digest)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_audit_skill ON audit_log(skill_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_audit_revision ON audit_log(revision_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_audit_type ON audit_log(event_type)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_log(timestamp)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_action_jobs_status ON action_jobs(status)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_action_jobs_queued_at ON action_jobs(queued_at)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_action_job_items_job ON action_job_items(job_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_action_job_items_status ON action_job_items(job_id, status)"
            )

            # Check schema version
            cursor.execute(
                "SELECT version FROM schema_version ORDER BY applied_at DESC LIMIT 1"
            )
            row = cursor.fetchone()

            if not row:
                cursor.execute(
                    "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
                    (self.SCHEMA_VERSION, datetime.now().isoformat()),
                )
            elif row["version"] != self.SCHEMA_VERSION:
                cursor.execute(
                    "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
                    (self.SCHEMA_VERSION, datetime.now().isoformat()),
                )

            self._backfill_revisions(conn)

    def generate_id(self) -> str:
        """Generate a unique ID"""
        return str(uuid.uuid4())

    # ============ Skills CRUD ============

    def create_skill(
        self,
        name: str,
        source_type: str = "local",
        source_path: str = "",
        source_url: str = "",
        author_name: str = "Unknown",
        license_spdx: str = "UNKNOWN",
        **kwargs,
    ) -> str:
        """Create a new skill record"""
        skill_id = self.generate_id()
        now = datetime.now().isoformat()

        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO skills (
                    skill_id, name, source_type, source_path, source_url,
                    author_name, license_spdx, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
            """,
                (
                    skill_id,
                    name,
                    source_type,
                    source_path,
                    source_url,
                    author_name,
                    license_spdx,
                    now,
                    now,
                ),
            )

            revision_payload = {
                "version": kwargs.get("version", "1.0.0"),
                "status": kwargs.get("status", "pending"),
                "source_type": source_type,
                "source_url": source_url,
                "source_commit": kwargs.get("source_commit"),
                "source_path": source_path,
                "original_format": kwargs.get("original_format"),
                "fetched_at": kwargs.get("fetched_at"),
                "converted_at": kwargs.get("converted_at"),
                "converter_version": kwargs.get("converter_version"),
                "target_format": kwargs.get("target_format"),
                "installed_path": kwargs.get("installed_path"),
                "installed_at": kwargs.get("installed_at"),
                "created_at": now,
                "updated_at": now,
            }
            revision_id = self._create_revision(conn, skill_id, revision_payload, revision_number=1, is_current=True)

            # Log the creation
            self._log_event(
                conn,
                "create",
                skill_id=skill_id,
                revision_id=revision_id,
                skill_name=name,
                details={"source_type": source_type, "source_path": source_path, "revision_id": revision_id},
            )

        return skill_id

    def get_skill(
        self, skill_id: str = None, name: str = None
    ) -> Optional[SkillRecord]:
        """Get a skill by ID or name"""
        with self.connection() as conn:
            cursor = conn.cursor()
            base_query = self._skill_projection_query()

            if skill_id:
                cursor.execute(f"{base_query} WHERE s.skill_id = ?", (skill_id,))
            elif name:
                cursor.execute(f"{base_query} WHERE s.name = ?", (name,))
            else:
                return None

            row = cursor.fetchone()
            return SkillRecord.from_row(row) if row else None

    def update_skill(self, skill_id: str, **updates) -> bool:
        """Update skill-row metadata only.

        Artifact and revision-bound fields must not be mutated in place via
        this method. Use `register_revision()` for artifact changes and
        `update_current_revision_state()` for narrow workflow state changes.
        """
        if not updates:
            return False

        with self.connection() as conn:
            cursor = conn.cursor()

            # Get previous state for audit
            cursor.execute(self._skill_projection_query() + " WHERE s.skill_id = ?", (skill_id,))
            prev_row = cursor.fetchone()
            if not prev_row:
                return False

            revision_fields = {
                "version",
                "status",
                "source_type",
                "source_url",
                "source_commit",
                "source_path",
                "original_format",
                "fetched_at",
                "converted_at",
                "converter_version",
                "target_format",
                "security_scanned_at",
                "scanner_version",
                "risk_level",
                "risk_score",
                "security_findings",
                "approved_by",
                "approved_at",
                "equivalence_tested_at",
                "equivalence_score",
                "semantic_similarity",
                "structure_similarity",
                "keyword_similarity",
                "equivalence_passed",
                "installed_path",
                "installed_at",
            }

            skill_updates = {k: v for k, v in updates.items() if k in self.SKILL_MUTABLE_FIELDS}
            revision_updates = {k: v for k, v in updates.items() if k in revision_fields}
            invalid_updates = [k for k in updates.keys() if k not in self.SKILL_MUTABLE_FIELDS and k not in revision_fields]

            if invalid_updates:
                raise ValueError(f"Unsupported skill update fields: {', '.join(sorted(invalid_updates))}")
            if revision_updates:
                raise ValueError(
                    "Artifact and revision-bound fields cannot be mutated via update_skill(); "
                    "use register_revision() for artifact changes or update_current_revision_state() "
                    "for allowed revision workflow state."
                )

            now = datetime.now().isoformat()

            if skill_updates:
                skill_updates["updated_at"] = now
                set_clause = ", ".join(f"{k} = ?" for k in skill_updates.keys())
                values = list(skill_updates.values()) + [skill_id]
                cursor.execute(f"UPDATE skills SET {set_clause} WHERE skill_id = ?", values)

            if skill_updates:
                self._log_event(
                    conn,
                    "update",
                    skill_id=skill_id,
                    revision_id=prev_row["current_revision_id"],
                    skill_name=prev_row["name"] if prev_row else None,
                    details=updates,
                    previous_state=dict(prev_row) if prev_row else None,
                )
                return True

        return False

    def update_current_revision_state(self, skill_id: str, **updates) -> bool:
        """Allow only the application remediation transition blocked -> pending."""
        if not updates:
            return False

        invalid_updates = [k for k in updates.keys() if k not in self.REVISION_MUTABLE_STATE_FIELDS]
        if invalid_updates:
            raise ValueError(
                "Unsupported current revision state fields: " + ", ".join(sorted(invalid_updates))
            )

        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(self._skill_projection_query() + " WHERE s.skill_id = ?", (skill_id,))
            prev_row = cursor.fetchone()
            if not prev_row or not prev_row["current_revision_id"]:
                return False
            if updates != {"status": "pending"} or prev_row["status"] != "blocked":
                raise ValueError(
                    "Current revision state updates only allow blocked-to-pending remediation; "
                    "approval requires approve_skill() and rejection requires a new revision"
                )

            now = datetime.now().isoformat()
            revision_updates = dict(updates)
            revision_updates["updated_at"] = now

            set_clause = ", ".join(f"{k} = ?" for k in revision_updates.keys())
            values = list(revision_updates.values()) + [prev_row["current_revision_id"]]
            cursor.execute(f"UPDATE skill_revisions SET {set_clause} WHERE revision_id = ?", values)

            projection_updates = dict(updates)
            projection_updates["updated_at"] = now
            set_clause = ", ".join(f"{k} = ?" for k in projection_updates.keys())
            values = list(projection_updates.values()) + [skill_id]
            cursor.execute(f"UPDATE skills SET {set_clause} WHERE skill_id = ?", values)

            self._log_event(
                conn,
                "revision_state_update",
                skill_id=skill_id,
                revision_id=prev_row["current_revision_id"],
                skill_name=prev_row["name"],
                details=updates,
                previous_state=dict(prev_row),
                new_state={"status": "pending"},
            )
            return True

    def list_skills(
        self,
        status: str = None,
        risk_level: str = None,
        limit: int = 100,
    ) -> List[SkillRecord]:
        """List skills with optional filtering"""
        with self.connection() as conn:
            cursor = conn.cursor()

            query = self._skill_projection_query() + " WHERE 1=1"
            params = []

            if status:
                query += " AND status = ?"
                params.append(status)

            if risk_level:
                query += " AND risk_level = ?"
                params.append(risk_level)

            query += " ORDER BY updated_at DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            return [SkillRecord.from_row(row) for row in cursor.fetchall()]

    def get_current_revision(self, skill_id: str) -> Optional[SkillRevisionRecord]:
        """Return the current revision for a skill."""
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT sr.* FROM skill_revisions sr
                JOIN skills s ON s.current_revision_id = sr.revision_id
                WHERE s.skill_id = ?
                """,
                (skill_id,),
            )
            row = cursor.fetchone()
            return SkillRevisionRecord.from_row(row) if row else None

    def list_revisions(self, skill_id: str, limit: int = 20) -> List[SkillRevisionRecord]:
        """List revisions for a skill, newest first."""
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM skill_revisions
                WHERE skill_id = ?
                ORDER BY revision_number DESC
                LIMIT ?
                """,
                (skill_id, limit),
            )
            return [SkillRevisionRecord.from_row(row) for row in cursor.fetchall()]

    def register_revision(self, skill_id: str, **updates) -> Optional[str]:
        """Create a new current revision for an existing skill."""
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(self._skill_projection_query() + " WHERE s.skill_id = ?", (skill_id,))
            row = cursor.fetchone()
            if not row:
                return None

            now = datetime.now().isoformat()
            payload = dict(row)
            payload.update(updates)
            # A new revision never inherits authority or freshness-sensitive
            # workflow projections. It must be rebound, rescanned, retested,
            # and reviewed through evidence written for its own revision ID.
            payload.update(
                {
                    "artifact_digest": None,
                    "status": "pending",
                    "approved_by": None,
                    "approved_at": None,
                    "security_scanned_at": None,
                    "scanner_version": None,
                    "risk_level": "unknown",
                    "risk_score": 0,
                    "security_findings": None,
                    "equivalence_tested_at": None,
                    "equivalence_score": None,
                    "semantic_similarity": None,
                    "structure_similarity": None,
                    "keyword_similarity": None,
                    "equivalence_passed": None,
                    "installed_path": None,
                    "installed_at": None,
                    "source_checksum": None,
                    "provenance_json": None,
                    "created_at": now,
                    "updated_at": now,
                }
            )
            revision_id = self._create_revision(conn, skill_id, payload, is_current=True)
            self._log_event(
                conn,
                "revision_create",
                skill_id=skill_id,
                revision_id=revision_id,
                skill_name=row["name"],
                details={"updates": updates, "revision_id": revision_id},
            )
            return revision_id

    def bind_runtime_artifact(
        self,
        skill_id: str,
        *,
        canonical_skill_id: str,
        artifact_digest: str,
        bound_by: str,
    ) -> Optional[Dict[str, Any]]:
        """Bind a pending current revision to one exact canonical parsed JSON."""
        if not re.fullmatch(
            r"(?:claude|mcp)__[a-z0-9_]+__[a-z0-9][a-z0-9_.-]*",
            canonical_skill_id,
        ):
            raise ValueError("Invalid canonical skill ID")
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", artifact_digest):
            raise ValueError("Invalid canonical artifact digest")
        actor = bound_by.strip()
        if not actor:
            raise ValueError("Runtime artifact binding actor is required")

        with self.connection() as conn:
            cursor = conn.cursor()
            row = cursor.execute(
                """SELECT
                       s.name,
                       s.canonical_skill_id,
                       s.current_revision_id,
                       sr.status AS revision_status,
                       sr.artifact_digest
                   FROM skills s
                   LEFT JOIN skill_revisions sr
                     ON sr.revision_id=s.current_revision_id
                    AND sr.skill_id=s.skill_id
                   WHERE s.skill_id=?""",
                (skill_id,),
            ).fetchone()
            if row is None or not row["current_revision_id"]:
                return None
            if (
                row["canonical_skill_id"] == canonical_skill_id
                and row["artifact_digest"] == artifact_digest
            ):
                return {
                    "skill_id": skill_id,
                    "canonical_skill_id": canonical_skill_id,
                    "revision_id": row["current_revision_id"],
                    "artifact_digest": artifact_digest,
                }
            if row["revision_status"] != "pending":
                raise ValueError(
                    "Runtime artifact binding requires a pending current revision"
                )
            if row["canonical_skill_id"] not in {None, canonical_skill_id}:
                raise ValueError("Governance skill already has another canonical identity")
            if row["artifact_digest"] not in {None, artifact_digest}:
                raise ValueError("Current revision already has another artifact digest")

            try:
                cursor.execute(
                    "UPDATE skills SET canonical_skill_id=?, updated_at=? WHERE skill_id=?",
                    (canonical_skill_id, datetime.now().isoformat(), skill_id),
                )
            except sqlite3.IntegrityError as exc:
                raise ValueError("Canonical skill ID is already bound") from exc
            cursor.execute(
                """UPDATE skill_revisions
                   SET artifact_digest=?, updated_at=?
                   WHERE revision_id=? AND skill_id=? AND status='pending'""",
                (
                    artifact_digest,
                    datetime.now().isoformat(),
                    row["current_revision_id"],
                    skill_id,
                ),
            )
            if cursor.rowcount != 1:
                raise ValueError("Current revision changed during runtime binding")
            self._log_event(
                conn,
                "runtime_bind",
                skill_id=skill_id,
                revision_id=row["current_revision_id"],
                skill_name=row["name"],
                actor=actor,
                details={
                    "canonical_skill_id": canonical_skill_id,
                    "artifact_digest": artifact_digest,
                },
            )
            return {
                "skill_id": skill_id,
                "canonical_skill_id": canonical_skill_id,
                "revision_id": row["current_revision_id"],
                "artifact_digest": artifact_digest,
            }

    def get_runtime_approval(
        self,
        *,
        canonical_skill_id: str,
        artifact_digest: str,
    ) -> Optional[Dict[str, Any]]:
        """Resolve exact current-revision Runtime approval; ignore skill projection status."""
        with self.connection() as conn:
            row = conn.execute(
                """SELECT
                       s.skill_id AS governance_skill_id,
                       s.canonical_skill_id,
                       sr.revision_id,
                       sr.revision_number,
                       sr.version,
                       sr.status,
                       sr.artifact_digest,
                       sr.approved_by,
                       sr.approved_at
                   FROM skills s
                   JOIN skill_revisions sr
                     ON sr.revision_id=s.current_revision_id
                    AND sr.skill_id=s.skill_id
                   WHERE s.canonical_skill_id=?
                     AND sr.artifact_digest=?
                     AND sr.is_current=1
                     AND sr.status='approved'""",
                (canonical_skill_id, artifact_digest),
            ).fetchone()
            return dict(row) if row is not None else None

    # ============ Security Scans ============

    def record_security_scan(
        self,
        skill_id: str,
        scan_result: Dict[str, Any],
        revision_id: Optional[str] = None,
    ) -> str:
        """Record a security scan result"""
        scan_id = self.generate_id()

        with self.connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            cursor = conn.cursor()
            target = self._resolve_current_target(
                conn,
                skill_id=skill_id,
                revision_id=revision_id,
            )
            current_revision = target["current_revision_id"]

            cursor.execute(
                """
                INSERT INTO security_scans (
                    scan_id, skill_id, revision_id, scanned_at, scanner_version,
                    risk_level, risk_score, files_scanned, findings_count,
                    findings_json, blocked, blocked_reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    scan_id,
                    skill_id,
                    current_revision,
                    scan_result.get("scanned_at", datetime.now().isoformat()),
                    scan_result.get("scanner_version", "1.0.0"),
                    scan_result.get("risk_level", "unknown"),
                    scan_result.get("risk_score", 0),
                    scan_result.get("files_scanned", 0),
                    scan_result.get("findings_count", 0),
                    json.dumps(scan_result.get("findings", [])),
                    1 if scan_result.get("blocked") else 0,
                    scan_result.get("blocked_reason", ""),
                ),
            )

            # Update skill with latest scan
            cursor.execute(
                """
                UPDATE skills SET
                    security_scanned_at = ?,
                    scanner_version = ?,
                    risk_level = ?,
                    risk_score = ?,
                    security_findings = ?,
                    updated_at = ?
                WHERE skill_id = ?
            """,
                (
                    scan_result.get("scanned_at"),
                    scan_result.get("scanner_version"),
                    scan_result.get("risk_level"),
                    scan_result.get("risk_score"),
                    json.dumps(scan_result.get("findings", [])),
                    datetime.now().isoformat(),
                    skill_id,
                ),
            )

            if current_revision:
                cursor.execute(
                    """
                    UPDATE skill_revisions SET
                        security_scanned_at = ?,
                        scanner_version = ?,
                        risk_level = ?,
                        risk_score = ?,
                        security_findings = ?,
                        status = CASE WHEN ? THEN 'blocked' ELSE status END,
                        updated_at = ?
                    WHERE revision_id = ?
                    """,
                    (
                        scan_result.get("scanned_at"),
                        scan_result.get("scanner_version"),
                        scan_result.get("risk_level"),
                        scan_result.get("risk_score"),
                        json.dumps(scan_result.get("findings", [])),
                        1 if scan_result.get("blocked") else 0,
                        datetime.now().isoformat(),
                        current_revision,
                    ),
                )

            # Update status if blocked
            if scan_result.get("blocked"):
                cursor.execute(
                    "UPDATE skills SET status = 'blocked' WHERE skill_id = ?",
                    (skill_id,),
                )

            self._log_event(
                conn,
                "scan",
                skill_id=skill_id,
                revision_id=current_revision,
                details={
                    "scan_id": scan_id,
                    "revision_id": current_revision,
                    "risk_level": scan_result.get("risk_level"),
                    "risk_score": scan_result.get("risk_score"),
                    "findings_count": scan_result.get("findings_count"),
                    "blocked": bool(scan_result.get("blocked")),
                },
            )

        return scan_id

    def get_scan_history(self, skill_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get security scan history for a skill"""
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM security_scans 
                WHERE skill_id = ?
                ORDER BY scanned_at DESC
                LIMIT ?
            """,
                (skill_id, limit),
            )

            return [dict(row) for row in cursor.fetchall()]

    # ============ Equivalence Tests ============

    def record_equivalence_test(
        self,
        skill_id: str,
        test_result: Dict[str, Any],
        revision_id: Optional[str] = None,
    ) -> str:
        """Record an equivalence test result"""
        test_id = self.generate_id()

        scores = test_result.get("scores", {})

        with self.connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            cursor = conn.cursor()
            target = self._resolve_current_target(
                conn,
                skill_id=skill_id,
                revision_id=revision_id,
            )
            current_revision = target["current_revision_id"]

            cursor.execute(
                """
                INSERT INTO equivalence_tests (
                    test_id, skill_id, revision_id, tested_at, tester_version,
                    original_path, converted_path,
                    semantic_similarity, structure_similarity,
                    keyword_similarity, metadata_completeness,
                    overall_score, passed,
                    details_json, warnings_json, errors_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    test_id,
                    skill_id,
                    current_revision,
                    test_result.get("tested_at", datetime.now().isoformat()),
                    test_result.get("tester_version", "1.0.0"),
                    test_result.get("original_path", ""),
                    test_result.get("converted_path", ""),
                    scores.get("semantic_similarity", 0),
                    scores.get("structure_similarity", 0),
                    scores.get("keyword_similarity", 0),
                    scores.get("metadata_completeness", 0),
                    scores.get("overall", 0),
                    1 if test_result.get("passed") else 0,
                    json.dumps(test_result.get("details", {})),
                    json.dumps(test_result.get("warnings", [])),
                    json.dumps(test_result.get("errors", [])),
                ),
            )

            # Update skill with latest test
            cursor.execute(
                """
                UPDATE skills SET
                    equivalence_tested_at = ?,
                    equivalence_score = ?,
                    semantic_similarity = ?,
                    structure_similarity = ?,
                    keyword_similarity = ?,
                    equivalence_passed = ?,
                    updated_at = ?
                WHERE skill_id = ?
            """,
                (
                    test_result.get("tested_at"),
                    scores.get("overall", 0),
                    scores.get("semantic_similarity", 0),
                    scores.get("structure_similarity", 0),
                    scores.get("keyword_similarity", 0),
                    1 if test_result.get("passed") else 0,
                    datetime.now().isoformat(),
                    skill_id,
                ),
            )

            if current_revision:
                cursor.execute(
                    """
                    UPDATE skill_revisions SET
                        equivalence_tested_at = ?,
                        equivalence_score = ?,
                        semantic_similarity = ?,
                        structure_similarity = ?,
                        keyword_similarity = ?,
                        equivalence_passed = ?,
                        updated_at = ?
                    WHERE revision_id = ?
                    """,
                    (
                        test_result.get("tested_at"),
                        scores.get("overall", 0),
                        scores.get("semantic_similarity", 0),
                        scores.get("structure_similarity", 0),
                        scores.get("keyword_similarity", 0),
                        1 if test_result.get("passed") else 0,
                        datetime.now().isoformat(),
                        current_revision,
                    ),
                )

            self._log_event(
                conn,
                "test",
                skill_id=skill_id,
                revision_id=current_revision,
                details={
                    "test_id": test_id,
                    "revision_id": current_revision,
                    "overall_score": scores.get("overall"),
                    "passed": test_result.get("passed"),
                },
            )

        return test_id

    def get_test_history(self, skill_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get equivalence test history for a skill"""
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM equivalence_tests
                WHERE skill_id = ?
                ORDER BY tested_at DESC
                LIMIT ?
            """,
                (skill_id, limit),
            )

            return [dict(row) for row in cursor.fetchall()]

    # ============ Durable Action Jobs ============

    def create_action_job(self, job: Dict[str, Any], items: List[Dict[str, Any]]) -> None:
        """Persist an async governance action job and its items."""
        now = datetime.now().isoformat()

        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO action_jobs (
                    job_id, job_type, status, requested_by, selection_mode,
                    max_attempts, queued_at, started_at, completed_at,
                    cancelled_at, cancelled_by, error_code, error_message, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job["job_id"],
                    job["job_type"],
                    job["status"],
                    job["requested_by"],
                    job["selection_mode"],
                    job["max_attempts"],
                    job["queued_at"],
                    job.get("started_at"),
                    job.get("completed_at"),
                    job.get("cancelled_at"),
                    job.get("cancelled_by"),
                    job.get("error_code"),
                    job.get("error_message"),
                    job.get("created_at", now),
                    job.get("updated_at", now),
                ),
            )

            for item in items:
                cursor.execute(
                    """
                    INSERT INTO action_job_items (
                        item_id, job_id, skill_id, target_revision_id, action_type,
                        status, attempt_number, max_attempts, started_at, completed_at,
                        result_json, error_code, error_message, claimed_by, lease_expires_at,
                        retry_of_item_id, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item["item_id"],
                        item["job_id"],
                        item["skill_id"],
                        item.get("target_revision_id"),
                        item["action_type"],
                        item["status"],
                        item["attempt_number"],
                        item["max_attempts"],
                        item.get("started_at"),
                        item.get("completed_at"),
                        json.dumps(item.get("result")) if item.get("result") is not None else None,
                        item.get("error_code"),
                        item.get("error_message"),
                        item.get("claimed_by"),
                        item.get("lease_expires_at"),
                        item.get("retry_of_item_id"),
                        item.get("created_at", now),
                        item.get("updated_at", now),
                    ),
                )

    def get_action_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a persisted action job by ID."""
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM action_jobs WHERE job_id = ?", (job_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def list_action_jobs(
        self,
        *,
        statuses: Optional[List[str]] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """List persisted action jobs, optionally filtered by status."""
        with self.connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM action_jobs"
            params: List[Any] = []

            if statuses:
                placeholders = ", ".join("?" for _ in statuses)
                query += f" WHERE status IN ({placeholders})"
                params.extend(statuses)

            query += " ORDER BY queued_at DESC LIMIT ?"
            params.append(limit)
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_action_job_items(self, job_id: str) -> List[Dict[str, Any]]:
        """Fetch persisted action job items for a job."""
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM action_job_items
                WHERE job_id = ?
                ORDER BY created_at ASC, item_id ASC
                """,
                (job_id,),
            )
            items = []
            for row in cursor.fetchall():
                item = dict(row)
                item["result"] = self._decode_json_field(item.pop("result_json", None), None)
                items.append(item)
            return items

    def update_action_job(self, job_id: str, **updates) -> bool:
        """Update mutable state for a persisted action job."""
        allowed = {
            "status",
            "started_at",
            "completed_at",
            "cancelled_at",
            "cancelled_by",
            "error_code",
            "error_message",
        }
        invalid = sorted(set(updates) - allowed)
        if invalid:
            raise ValueError("Unsupported action job fields: " + ", ".join(invalid))
        if not updates:
            return False

        with self.connection() as conn:
            cursor = conn.cursor()
            updates["updated_at"] = datetime.now().isoformat()
            set_clause = ", ".join(f"{field} = ?" for field in updates)
            values = list(updates.values()) + [job_id]
            cursor.execute(f"UPDATE action_jobs SET {set_clause} WHERE job_id = ?", values)
            return cursor.rowcount > 0

    def update_action_job_item(self, item_id: str, **updates) -> bool:
        """Update mutable state for a persisted action job item."""
        allowed = {
            "status",
            "started_at",
            "completed_at",
            "result",
            "error_code",
            "error_message",
            "claimed_by",
            "lease_expires_at",
        }
        invalid = sorted(set(updates) - allowed)
        if invalid:
            raise ValueError("Unsupported action job item fields: " + ", ".join(invalid))
        if not updates:
            return False

        db_updates = dict(updates)
        if "result" in db_updates:
            result = db_updates.pop("result")
            db_updates["result_json"] = json.dumps(result) if result is not None else None

        with self.connection() as conn:
            cursor = conn.cursor()
            db_updates["updated_at"] = datetime.now().isoformat()
            set_clause = ", ".join(f"{field} = ?" for field in db_updates)
            values = list(db_updates.values()) + [item_id]
            cursor.execute(f"UPDATE action_job_items SET {set_clause} WHERE item_id = ?", values)
            return cursor.rowcount > 0

    def claim_next_action_job_item(self, job_id: str, worker_id: str, lease_seconds: int) -> Optional[Dict[str, Any]]:
        """Atomically claim the next queued/retrying item for a worker."""
        while True:
            with self.connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT i.item_id
                    FROM action_job_items AS i
                    JOIN action_jobs AS j ON j.job_id = i.job_id
                    WHERE i.job_id = ?
                      AND i.status IN ('queued', 'retrying')
                      AND j.status IN ('queued', 'running')
                    ORDER BY i.created_at ASC, i.item_id ASC
                    LIMIT 1
                    """,
                    (job_id,),
                )
                row = cursor.fetchone()
                if not row:
                    return None

                now_utc = datetime.utcnow()
                started_at = now_utc.isoformat() + "Z"
                lease_expires_at_iso = (now_utc + timedelta(seconds=max(lease_seconds, 1))).isoformat() + "Z"
                updated_at = datetime.now().isoformat()
                cursor.execute(
                    """
                    UPDATE action_job_items
                    SET status = 'running',
                        started_at = ?,
                        completed_at = NULL,
                        result_json = NULL,
                        error_code = NULL,
                        error_message = NULL,
                        claimed_by = ?,
                        lease_expires_at = ?,
                        updated_at = ?
                    WHERE item_id = ? AND status IN ('queued', 'retrying')
                    """,
                    (started_at, worker_id, lease_expires_at_iso, updated_at, row["item_id"]),
                )
                if cursor.rowcount != 1:
                    continue

                cursor.execute("SELECT * FROM action_job_items WHERE item_id = ?", (row["item_id"],))
                claimed = cursor.fetchone()
                if not claimed:
                    return None
                item = dict(claimed)
                item["result"] = self._decode_json_field(item.pop("result_json", None), None)
                return item

    def cancel_pending_action_job_items(self, job_id: str, *, cancelled_at: str, error_message: str) -> int:
        """Mark all queued/retrying items in a job as cancelled."""
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE action_job_items
                SET status = 'cancelled',
                    completed_at = ?,
                    error_code = 'JOB_CANCELLED',
                    error_message = ?,
                    claimed_by = NULL,
                    lease_expires_at = NULL,
                    updated_at = ?
                WHERE job_id = ? AND status IN ('queued', 'retrying')
                """,
                (
                    cancelled_at,
                    error_message,
                    datetime.now().isoformat(),
                    job_id,
                ),
            )
            return cursor.rowcount

    def refresh_action_job_item_lease(self, item_id: str, worker_id: str, lease_seconds: int) -> bool:
        """Extend the lease for a running item held by the same worker."""
        lease_expires_at_iso = (datetime.utcnow() + timedelta(seconds=max(lease_seconds, 1))).isoformat() + "Z"
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE action_job_items
                SET lease_expires_at = ?,
                    updated_at = ?
                WHERE item_id = ? AND status = 'running' AND claimed_by = ?
                """,
                (
                    lease_expires_at_iso,
                    datetime.now().isoformat(),
                    item_id,
                    worker_id,
                ),
            )
            return cursor.rowcount == 1

    # ============ Approval Workflow ============

    def approve_skill(
        self,
        skill_id: str,
        approved_by: str,
        reason: str = "",
        revision_id: Optional[str] = None,
        decision_evidence: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Approve a skill for use"""
        with self.connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            cursor = conn.cursor()
            try:
                row = self._resolve_current_target(
                    conn,
                    skill_id=skill_id,
                    revision_id=revision_id,
                )
            except GovernanceTargetError:
                return False

            if row["status"] in {"blocked", "rejected"}:
                return False  # Rejected revisions must be superseded before reapproval.

            current_revision = row["current_revision_id"]
            if not row["canonical_skill_id"] or not row["artifact_digest"]:
                return False

            fresh_reapproval = None
            prior_authority_failure = self._has_prior_authority_failure(
                conn,
                skill_id=skill_id,
                current_revision_id=current_revision,
            )
            blocked_remediation_cutoff = self._blocked_remediation_cutoff(
                conn,
                skill_id=skill_id,
                revision_id=current_revision,
            )
            if row["status"] == "pending" and (
                prior_authority_failure or blocked_remediation_cutoff is not None
            ):
                actor = (approved_by or "").strip()
                review_reason = (reason or "").strip()
                if not actor or not review_reason:
                    return False
                fresh_reapproval = self._fresh_reapproval_evidence(
                    conn,
                    skill_id=skill_id,
                    revision_id=current_revision,
                    canonical_skill_id=row["canonical_skill_id"],
                    artifact_digest=row["artifact_digest"],
                    not_before=blocked_remediation_cutoff,
                )
                if fresh_reapproval is None:
                    return False
                review_event_id = self._log_event(
                    conn,
                    "review",
                    skill_id=skill_id,
                    revision_id=current_revision,
                    skill_name=row["name"],
                    actor=actor,
                    details={
                        **fresh_reapproval,
                        "reason": review_reason,
                    },
                    previous_state={"status": row["status"]},
                    new_state={"status": row["status"]},
                )
                fresh_reapproval["review_event_id"] = review_event_id

            cursor.execute(
                """
                UPDATE skills SET
                    status = 'approved',
                    approved_by = ?,
                    approved_at = ?,
                    updated_at = ?
                WHERE skill_id = ?
            """,
                (
                    approved_by,
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                    skill_id,
                ),
            )

            if current_revision:
                cursor.execute(
                    """
                    UPDATE skill_revisions SET
                        status = 'approved',
                        approved_by = ?,
                        approved_at = ?,
                        updated_at = ?
                    WHERE revision_id = ?
                    """,
                    (
                        approved_by,
                        datetime.now().isoformat(),
                        datetime.now().isoformat(),
                        current_revision,
                    ),
                )

            self._log_event(
                conn,
                "approve",
                skill_id=skill_id,
                revision_id=current_revision,
                skill_name=row["name"],
                actor=approved_by,
                details={
                    "reason": reason,
                    "revision_id": current_revision,
                    "decision_evidence": decision_evidence,
                    "fresh_reapproval": fresh_reapproval,
                },
                previous_state={"status": row["status"]},
                new_state={"status": "approved"},
            )

            return True

    def reject_skill(
        self,
        skill_id: str,
        rejected_by: str,
        reason: str,
        revision_id: Optional[str] = None,
        decision_evidence: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Reject a skill"""
        with self.connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            cursor = conn.cursor()
            try:
                row = self._resolve_current_target(
                    conn,
                    skill_id=skill_id,
                    revision_id=revision_id,
                )
            except GovernanceTargetError:
                return False

            current_revision = row["current_revision_id"]

            cursor.execute(
                """
                UPDATE skills SET
                    status = 'rejected',
                    updated_at = ?
                WHERE skill_id = ?
                """,
                (datetime.now().isoformat(), skill_id),
            )

            if current_revision:
                cursor.execute(
                    """
                    UPDATE skill_revisions SET
                        status = 'rejected',
                        updated_at = ?
                    WHERE revision_id = ?
                    """,
                    (datetime.now().isoformat(), current_revision),
                )

            self._log_event(
                conn,
                "reject",
                skill_id=skill_id,
                revision_id=current_revision,
                skill_name=row["name"],
                actor=rejected_by,
                details={
                    "reason": reason,
                    "revision_id": current_revision,
                    "decision_evidence": decision_evidence,
                },
                previous_state={"status": row["status"]},
                new_state={"status": "rejected"},
            )

            return True

    # ============ Audit Log ============

    def _log_event(
        self,
        conn: sqlite3.Connection,
        event_type: str,
        skill_id: str = None,
        revision_id: str = None,
        skill_name: str = None,
        actor: str = "system",
        details: Dict = None,
        previous_state: Dict = None,
        new_state: Dict = None,
    ) -> str:
        """Internal: Log an audit event"""
        cursor = conn.cursor()
        event_id = self.generate_id()
        cursor.execute(
            """
            INSERT INTO audit_log (
                event_id, timestamp, event_type, skill_id, revision_id, skill_name,
                actor, details_json, previous_state_json, new_state_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                event_id,
                datetime.now().isoformat(),
                event_type,
                skill_id,
                revision_id,
                skill_name,
                actor,
                json.dumps(details) if details else None,
                json.dumps(previous_state) if previous_state else None,
                json.dumps(new_state) if new_state else None,
            ),
        )
        return event_id

    def get_audit_log(
        self,
        skill_id: str = None,
        event_type: str = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get audit log entries"""
        with self.connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM audit_log WHERE 1=1"
            params = []

            if skill_id:
                query += " AND skill_id = ?"
                params.append(skill_id)

            if event_type:
                query += " AND event_type = ?"
                params.append(event_type)

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)

            results = []
            for row in cursor.fetchall():
                entry = dict(row)
                # Parse JSON fields
                for field in ["details_json", "previous_state_json", "new_state_json"]:
                    if entry.get(field):
                        try:
                            entry[field.replace("_json", "")] = json.loads(entry[field])
                        except:
                            pass
                        del entry[field]
                results.append(entry)

            return results

    # ============ Statistics ============

    def get_statistics(self) -> Dict[str, Any]:
        """Get overall statistics"""
        with self.connection() as conn:
            cursor = conn.cursor()

            stats = {}

            # Skills by status
            cursor.execute("""
                SELECT status, COUNT(*) as count 
                FROM skills 
                GROUP BY status
            """)
            stats["by_status"] = {
                row["status"]: row["count"] for row in cursor.fetchall()
            }

            # Skills by risk level
            cursor.execute("""
                SELECT risk_level, COUNT(*) as count 
                FROM skills 
                WHERE risk_level IS NOT NULL
                GROUP BY risk_level
            """)
            stats["by_risk"] = {
                row["risk_level"]: row["count"] for row in cursor.fetchall()
            }

            # Total counts
            cursor.execute("SELECT COUNT(*) FROM skills")
            stats["total_skills"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM security_scans")
            stats["total_scans"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM equivalence_tests")
            stats["total_tests"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM audit_log")
            stats["total_events"] = cursor.fetchone()[0]

            return stats


# CLI for database operations
def main():
    import argparse

    parser = argparse.ArgumentParser(description="Governance Database CLI")
    parser.add_argument("--db", type=Path, help="Database path")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # init command
    subparsers.add_parser("init", help="Initialize database")

    # stats command
    subparsers.add_parser("stats", help="Show statistics")

    # list command
    list_parser = subparsers.add_parser("list", help="List skills")
    list_parser.add_argument("--status", help="Filter by status")
    list_parser.add_argument("--risk", help="Filter by risk level")
    list_parser.add_argument("--json", action="store_true")

    # audit command
    audit_parser = subparsers.add_parser("audit", help="Show audit log")
    audit_parser.add_argument("--skill", help="Filter by skill ID")
    audit_parser.add_argument("--type", help="Filter by event type")
    audit_parser.add_argument("--limit", type=int, default=20)

    args = parser.parse_args()

    db = GovernanceDB(db_path=args.db)

    if args.command == "init":
        print(f"✅ Database initialized at {db.db_path}")

    elif args.command == "stats":
        stats = db.get_statistics()
        print("\n📊 Governance Database Statistics")
        print(f"   Total Skills: {stats['total_skills']}")
        print(f"   Total Scans:  {stats['total_scans']}")
        print(f"   Total Tests:  {stats['total_tests']}")
        print(f"   Audit Events: {stats['total_events']}")

        if stats.get("by_status"):
            print("\n   By Status:")
            for status, count in stats["by_status"].items():
                print(f"     {status}: {count}")

        if stats.get("by_risk"):
            print("\n   By Risk Level:")
            for risk, count in stats["by_risk"].items():
                print(f"     {risk}: {count}")

    elif args.command == "list":
        skills = db.list_skills(status=args.status, risk_level=args.risk)

        if args.json:
            print(
                json.dumps(
                    [
                        {
                            "id": s.skill_id,
                            "name": s.name,
                            "status": s.status,
                            "risk_level": s.risk_level,
                            "risk_score": s.risk_score,
                        }
                        for s in skills
                    ],
                    indent=2,
                )
            )
        else:
            print(f"\n📋 Skills ({len(skills)}):")
            for s in skills:
                status_icon = {
                    "pending": "⏳",
                    "approved": "✅",
                    "rejected": "❌",
                    "blocked": "🚫",
                }.get(s.status, "?")
                print(f"  {status_icon} {s.name} [{s.risk_level}:{s.risk_score}]")

    elif args.command == "audit":
        events = db.get_audit_log(
            skill_id=args.skill,
            event_type=args.type,
            limit=args.limit,
        )

        print(f"\n📜 Audit Log ({len(events)} events):")
        for e in events:
            print(
                f"  [{e['timestamp'][:19]}] {e['event_type'].upper()}: {e.get('skill_name', e.get('skill_id', 'N/A'))}"
            )
            if e.get("details"):
                print(f"    {e['details']}")


if __name__ == "__main__":
    main()
