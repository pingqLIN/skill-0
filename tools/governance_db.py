<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
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
import sqlite3
import uuid
from pathlib import Path
from datetime import datetime
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

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "SkillRecord":
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
        )


class GovernanceDB:
    """SQLite database for skill governance"""

    SCHEMA_VERSION = "1.0.0"

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

            # Security scans table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS security_scans (
                    scan_id TEXT PRIMARY KEY,
                    skill_id TEXT NOT NULL,
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

            # Equivalence tests table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS equivalence_tests (
                    test_id TEXT PRIMARY KEY,
                    skill_id TEXT NOT NULL,
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

            # Audit log table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    event_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    skill_id TEXT,
                    skill_name TEXT,
                    actor TEXT DEFAULT 'system',
                    details_json TEXT,
                    previous_state_json TEXT,
                    new_state_json TEXT
                )
            """)

            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_skills_name ON skills(name)")
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_skills_status ON skills(status)"
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
                "CREATE INDEX IF NOT EXISTS idx_audit_skill ON audit_log(skill_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_audit_type ON audit_log(event_type)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_log(timestamp)"
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

            # Log the creation
            self._log_event(
                conn,
                "create",
                skill_id=skill_id,
                skill_name=name,
                details={"source_type": source_type, "source_path": source_path},
            )

        return skill_id

    def get_skill(
        self, skill_id: str = None, name: str = None
    ) -> Optional[SkillRecord]:
        """Get a skill by ID or name"""
        with self.connection() as conn:
            cursor = conn.cursor()

            if skill_id:
                cursor.execute("SELECT * FROM skills WHERE skill_id = ?", (skill_id,))
            elif name:
                cursor.execute("SELECT * FROM skills WHERE name = ?", (name,))
            else:
                return None

            row = cursor.fetchone()
            return SkillRecord.from_row(row) if row else None

    def update_skill(self, skill_id: str, **updates) -> bool:
        """Update a skill record"""
        if not updates:
            return False

        updates["updated_at"] = datetime.now().isoformat()

        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [skill_id]

        with self.connection() as conn:
            cursor = conn.cursor()

            # Get previous state for audit
            cursor.execute("SELECT * FROM skills WHERE skill_id = ?", (skill_id,))
            prev_row = cursor.fetchone()

            cursor.execute(f"UPDATE skills SET {set_clause} WHERE skill_id = ?", values)

            if cursor.rowcount > 0:
                self._log_event(
                    conn,
                    "update",
                    skill_id=skill_id,
                    skill_name=prev_row["name"] if prev_row else None,
                    details=updates,
                    previous_state=dict(prev_row) if prev_row else None,
                )
                return True

        return False

    def list_skills(
        self,
        status: str = None,
        risk_level: str = None,
        limit: int = 100,
    ) -> List[SkillRecord]:
        """List skills with optional filtering"""
        with self.connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM skills WHERE 1=1"
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

    # ============ Security Scans ============

    def record_security_scan(
        self,
        skill_id: str,
        scan_result: Dict[str, Any],
    ) -> str:
        """Record a security scan result"""
        scan_id = self.generate_id()

        with self.connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO security_scans (
                    scan_id, skill_id, scanned_at, scanner_version,
                    risk_level, risk_score, files_scanned, findings_count,
                    findings_json, blocked, blocked_reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    scan_id,
                    skill_id,
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
                details={
                    "risk_level": scan_result.get("risk_level"),
                    "risk_score": scan_result.get("risk_score"),
                    "findings_count": scan_result.get("findings_count"),
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
    ) -> str:
        """Record an equivalence test result"""
        test_id = self.generate_id()

        scores = test_result.get("scores", {})

        with self.connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO equivalence_tests (
                    test_id, skill_id, tested_at, tester_version,
                    original_path, converted_path,
                    semantic_similarity, structure_similarity,
                    keyword_similarity, metadata_completeness,
                    overall_score, passed,
                    details_json, warnings_json, errors_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    test_id,
                    skill_id,
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

            self._log_event(
                conn,
                "test",
                skill_id=skill_id,
                details={
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

    # ============ Approval Workflow ============

    def approve_skill(self, skill_id: str, approved_by: str, reason: str = "") -> bool:
        """Approve a skill for use"""
        with self.connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                "SELECT status, name FROM skills WHERE skill_id = ?", (skill_id,)
            )
            row = cursor.fetchone()

            if not row:
                return False

            if row["status"] == "blocked":
                return False  # Cannot approve blocked skills

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

            self._log_event(
                conn,
                "approve",
                skill_id=skill_id,
                skill_name=row["name"],
                actor=approved_by,
                details={"reason": reason},
                previous_state={"status": row["status"]},
                new_state={"status": "approved"},
            )

            return True

    def reject_skill(self, skill_id: str, rejected_by: str, reason: str) -> bool:
        """Reject a skill"""
        with self.connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                "SELECT status, name FROM skills WHERE skill_id = ?", (skill_id,)
            )
            row = cursor.fetchone()

            if not row:
                return False

            cursor.execute(
                """
                UPDATE skills SET
                    status = 'rejected',
                    updated_at = ?
                WHERE skill_id = ?
            """,
                (datetime.now().isoformat(), skill_id),
            )

            self._log_event(
                conn,
                "reject",
                skill_id=skill_id,
                skill_name=row["name"],
                actor=rejected_by,
                details={"reason": reason},
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
        skill_name: str = None,
        actor: str = "system",
        details: Dict = None,
        previous_state: Dict = None,
        new_state: Dict = None,
    ):
        """Internal: Log an audit event"""
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO audit_log (
                event_id, timestamp, event_type, skill_id, skill_name,
                actor, details_json, previous_state_json, new_state_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                self.generate_id(),
                datetime.now().isoformat(),
                event_type,
                skill_id,
                skill_name,
                actor,
                json.dumps(details) if details else None,
                json.dumps(previous_state) if previous_state else None,
                json.dumps(new_state) if new_state else None,
            ),
        )

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
=======
=======
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
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
import sqlite3
import uuid
from pathlib import Path
from datetime import datetime
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
    source_path: str
    author_name: str
    author_email: Optional[str]
    license_spdx: str
    risk_level: str
    risk_score: int
    equivalence_score: Optional[float]
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "SkillRecord":
        return cls(
            skill_id=row["skill_id"],
            name=row["name"],
            version=row["version"],
            status=row["status"],
            source_type=row["source_type"],
            source_url=row["source_url"] or "",
            source_path=row["source_path"] or "",
            author_name=row["author_name"] or "Unknown",
            author_email=row["author_email"],
            license_spdx=row["license_spdx"] or "UNKNOWN",
            risk_level=row["risk_level"] or "unknown",
            risk_score=row["risk_score"] or 0,
            equivalence_score=row["equivalence_score"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


class GovernanceDB:
    """SQLite database for skill governance"""

    SCHEMA_VERSION = "1.0.0"

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

            # Security scans table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS security_scans (
                    scan_id TEXT PRIMARY KEY,
                    skill_id TEXT NOT NULL,
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

            # Equivalence tests table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS equivalence_tests (
                    test_id TEXT PRIMARY KEY,
                    skill_id TEXT NOT NULL,
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

            # Audit log table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    event_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    skill_id TEXT,
                    skill_name TEXT,
                    actor TEXT DEFAULT 'system',
                    details_json TEXT,
                    previous_state_json TEXT,
                    new_state_json TEXT
                )
            """)

            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_skills_name ON skills(name)")
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_skills_status ON skills(status)"
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
                "CREATE INDEX IF NOT EXISTS idx_audit_skill ON audit_log(skill_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_audit_type ON audit_log(event_type)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_log(timestamp)"
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

            # Log the creation
            self._log_event(
                conn,
                "create",
                skill_id=skill_id,
                skill_name=name,
                details={"source_type": source_type, "source_path": source_path},
            )

        return skill_id

    def get_skill(
        self, skill_id: str = None, name: str = None
    ) -> Optional[SkillRecord]:
        """Get a skill by ID or name"""
        with self.connection() as conn:
            cursor = conn.cursor()

            if skill_id:
                cursor.execute("SELECT * FROM skills WHERE skill_id = ?", (skill_id,))
            elif name:
                cursor.execute("SELECT * FROM skills WHERE name = ?", (name,))
            else:
                return None

            row = cursor.fetchone()
            return SkillRecord.from_row(row) if row else None

    def update_skill(self, skill_id: str, **updates) -> bool:
        """Update a skill record"""
        if not updates:
            return False

        updates["updated_at"] = datetime.now().isoformat()

        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [skill_id]

        with self.connection() as conn:
            cursor = conn.cursor()

            # Get previous state for audit
            cursor.execute("SELECT * FROM skills WHERE skill_id = ?", (skill_id,))
            prev_row = cursor.fetchone()

            cursor.execute(f"UPDATE skills SET {set_clause} WHERE skill_id = ?", values)

            if cursor.rowcount > 0:
                self._log_event(
                    conn,
                    "update",
                    skill_id=skill_id,
                    skill_name=prev_row["name"] if prev_row else None,
                    details=updates,
                    previous_state=dict(prev_row) if prev_row else None,
                )
                return True

        return False

    def list_skills(
        self,
        status: str = None,
        risk_level: str = None,
        limit: int = 100,
    ) -> List[SkillRecord]:
        """List skills with optional filtering"""
        with self.connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM skills WHERE 1=1"
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

    # ============ Security Scans ============

    def record_security_scan(
        self,
        skill_id: str,
        scan_result: Dict[str, Any],
    ) -> str:
        """Record a security scan result"""
        scan_id = self.generate_id()

        with self.connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO security_scans (
                    scan_id, skill_id, scanned_at, scanner_version,
                    risk_level, risk_score, files_scanned, findings_count,
                    findings_json, blocked, blocked_reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    scan_id,
                    skill_id,
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
                details={
                    "risk_level": scan_result.get("risk_level"),
                    "risk_score": scan_result.get("risk_score"),
                    "findings_count": scan_result.get("findings_count"),
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
    ) -> str:
        """Record an equivalence test result"""
        test_id = self.generate_id()

        scores = test_result.get("scores", {})

        with self.connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO equivalence_tests (
                    test_id, skill_id, tested_at, tester_version,
                    original_path, converted_path,
                    semantic_similarity, structure_similarity,
                    keyword_similarity, metadata_completeness,
                    overall_score, passed,
                    details_json, warnings_json, errors_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    test_id,
                    skill_id,
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

            self._log_event(
                conn,
                "test",
                skill_id=skill_id,
                details={
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

    # ============ Approval Workflow ============

    def approve_skill(self, skill_id: str, approved_by: str, reason: str = "") -> bool:
        """Approve a skill for use"""
        with self.connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                "SELECT status, name FROM skills WHERE skill_id = ?", (skill_id,)
            )
            row = cursor.fetchone()

            if not row:
                return False

            if row["status"] == "blocked":
                return False  # Cannot approve blocked skills

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

            self._log_event(
                conn,
                "approve",
                skill_id=skill_id,
                skill_name=row["name"],
                actor=approved_by,
                details={"reason": reason},
                previous_state={"status": row["status"]},
                new_state={"status": "approved"},
            )

            return True

    def reject_skill(self, skill_id: str, rejected_by: str, reason: str) -> bool:
        """Reject a skill"""
        with self.connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                "SELECT status, name FROM skills WHERE skill_id = ?", (skill_id,)
            )
            row = cursor.fetchone()

            if not row:
                return False

            cursor.execute(
                """
                UPDATE skills SET
                    status = 'rejected',
                    updated_at = ?
                WHERE skill_id = ?
            """,
                (datetime.now().isoformat(), skill_id),
            )

            self._log_event(
                conn,
                "reject",
                skill_id=skill_id,
                skill_name=row["name"],
                actor=rejected_by,
                details={"reason": reason},
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
        skill_name: str = None,
        actor: str = "system",
        details: Dict = None,
        previous_state: Dict = None,
        new_state: Dict = None,
    ):
        """Internal: Log an audit event"""
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO audit_log (
                event_id, timestamp, event_type, skill_id, skill_name,
                actor, details_json, previous_state_json, new_state_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                self.generate_id(),
                datetime.now().isoformat(),
                event_type,
                skill_id,
                skill_name,
                actor,
                json.dumps(details) if details else None,
                json.dumps(previous_state) if previous_state else None,
                json.dumps(new_state) if new_state else None,
            ),
        )

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
<<<<<<< Updated upstream
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
