"""
GovernanceService - Service layer wrapping the GovernanceDB

This service provides a clean interface for the API routers to interact
with the underlying governance database.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

TOOLS_DIR = Path(os.getenv(
    "SKILL0_TOOLS_PATH",
    str(Path(__file__).parent.parent.parent.parent.parent / "tools"),
))
sys.path.insert(0, str(TOOLS_DIR))

from governance_db import GovernanceDB, SkillRecord


class GovernanceService:
    """Service layer for governance operations"""

    def __init__(self):
        db_path = Path(os.getenv(
            "SKILL0_GOVERNANCE_DB_PATH",
            str(TOOLS_DIR.parent / "governance" / "db" / "governance.db"),
        ))
        self.db = GovernanceDB(db_path=db_path)

    # ============ Statistics ============

    def get_stats_overview(self) -> Dict[str, Any]:
        """Get overview statistics for the dashboard"""
        stats = self.db.get_statistics()
        by_status = stats.get("by_status", {})
        by_risk = stats.get("by_risk", {})

        # Calculate avg equivalence from all skills
        skills = self.db.list_skills(limit=1000)
        equiv_scores = [
            s.equivalence_score for s in skills if s.equivalence_score is not None
        ]
        avg_equiv = sum(equiv_scores) / len(equiv_scores) if equiv_scores else 0.0

        return {
            "total_skills": stats.get("total_skills", 0),
            "pending_count": by_status.get("pending", 0),
            "approved_count": by_status.get("approved", 0),
            "rejected_count": by_status.get("rejected", 0),
            "blocked_count": by_status.get("blocked", 0),
            "high_risk_count": by_risk.get("high", 0) + by_risk.get("critical", 0),
            "avg_equivalence_score": round(avg_equiv, 2),
        }

    def get_risk_distribution(self) -> Dict[str, int]:
        """Get distribution of skills by risk level"""
        stats = self.db.get_statistics()
        by_risk = stats.get("by_risk", {})
        return {
            "safe": by_risk.get("safe", 0),
            "low": by_risk.get("low", 0),
            "medium": by_risk.get("medium", 0),
            "high": by_risk.get("high", 0),
            "critical": by_risk.get("critical", 0),
            "blocked": by_risk.get("blocked", 0),
        }

    def get_status_distribution(self) -> Dict[str, int]:
        """Get distribution of skills by status"""
        stats = self.db.get_statistics()
        by_status = stats.get("by_status", {})
        return {
            "pending": by_status.get("pending", 0),
            "approved": by_status.get("approved", 0),
            "rejected": by_status.get("rejected", 0),
            "blocked": by_status.get("blocked", 0),
        }

    def get_findings_by_rule(self) -> List[Dict[str, Any]]:
        """Aggregate security findings by rule across all skills"""
        findings_map: Dict[str, Dict[str, Any]] = {}

        skills = self.db.list_skills(limit=1000)
        for skill in skills:
            scan_history = self.db.get_scan_history(skill.skill_id)
            for scan in scan_history:
                findings_json = scan.get("findings_json", "[]")
                try:
                    findings = json.loads(findings_json) if findings_json else []
                except (json.JSONDecodeError, TypeError):
                    findings = []

                for finding in findings:
                    rule_id = finding.get("rule_id", "unknown")
                    if rule_id not in findings_map:
                        findings_map[rule_id] = {
                            "rule_id": rule_id,
                            "rule_name": finding.get("rule_name", rule_id),
                            "severity": finding.get("severity", "unknown"),
                            "count": 0,
                        }
                    findings_map[rule_id]["count"] += 1

        return sorted(findings_map.values(), key=lambda x: x["count"], reverse=True)

    # ============ Skills ============

    def list_skills(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        risk_level: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: str = "updated_at",
        sort_order: str = "desc",
    ) -> Dict[str, Any]:
        """List skills with pagination and filtering"""
        # Get all matching skills from DB
        all_skills = self.db.list_skills(
            status=status, risk_level=risk_level, limit=1000
        )

        # Apply search filter if provided
        if search:
            search_lower = search.lower()
            all_skills = [
                s
                for s in all_skills
                if search_lower in s.name.lower()
                or search_lower in s.author_name.lower()
            ]

        # Sort skills
        reverse = sort_order.lower() == "desc"
        if sort_by == "name":
            all_skills.sort(key=lambda s: s.name.lower(), reverse=reverse)
        elif sort_by == "risk_score":
            all_skills.sort(key=lambda s: s.risk_score, reverse=reverse)
        elif sort_by == "status":
            all_skills.sort(key=lambda s: s.status, reverse=reverse)
        elif sort_by == "updated_at":
            all_skills.sort(key=lambda s: s.updated_at, reverse=reverse)

        # Calculate pagination
        total = len(all_skills)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_skills = all_skills[start_idx:end_idx]

        # Convert to summary format
        items = [self._skill_to_summary(s) for s in page_skills]

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def get_skill(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed skill information"""
        skill = self.db.get_skill(skill_id=skill_id)
        if not skill:
            return None

        # Get related data
        scan_history = self.db.get_scan_history(skill_id)
        test_history = self.db.get_test_history(skill_id)
        audit_events = self.db.get_audit_log(skill_id=skill_id, limit=50)

        # Parse security findings from latest scan
        security_findings = []
        if scan_history:
            latest_scan = scan_history[0]
            findings_json = latest_scan.get("findings_json", "[]")
            try:
                security_findings = json.loads(findings_json) if findings_json else []
            except (json.JSONDecodeError, TypeError):
                security_findings = []

        return {
            "skill_id": skill.skill_id,
            "name": skill.name,
            "version": skill.version,
            "status": skill.status,
            "risk_level": skill.risk_level or "unknown",
            "risk_score": skill.risk_score,
            "equivalence_score": skill.equivalence_score,
            "author_name": skill.author_name,
            "author_email": skill.author_email,
            "author_url": skill.author_url,
            "author_org": skill.author_org,
            "license_spdx": skill.license_spdx,
            "license_url": skill.license_url,
            "requires_attribution": skill.requires_attribution,
            "commercial_allowed": skill.commercial_allowed,
            "modification_allowed": skill.modification_allowed,
            "source_type": skill.source_type or "local",
            "source_path": skill.source_path or "",
            "source_url": skill.source_url or "",
            "source_commit": skill.source_commit,
            "original_format": skill.original_format,
            "fetched_at": skill.fetched_at,
            "converted_at": skill.converted_at,
            "converter_version": skill.converter_version,
            "target_format": skill.target_format,
            "security_scanned_at": skill.security_scanned_at,
            "scanner_version": skill.scanner_version,
            "approved_by": skill.approved_by,
            "approved_at": skill.approved_at,
            "equivalence_tested_at": skill.equivalence_tested_at,
            "equivalence_passed": skill.equivalence_passed,
            "installed_path": skill.installed_path,
            "installed_at": skill.installed_at,
            "created_at": skill.created_at,
            "updated_at": skill.updated_at,
            "security_findings": [
                {
                    "rule_id": f.get("rule_id", "unknown"),
                    "rule_name": f.get("rule_name", "Unknown Rule"),
                    "severity": f.get(
                        "adjusted_severity", f.get("severity", "unknown")
                    ),
                    "line_number": f.get("line_number", 0),
                    "line_content": f.get("line_content", ""),
                    "file_path": f.get("file_path", ""),
                    # Context-aware fields
                    "original_severity": f.get("original_severity"),
                    "adjusted_severity": f.get("adjusted_severity"),
                    "severity_changed": f.get("severity_changed", False),
                    "context_type": f.get("context_type"),
                    "in_code_block": f.get("in_code_block", False),
                    "code_block_language": f.get("code_block_language"),
                    "adjustment_reason": f.get("adjustment_reason"),
                    # Detection standard reference
                    "detection_standard": f.get("detection_standard"),
                    "standard_url": f.get("standard_url"),
                }
                for f in security_findings
            ],
            "scan_history": [
                {
                    "scan_id": s.get("scan_id"),
                    "scanned_at": s.get("scanned_at"),
                    "risk_level": s.get("risk_level", "unknown"),
                    "risk_score": s.get("risk_score", 0),
                    "findings_count": s.get("findings_count", 0),
                }
                for s in scan_history
            ],
            "test_history": [
                {
                    "test_id": t.get("test_id"),
                    "tested_at": t.get("tested_at"),
                    "overall_score": t.get("overall_score", 0),
                    "passed": bool(t.get("passed", False)),
                    "semantic_similarity": t.get("semantic_similarity"),
                    "structure_similarity": t.get("structure_similarity"),
                    "keyword_similarity": t.get("keyword_similarity"),
                }
                for t in test_history
            ],
            "audit_events": [
                {
                    "event_id": e.get("event_id"),
                    "timestamp": e.get("timestamp"),
                    "event_type": e.get("event_type"),
                    "skill_id": e.get("skill_id"),
                    "skill_name": e.get("skill_name"),
                    "actor": e.get("actor", "system"),
                    "details": e.get("details"),
                }
                for e in audit_events
            ],
        }

    def _skill_to_summary(self, skill: SkillRecord) -> Dict[str, Any]:
        """Convert a SkillRecord to a summary dict"""
        return {
            "skill_id": skill.skill_id,
            "name": skill.name,
            "status": skill.status,
            "risk_level": skill.risk_level or "unknown",
            "risk_score": skill.risk_score,
            "equivalence_score": skill.equivalence_score,
            "author_name": skill.author_name,
            "license_spdx": skill.license_spdx,
            "source_url": skill.source_url or "",
            "source_type": skill.source_type or "local",
            "version": skill.version or "1.0.0",
            "created_at": skill.created_at,
            "updated_at": skill.updated_at,
        }

    # ============ Reviews ============

    def get_pending_reviews(self) -> List[Dict[str, Any]]:
        """Get all skills pending review"""
        skills = self.db.list_skills(status="pending", limit=100)
        return [self._skill_to_summary(s) for s in skills]

    def approve_skill(self, skill_id: str, reviewer: str, reason: str) -> bool:
        """Approve a skill"""
        return self.db.approve_skill(skill_id, approved_by=reviewer, reason=reason)

    def reject_skill(self, skill_id: str, reviewer: str, reason: str) -> bool:
        """Reject a skill"""
        return self.db.reject_skill(skill_id, rejected_by=reviewer, reason=reason)

    # ============ Scans ============

    def list_scans(self, limit: int = 100) -> List[Dict[str, Any]]:
        """List all recent scans across all skills"""
        results = []
        skills = self.db.list_skills(limit=1000)

        for skill in skills:
            scan_history = self.db.get_scan_history(skill.skill_id, limit=5)
            for scan in scan_history:
                results.append(
                    {
                        "scan_id": scan.get("scan_id"),
                        "skill_id": skill.skill_id,
                        "skill_name": skill.name,
                        "scanned_at": scan.get("scanned_at"),
                        "risk_level": scan.get("risk_level", "unknown"),
                        "risk_score": scan.get("risk_score", 0),
                        "findings_count": scan.get("findings_count", 0),
                        "files_scanned": scan.get("files_scanned", 0),
                        "blocked": bool(scan.get("blocked", False)),
                        "blocked_reason": scan.get("blocked_reason"),
                    }
                )

        # Sort by scan time descending
        results.sort(key=lambda x: x.get("scanned_at", ""), reverse=True)
        return results[:limit]

    def get_skill_scans(self, skill_id: str) -> List[Dict[str, Any]]:
        """Get scan history for a specific skill"""
        scan_history = self.db.get_scan_history(skill_id)
        results = []

        for scan in scan_history:
            findings_json = scan.get("findings_json", "[]")
            try:
                findings = json.loads(findings_json) if findings_json else []
            except (json.JSONDecodeError, TypeError):
                findings = []

            # Process findings with context-aware fields
            processed_findings = []
            findings_in_code_blocks = 0
            severity_adjustments = 0

            for f in findings:
                finding = {
                    "rule_id": f.get("rule_id", "unknown"),
                    "rule_name": f.get("rule_name", "Unknown Rule"),
                    "severity": f.get(
                        "adjusted_severity", f.get("severity", "unknown")
                    ),
                    "line_number": f.get("line_number", 0),
                    "line_content": f.get("line_content", ""),
                    "file_path": f.get("file_path", ""),
                    # Context-aware fields
                    "original_severity": f.get("original_severity"),
                    "adjusted_severity": f.get("adjusted_severity"),
                    "severity_changed": f.get("severity_changed", False),
                    "context_type": f.get("context_type"),
                    "in_code_block": f.get("in_code_block", False),
                    "code_block_language": f.get("code_block_language"),
                    "adjustment_reason": f.get("adjustment_reason"),
                    # Detection standard reference
                    "detection_standard": f.get("detection_standard"),
                    "standard_url": f.get("standard_url"),
                    "matched_pattern": f.get("matched_pattern"),
                }
                processed_findings.append(finding)

                if f.get("in_code_block"):
                    findings_in_code_blocks += 1
                if f.get("severity_changed"):
                    severity_adjustments += 1

            results.append(
                {
                    "scan_id": scan.get("scan_id"),
                    "scanned_at": scan.get("scanned_at"),
                    "risk_level": scan.get("risk_level", "unknown"),
                    "risk_score": scan.get("risk_score", 0),
                    "findings_count": scan.get("findings_count", 0),
                    "files_scanned": scan.get("files_scanned", 0),
                    "blocked": bool(scan.get("blocked", False)),
                    "blocked_reason": scan.get("blocked_reason"),
                    "findings": processed_findings,
                    # Context-aware stats
                    "original_risk_score": scan.get("original_risk_score"),
                    "code_blocks_found": scan.get("code_blocks_found", 0),
                    "findings_in_code_blocks": findings_in_code_blocks,
                    "severity_adjustments": severity_adjustments,
                    "scanner_version": scan.get("scanner_version"),
                }
            )

        return results

    # ============ Audit ============

    def get_audit_log(
        self,
        page: int = 1,
        page_size: int = 50,
        skill_id: Optional[str] = None,
        event_type: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get paginated audit log"""
        # Get all matching events
        all_events = self.db.get_audit_log(
            skill_id=skill_id,
            event_type=event_type,
            limit=1000,
        )

        # Apply date filters if provided
        if from_date:
            all_events = [e for e in all_events if e.get("timestamp", "") >= from_date]
        if to_date:
            all_events = [e for e in all_events if e.get("timestamp", "") <= to_date]

        # Calculate pagination
        total = len(all_events)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_events = all_events[start_idx:end_idx]

        # Format events
        items = [
            {
                "event_id": e.get("event_id"),
                "timestamp": e.get("timestamp"),
                "event_type": e.get("event_type"),
                "skill_id": e.get("skill_id"),
                "skill_name": e.get("skill_name"),
                "actor": e.get("actor", "system"),
                "details": e.get("details"),
            }
            for e in page_events
        ]

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }
