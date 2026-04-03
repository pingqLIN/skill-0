"""
GovernanceService - Service layer wrapping the GovernanceDB

This service provides a clean interface for the API routers to interact
with the underlying governance database.
"""

import os
import sys
import json
import threading
import uuid
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

def _default_tools_dir() -> Path:
    current = Path(__file__).resolve()
    candidates = [
        current.parents[4] / "tools",
        current.parents[2] / "tools",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


TOOLS_DIR = Path(os.getenv("SKILL0_TOOLS_PATH") or _default_tools_dir())
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
        self._action_job_lock = threading.Lock()
        self._active_action_job_threads: set[str] = set()
        self._worker_id = f"worker-{os.getpid()}-{uuid.uuid4().hex[:8]}"
        self._recover_incomplete_action_jobs()

    def _ensure_action_job_state(self) -> None:
        """Backfill runtime-only action job state for tests using object.__new__."""
        if not hasattr(self, "_action_job_lock"):
            self._action_job_lock = threading.Lock()
        if not hasattr(self, "_active_action_job_threads"):
            self._active_action_job_threads = set()
        if not hasattr(self, "_worker_id"):
            self._worker_id = f"worker-{os.getpid()}-{uuid.uuid4().hex[:8]}"

    def _utcnow_iso(self) -> str:
        return datetime.utcnow().isoformat() + "Z"

    def _job_action_type(self, job_type: str) -> str:
        return "scan" if job_type == "scan_batch" else "test"

    def _action_job_item_lease_seconds(self) -> int:
        raw = os.getenv("SKILL0_ACTION_JOB_LEASE_SECONDS", "300")
        try:
            return max(int(raw), 5)
        except ValueError:
            return 300

    def _action_job_item_heartbeat_seconds(self) -> float:
        raw = os.getenv("SKILL0_ACTION_JOB_HEARTBEAT_SECONDS")
        if raw:
            try:
                return max(float(raw), 0.1)
            except ValueError:
                pass
        return max(self._action_job_item_lease_seconds() / 3.0, 1.0)

    def _is_retriable_error(self, error_code: Optional[str]) -> bool:
        non_retriable = {
            "PATH_NOT_FOUND",
            "SOURCE_PATH_MISSING",
            "SOURCE_PATH_NOT_ALLOWED",
            "INSTALLED_PATH_MISSING",
            "INSTALLED_PATH_NOT_ALLOWED",
        }
        return bool(error_code) and error_code not in non_retriable

    def _compute_job_summary(self, items: List[Dict[str, Any]]) -> Dict[str, int]:
        summary = {
            "total": len(items),
            "queued": 0,
            "running": 0,
            "succeeded": 0,
            "failed": 0,
            "retrying": 0,
            "skipped": 0,
        }
        for item in items:
            status = item.get("status")
            if status in summary:
                summary[status] += 1
        return summary

    def _serialize_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        job = self.db.get_action_job(job_id)
        if not job:
            return None
        items = self.db.get_action_job_items(job_id)
        payload = dict(job)
        payload["summary"] = self._compute_job_summary(items)
        payload["queued_items"] = len(items)
        return payload

    def _serialize_job_items(self, job_id: str) -> Optional[List[Dict[str, Any]]]:
        job = self.db.get_action_job(job_id)
        if not job:
            return None
        return self.db.get_action_job_items(job_id)

    def _make_job_id(self, job_type: str) -> str:
        prefix = "scan" if job_type == "scan_batch" else "test"
        suffix = self.db.generate_id().split("-")[0]
        return f"job_{prefix}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{suffix}"

    def _build_job_item(
        self,
        *,
        job_id: str,
        job_type: str,
        skill_id: str,
        target_revision_id: Optional[str],
        max_attempts: int,
        attempt_number: int = 1,
        retry_of_item_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        item_id = f"{job_id}_item_{skill_id.replace('/', '_')}_{attempt_number:02d}"
        now = self._utcnow_iso()
        return {
            "item_id": item_id,
            "job_id": job_id,
            "skill_id": skill_id,
            "target_revision_id": target_revision_id,
            "action_type": self._job_action_type(job_type),
            "status": "queued" if attempt_number == 1 else "retrying",
            "attempt_number": attempt_number,
            "max_attempts": max_attempts,
            "started_at": None,
            "completed_at": None,
            "result": None,
            "error_code": None,
            "error_message": None,
            "claimed_by": None,
            "retry_of_item_id": retry_of_item_id,
            "created_at": now,
            "updated_at": now,
        }

    def _start_action_job_runner(self, job_id: str) -> None:
        self._ensure_action_job_state()
        with self._action_job_lock:
            if job_id in self._active_action_job_threads:
                return
            self._active_action_job_threads.add(job_id)

        thread = threading.Thread(target=self._run_action_job_thread, args=(job_id,), daemon=True)
        thread.start()

    def _run_action_job_thread(self, job_id: str) -> None:
        try:
            self._run_action_job(job_id)
        finally:
            with self._action_job_lock:
                self._active_action_job_threads.discard(job_id)

    def _is_item_lease_expired(self, item: Dict[str, Any], *, now: Optional[datetime] = None) -> bool:
        lease_expires_at = item.get("lease_expires_at")
        if not lease_expires_at:
            return True
        current = now or datetime.utcnow()
        try:
            expiry = datetime.fromisoformat(str(lease_expires_at).replace("Z", ""))
        except ValueError:
            return True
        return expiry <= current

    def _start_item_heartbeat(self, item_id: str) -> tuple[threading.Event, threading.Thread]:
        stop_event = threading.Event()
        interval = self._action_job_item_heartbeat_seconds()
        lease_seconds = self._action_job_item_lease_seconds()

        def heartbeat() -> None:
            while not stop_event.wait(interval):
                refreshed = self.db.refresh_action_job_item_lease(item_id, self._worker_id, lease_seconds)
                if not refreshed:
                    return

        thread = threading.Thread(target=heartbeat, args=(), daemon=True)
        thread.start()
        return stop_event, thread

    def _recover_incomplete_action_jobs(self) -> None:
        self._ensure_action_job_state()
        recoverable_jobs = self.db.list_action_jobs(statuses=["queued", "running"], limit=500)
        for job in recoverable_jobs:
            items = self.db.get_action_job_items(job["job_id"])
            stale_running_items = [
                item for item in items
                if item["status"] == "running" and self._is_item_lease_expired(item)
            ]
            runnable_items = [
                item for item in items
                if item["status"] in {"queued", "retrying"}
            ]
            live_running_items = [
                item for item in items
                if item["status"] == "running" and not self._is_item_lease_expired(item)
            ]
            if not stale_running_items and not runnable_items and not live_running_items:
                self._finalize_action_job(job["job_id"], items)
                continue

            for item in stale_running_items:
                recovered_status = "retrying" if item["attempt_number"] > 1 else "queued"
                self.db.update_action_job_item(
                    item["item_id"],
                    status=recovered_status,
                    started_at=None,
                    completed_at=None,
                    error_code=None,
                    error_message=None,
                    claimed_by=None,
                    lease_expires_at=None,
                )
                runnable_items.append(item)

            if runnable_items:
                self.db.update_action_job(
                    job["job_id"],
                    status="running" if live_running_items else "queued",
                    completed_at=None,
                    error_code=None,
                    error_message=None,
                )
                self._start_action_job_runner(job["job_id"])
                continue

            if live_running_items:
                self.db.update_action_job(
                    job["job_id"],
                    status="running",
                    completed_at=None,
                    error_code=None,
                    error_message=None,
                )

    def _finalize_action_job(self, job_id: str, items: Optional[List[Dict[str, Any]]] = None) -> Optional[Dict[str, Any]]:
        items = items if items is not None else self.db.get_action_job_items(job_id)
        if items is None:
            return None

        summary = self._compute_job_summary(items)
        if summary["queued"] > 0 or summary["running"] > 0 or summary["retrying"] > 0:
            return self._serialize_job(job_id)
        failed_items = [item for item in items if item.get("status") == "failed"]
        if summary["failed"] == 0:
            final_status = "completed"
            error_code = None
            error_message = None
        elif summary["succeeded"] == 0:
            final_status = "failed"
            error_code = failed_items[0].get("error_code") if failed_items else None
            error_message = failed_items[0].get("error_message") if failed_items else None
        else:
            final_status = "completed_with_failures"
            error_code = failed_items[0].get("error_code") if failed_items else None
            error_message = failed_items[0].get("error_message") if failed_items else None

        self.db.update_action_job(
            job_id,
            status=final_status,
            completed_at=self._utcnow_iso(),
            error_code=error_code,
            error_message=error_message,
        )
        return self._serialize_job(job_id)

    def enqueue_action_job(
        self,
        *,
        job_type: str,
        skill_ids: Optional[List[str]],
        requested_by: str,
        selection_mode: str = "explicit",
        max_attempts: int = 2,
    ) -> Dict[str, Any]:
        """Create and start an async governance action job."""
        self._ensure_action_job_state()
        selected_skill_ids = [skill_id for skill_id in (skill_ids or []) if skill_id]

        if selection_mode == "pending" or (selection_mode == "explicit" and not selected_skill_ids):
            selected_skill_ids = [skill.skill_id for skill in self.db.list_skills(status="pending", limit=1000)]
            if selection_mode == "explicit":
                selection_mode = "pending"

        job_id = self._make_job_id(job_type)
        queued_at = self._utcnow_iso()
        items: List[Dict[str, Any]] = []
        for skill_id in selected_skill_ids:
            current_revision = self.db.get_current_revision(skill_id)
            items.append(
                self._build_job_item(
                    job_id=job_id,
                    job_type=job_type,
                    skill_id=skill_id,
                    target_revision_id=current_revision.revision_id if current_revision else None,
                    max_attempts=max_attempts,
                )
            )

        self.db.create_action_job(
            {
                "job_id": job_id,
                "job_type": job_type,
                "status": "queued",
                "requested_by": requested_by,
                "selection_mode": selection_mode,
                "max_attempts": max_attempts,
                "queued_at": queued_at,
                "started_at": None,
                "completed_at": None,
                "error_code": None,
                "error_message": None,
                "created_at": queued_at,
                "updated_at": queued_at,
            },
            items,
        )

        if items:
            self._start_action_job_runner(job_id)
        else:
            self.db.update_action_job(
                job_id,
                status="completed",
                completed_at=self._utcnow_iso(),
            )

        return self._serialize_job(job_id) or {}

    def _run_action_job(self, job_id: str) -> None:
        """Execute a queued async action job in-process."""
        job = self.db.get_action_job(job_id)
        if not job:
            return

        started_at = job.get("started_at") or self._utcnow_iso()
        self.db.update_action_job(
            job_id,
            status="running",
            started_at=started_at,
            completed_at=None,
            error_code=None,
            error_message=None,
        )
        job_type = job["job_type"]

        runner = self.run_scan if job_type == "scan_batch" else self.run_test

        while True:
            item = self.db.claim_next_action_job_item(
                job_id,
                self._worker_id,
                self._action_job_item_lease_seconds(),
            )
            if not item:
                break
            stop_heartbeat, heartbeat_thread = self._start_item_heartbeat(item["item_id"])
            result = runner(item["skill_id"])
            stop_heartbeat.set()
            heartbeat_thread.join(timeout=max(self._action_job_item_heartbeat_seconds(), 1.0))

            self.db.update_action_job_item(
                item["item_id"],
                result=result,
                completed_at=self._utcnow_iso(),
                error_code=result.get("error_code"),
                error_message=result.get("error_message"),
                status="succeeded" if result.get("status") == "success" else "failed",
                claimed_by=None,
                lease_expires_at=None,
            )

        self._finalize_action_job(job_id)

    def get_action_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a serialized async action job."""
        return self._serialize_job(job_id)

    def get_action_job_items(self, job_id: str) -> Optional[List[Dict[str, Any]]]:
        """Fetch serialized items for an async action job."""
        return self._serialize_job_items(job_id)

    def retry_action_job_failures(self, *, job_id: str, requested_by: str) -> Dict[str, Any]:
        """Create a new async job for all retriable failed items from a prior job."""
        job = self.db.get_action_job(job_id)
        items = self.db.get_action_job_items(job_id) if job else []

        if not job:
            raise KeyError(job_id)

        failed_items = [
            item for item in items
            if item.get("status") == "failed" and self._is_retriable_error(item.get("error_code"))
        ]
        if not failed_items:
            raise ValueError("No retriable failed items found for this action job")

        return self._enqueue_retry_job(
            source_job=job,
            source_items=failed_items,
            requested_by=requested_by,
            selection_mode="retry_failures",
        )

    def retry_action_job_item(self, *, job_id: str, item_id: str, requested_by: str) -> Dict[str, Any]:
        """Create a new async job for a specific retriable failed item."""
        job = self.db.get_action_job(job_id)
        items = self.db.get_action_job_items(job_id) if job else []

        if not job:
            raise KeyError(job_id)

        source_item = next((item for item in items if item.get("item_id") == item_id), None)
        if not source_item:
            raise KeyError(item_id)
        if source_item.get("status") != "failed":
            raise ValueError("Only failed items can be retried")
        if not self._is_retriable_error(source_item.get("error_code")):
            raise ValueError("Item is not retriable")

        return self._enqueue_retry_job(
            source_job=job,
            source_items=[source_item],
            requested_by=requested_by,
            selection_mode="retry_item",
        )

    def _enqueue_retry_job(
        self,
        *,
        source_job: Dict[str, Any],
        source_items: List[Dict[str, Any]],
        requested_by: str,
        selection_mode: str,
    ) -> Dict[str, Any]:
        """Create a retry job derived from prior failed items."""
        job_type = source_job["job_type"]
        max_attempts = source_job.get("max_attempts", 2)
        job_id = self._make_job_id(job_type)
        queued_at = self._utcnow_iso()
        items: List[Dict[str, Any]] = []

        for source_item in source_items:
            if source_item.get("attempt_number", 1) >= max_attempts:
                raise ValueError("Retry would exceed max_attempts")
            items.append(
                self._build_job_item(
                    job_id=job_id,
                    job_type=job_type,
                    skill_id=source_item["skill_id"],
                    target_revision_id=source_item.get("target_revision_id"),
                    max_attempts=max_attempts,
                    attempt_number=source_item.get("attempt_number", 1) + 1,
                    retry_of_item_id=source_item["item_id"],
                )
            )

        self.db.create_action_job(
            {
                "job_id": job_id,
                "job_type": job_type,
                "status": "queued",
                "requested_by": requested_by,
                "selection_mode": selection_mode,
                "max_attempts": max_attempts,
                "queued_at": queued_at,
                "started_at": None,
                "completed_at": None,
                "error_code": None,
                "error_message": None,
                "created_at": queued_at,
                "updated_at": queued_at,
            },
            items,
        )

        self._start_action_job_runner(job_id)
        return self._serialize_job(job_id) or {}

    def _allowed_path_roots(self) -> List[Path]:
        raw_roots = os.getenv("SKILL0_ALLOWED_PATH_ROOTS", str(TOOLS_DIR.parent))
        separators_normalized = raw_roots.replace(",", os.pathsep)
        roots: List[Path] = []
        for entry in separators_normalized.split(os.pathsep):
            candidate = entry.strip()
            if not candidate:
                continue
            roots.append(Path(candidate).expanduser().resolve(strict=False))
        return roots or [TOOLS_DIR.parent.resolve(strict=False)]

    def _resolve_managed_path(self, raw_path: str) -> tuple[Optional[Path], Optional[str]]:
        if not raw_path:
            return None, None

        resolved = Path(raw_path).expanduser().resolve(strict=False)
        for root in self._allowed_path_roots():
            try:
                resolved.relative_to(root)
                return resolved, None
            except ValueError:
                continue

        return None, f"path is outside allowed roots: {raw_path}"

    def _path_exists(self, raw_path: str) -> bool:
        if not raw_path:
            return False
        return Path(raw_path).expanduser().resolve(strict=False).exists()

    # ============ Statistics ============

    def get_stats_overview(self) -> Dict[str, Any]:
        """Get overview statistics for the dashboard"""
        stats = self.db.get_statistics()
        by_status = stats.get("by_status", {})
        by_risk = stats.get("by_risk", {})

        # Calculate avg fidelity from all skills
        skills = self.db.list_skills(limit=1000)
        fidelity_scores = [
            s.equivalence_score for s in skills if s.equivalence_score is not None
        ]
        avg_fidelity = sum(fidelity_scores) / len(fidelity_scores) if fidelity_scores else 0.0

        return {
            "total_skills": stats.get("total_skills", 0),
            "pending_count": by_status.get("pending", 0),
            "approved_count": by_status.get("approved", 0),
            "rejected_count": by_status.get("rejected", 0),
            "blocked_count": by_status.get("blocked", 0),
            "high_risk_count": by_risk.get("high", 0) + by_risk.get("critical", 0),
            "avg_fidelity_score": round(avg_fidelity, 2),
            "avg_equivalence_score": round(avg_fidelity, 2),
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
        revisions = self.db.list_revisions(skill_id, limit=20)

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
            "current_revision_id": skill.current_revision_id,
            "revision_id": skill.revision_id,
            "revision_number": skill.revision_number,
            "name": skill.name,
            "version": skill.version,
            "status": skill.status,
            "risk_level": skill.risk_level or "unknown",
            "risk_score": skill.risk_score,
            "fidelity_score": skill.equivalence_score,
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
            "source_checksum": skill.source_checksum,
            "original_format": skill.original_format,
            "fetched_at": skill.fetched_at,
            "converted_at": skill.converted_at,
            "converter_version": skill.converter_version,
            "target_format": skill.target_format,
            "security_scanned_at": skill.security_scanned_at,
            "scanner_version": skill.scanner_version,
            "approved_by": skill.approved_by,
            "approved_at": skill.approved_at,
            "fidelity_tested_at": skill.equivalence_tested_at,
            "equivalence_tested_at": skill.equivalence_tested_at,
            "fidelity_passed": skill.equivalence_passed,
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
                    "revision_id": s.get("revision_id"),
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
                    "revision_id": t.get("revision_id"),
                    "tested_at": t.get("tested_at"),
                    "fidelity_score": t.get("overall_score", 0),
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
                    "revision_id": e.get("revision_id"),
                    "skill_name": e.get("skill_name"),
                    "actor": e.get("actor", "system"),
                    "details": e.get("details"),
                }
                for e in audit_events
            ],
            "revision_history": [
                {
                    "revision_id": r.revision_id,
                    "revision_number": r.revision_number,
                    "status": r.status,
                    "version": r.version,
                    "source_commit": r.source_commit,
                    "source_path": r.source_path or "",
                    "source_checksum": r.source_checksum,
                    "risk_level": r.risk_level or "unknown",
                    "risk_score": r.risk_score,
                    "fidelity_score": r.equivalence_score,
                    "equivalence_score": r.equivalence_score,
                    "approved_by": r.approved_by,
                    "approved_at": r.approved_at,
                    "created_at": r.created_at,
                    "updated_at": r.updated_at,
                    "is_current": r.is_current,
                }
                for r in revisions
            ],
        }

    def get_skill_revisions(self, skill_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get explicit revision history for a skill."""
        skill = self.db.get_skill(skill_id=skill_id)
        if not skill:
            return None

        revisions = self.db.list_revisions(skill_id, limit=50)
        return [
            {
                "revision_id": r.revision_id,
                "revision_number": r.revision_number,
                "status": r.status,
                "version": r.version,
                "source_commit": r.source_commit,
                "source_path": r.source_path or "",
                "source_checksum": r.source_checksum,
                "risk_level": r.risk_level or "unknown",
                "risk_score": r.risk_score,
                "fidelity_score": r.equivalence_score,
                "equivalence_score": r.equivalence_score,
                "approved_by": r.approved_by,
                "approved_at": r.approved_at,
                "created_at": r.created_at,
                "updated_at": r.updated_at,
                "is_current": r.is_current,
            }
            for r in revisions
        ]

    def _skill_to_summary(self, skill: SkillRecord) -> Dict[str, Any]:
        """Convert a SkillRecord to a summary dict"""
        return {
            "skill_id": skill.skill_id,
            "current_revision_id": skill.current_revision_id,
            "revision_id": skill.revision_id,
            "revision_number": skill.revision_number,
            "name": skill.name,
            "status": skill.status,
            "risk_level": skill.risk_level or "unknown",
            "risk_score": skill.risk_score,
            "fidelity_score": skill.equivalence_score,
            "equivalence_score": skill.equivalence_score,
            "author_name": skill.author_name,
            "license_spdx": skill.license_spdx,
            "source_url": skill.source_url or "",
            "source_checksum": skill.source_checksum,
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
                        "revision_id": scan.get("revision_id"),
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
                    "revision_id": scan.get("revision_id"),
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

    # ============ Action Readiness ============

    def get_action_readiness(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """Check whether scan and test actions can be executed for a skill"""
        skill = self.db.get_skill(skill_id=skill_id)
        if not skill:
            return None

        source_path = skill.source_path or ""
        installed_path = skill.installed_path or ""
        source_path_exists = self._path_exists(source_path)
        installed_path_exists = self._path_exists(installed_path)
        resolved_source_path, source_path_issue = self._resolve_managed_path(source_path) if source_path_exists else (None, None)
        resolved_installed_path, installed_path_issue = self._resolve_managed_path(installed_path) if installed_path_exists else (None, None)

        reasons = []
        if source_path_issue:
            reasons.append(f"source_path {source_path_issue}")
        elif not source_path_exists:
            if not source_path:
                reasons.append("source_path is not set")
            else:
                reasons.append(f"source_path does not exist: {source_path}")
        if installed_path_issue:
            reasons.append(f"installed_path {installed_path_issue}")
        elif not installed_path_exists:
            if not installed_path:
                reasons.append("installed_path is not set")
            else:
                reasons.append(f"installed_path does not exist: {installed_path}")

        can_scan = source_path_exists and not source_path_issue
        can_test = source_path_exists and installed_path_exists and not source_path_issue and not installed_path_issue

        return {
            "skill_id": skill_id,
            "revision_id": skill.current_revision_id,
            "can_scan": can_scan,
            "can_test": can_test,
            "source_path_exists": source_path_exists,
            "installed_path_exists": installed_path_exists,
            "reasons": reasons,
        }

    def run_scan(self, skill_id: str) -> Dict[str, Any]:
        """Run a security scan for a single skill"""
        skill = self.db.get_skill(skill_id=skill_id)
        if not skill:
            return {
                "status": "failed",
                "skill_id": skill_id,
                "processed": 0,
                "results": [],
                "error_code": "PATH_NOT_FOUND",
                "error_message": f"Skill not found: {skill_id}",
                "hint": "Check that the skill_id is correct.",
            }

        source_path = skill.source_path or ""
        if not self._path_exists(source_path):
            return {
                "status": "failed",
                "skill_id": skill_id,
                "processed": 0,
                "results": [],
                "error_code": "SOURCE_PATH_MISSING",
                "error_message": f"Source path does not exist: {source_path or '(not set)'}",
                "hint": "Ensure the skill's source_path is set and the file is accessible.",
            }

        resolved_source_path, source_path_issue = self._resolve_managed_path(source_path)
        if source_path_issue:
            return {
                "status": "failed",
                "skill_id": skill_id,
                "processed": 0,
                "results": [],
                "error_code": "SOURCE_PATH_NOT_ALLOWED",
                "error_message": f"Source path is outside allowed roots: {source_path}",
                "hint": "Store managed skills under the configured allowed roots before scanning.",
            }

        try:
            from advanced_skill_analyzer import AdvancedSkillAnalyzer
            from datetime import datetime as _dt

            analyzer = AdvancedSkillAnalyzer()
            scan_result = analyzer.analyze(resolved_source_path)

            scan_data = {
                "scanned_at": _dt.now().isoformat(),
                "scanner_version": getattr(analyzer, "VERSION", "1.0.0"),
                "file_path": str(resolved_source_path),
                "risk_level": scan_result.risk_level,
                "risk_score": scan_result.risk_score,
                "findings": [
                    f.__dict__ if hasattr(f, "__dict__") else f
                    for f in (scan_result.findings or [])
                ],
            }
            self.db.record_security_scan(skill_id, scan_data)
            current_revision = self.db.get_current_revision(skill_id)

            item = {
                "skill_id": skill_id,
                "revision_id": current_revision.revision_id if current_revision else None,
                "status": "success",
                "risk_level": scan_result.risk_level,
                "risk_score": scan_result.risk_score,
                "findings_count": len(scan_result.findings or []),
            }
            return {
                "status": "success",
                "skill_id": skill_id,
                "revision_id": current_revision.revision_id if current_revision else None,
                "processed": 1,
                "results": [item],
            }
        except Exception as exc:
            return {
                "status": "failed",
                "skill_id": skill_id,
                "processed": 0,
                "results": [],
                "error_code": "SCAN_RUNTIME_ERROR",
                "error_message": str(exc),
                "hint": "Check that the source path contains a valid skill file.",
            }

    def run_scan_batch(self, skill_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run scan for multiple skills (pending by default)"""
        if skill_ids is not None and len(skill_ids) == 0:
            return {"status": "noop", "processed": 0, "results": []}

        skills = self.db.list_skills(status="pending", limit=1000)
        targets = [s for s in skills if skill_ids is None or s.skill_id in skill_ids]

        if not targets:
            return {"status": "noop", "processed": 0, "results": []}

        results = []
        for skill in targets:
            result = self.run_scan(skill.skill_id)
            results.append(result)

        success_count = sum(1 for r in results if r.get("status") == "success")
        overall = (
            "success"
            if success_count == len(results)
            else ("failed" if success_count == 0 else "partial")
        )
        return {
            "status": overall,
            "processed": len(results),
            "results": results,
        }

    def run_test(self, skill_id: str) -> Dict[str, Any]:
        """Run fidelity test for a single skill"""
        skill = self.db.get_skill(skill_id=skill_id)
        if not skill:
            return {
                "status": "failed",
                "skill_id": skill_id,
                "processed": 0,
                "results": [],
                "error_code": "PATH_NOT_FOUND",
                "error_message": f"Skill not found: {skill_id}",
                "hint": "Check that the skill_id is correct.",
            }

        source_path = skill.source_path or ""
        installed_path = skill.installed_path or ""
        if not self._path_exists(source_path):
            return {
                "status": "failed",
                "skill_id": skill_id,
                "processed": 0,
                "results": [],
                "error_code": "SOURCE_PATH_MISSING",
                "error_message": f"Source path does not exist: {source_path or '(not set)'}",
                "hint": "Ensure the skill's source_path is set and the file is accessible.",
            }

        if not self._path_exists(installed_path):
            return {
                "status": "failed",
                "skill_id": skill_id,
                "processed": 0,
                "results": [],
                "error_code": "INSTALLED_PATH_MISSING",
                "error_message": f"Installed path does not exist: {installed_path or '(not set)'}",
                "hint": "Ensure the skill has been installed and installed_path is set.",
            }

        resolved_installed_path, installed_path_issue = self._resolve_managed_path(installed_path)
        if installed_path_issue:
            return {
                "status": "failed",
                "skill_id": skill_id,
                "processed": 0,
                "results": [],
                "error_code": "INSTALLED_PATH_NOT_ALLOWED",
                "error_message": f"Installed path is outside allowed roots: {installed_path}",
                "hint": "Store installed skills under the configured allowed roots before testing.",
            }

        resolved_source_path, source_path_issue = self._resolve_managed_path(source_path)
        if source_path_issue:
            return {
                "status": "failed",
                "skill_id": skill_id,
                "processed": 0,
                "results": [],
                "error_code": "SOURCE_PATH_NOT_ALLOWED",
                "error_message": f"Source path is outside allowed roots: {source_path}",
                "hint": "Store managed skills under the configured allowed roots before testing.",
            }

        try:
            from skill_tester import SkillEquivalenceTester
            from datetime import datetime as _dt

            tester = SkillEquivalenceTester()
            test_result = tester.test_fidelity(resolved_source_path, resolved_installed_path)

            test_data = {
                "tested_at": _dt.now().isoformat(),
                "tester_version": getattr(tester, "VERSION", "1.0.0"),
                "original_path": str(resolved_source_path),
                "converted_path": str(resolved_installed_path),
                "scores": {
                    "semantic_similarity": test_result.semantic_similarity,
                    "structure_similarity": test_result.structure_similarity,
                    "keyword_similarity": test_result.keyword_similarity,
                    "metadata_completeness": test_result.metadata_completeness,
                    "overall": test_result.overall_score,
                },
                "passed": test_result.passed,
            }
            self.db.record_equivalence_test(skill_id, test_data)
            current_revision = self.db.get_current_revision(skill_id)

            item = {
                "skill_id": skill_id,
                "revision_id": current_revision.revision_id if current_revision else None,
                "status": "success",
                "fidelity_score": test_result.overall_score,
                "overall_score": test_result.overall_score,
                "passed": test_result.passed,
            }
            return {
                "status": "success",
                "skill_id": skill_id,
                "revision_id": current_revision.revision_id if current_revision else None,
                "processed": 1,
                "results": [item],
            }
        except Exception as exc:
            return {
                "status": "failed",
                "skill_id": skill_id,
                "processed": 0,
                "results": [],
                "error_code": "TEST_RUNTIME_ERROR",
                "error_message": str(exc),
                "hint": "Check that both source and installed paths contain valid skill files.",
            }

    def run_test_batch(self, skill_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run fidelity test for multiple skills (pending by default)"""
        if skill_ids is not None and len(skill_ids) == 0:
            return {"status": "noop", "processed": 0, "results": []}

        skills = self.db.list_skills(status="pending", limit=1000)
        targets = [s for s in skills if skill_ids is None or s.skill_id in skill_ids]

        if not targets:
            return {"status": "noop", "processed": 0, "results": []}

        results = []
        for skill in targets:
            result = self.run_test(skill.skill_id)
            results.append(result)

        success_count = sum(1 for r in results if r.get("status") == "success")
        overall = (
            "success"
            if success_count == len(results)
            else ("failed" if success_count == 0 else "partial")
        )
        return {
            "status": overall,
            "processed": len(results),
            "results": results,
        }

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
                "revision_id": e.get("revision_id"),
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
