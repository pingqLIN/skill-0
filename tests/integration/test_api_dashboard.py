"""
Integration tests for the Governance Dashboard API (skill-0-dashboard/apps/api)

Tests all dashboard endpoints with real governance.db:
  - Root, health
  - Stats (overview, risk distribution, status distribution, findings by rule)
  - Skills (list with filters, detail, scan stub, test stub)
  - Reviews (list pending, approve, reject)
  - Scans (list, skill scans, export)
  - Audit log (paginated, filtered)
"""

import sys
from pathlib import Path

import pytest

# Ensure project root tools are importable for GovernanceService
_PROJECT_ROOT = Path(__file__).parent.parent.parent
_TOOLS_DIR = _PROJECT_ROOT / "tools"
_DASHBOARD_API_DIR = _PROJECT_ROOT / "skill-0-dashboard" / "apps"

# CRITICAL: Remove any cached 'api' module from core API tests
# to prevent importing the wrong app
for _key in list(sys.modules.keys()):
    if _key == 'api' or _key.startswith('api.'):
        del sys.modules[_key]

# Insert dashboard paths BEFORE project root
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))
if str(_DASHBOARD_API_DIR) not in sys.path:
    sys.path.insert(0, str(_DASHBOARD_API_DIR))

from fastapi.testclient import TestClient
from api.main import app  # Now imports dashboard API, not core API


@pytest.fixture
def client():
    """TestClient for the Governance Dashboard API"""
    return TestClient(app)


# ==================== Root & Health ====================


class TestDashboardRootAndHealth:
    """Tests for root and health endpoints"""

    def test_root(self, client):
        """GET / returns API info"""
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Skill-0 Governance API"
        assert data["version"] == "1.0.0"
        assert "docs" in data

    def test_health(self, client):
        """GET /health returns healthy"""
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"


# ==================== Stats ====================


class TestDashboardStats:
    """Tests for statistics endpoints"""

    def test_stats_overview(self, client):
        """GET /api/stats returns overview statistics"""
        resp = client.get("/api/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_skills" in data
        assert data["total_skills"] >= 0
        assert "pending_count" in data
        assert "approved_count" in data
        assert "rejected_count" in data
        assert "blocked_count" in data
        assert "high_risk_count" in data
        assert "avg_equivalence_score" in data

    def test_risk_distribution(self, client):
        """GET /api/stats/risk-distribution returns risk counts"""
        resp = client.get("/api/stats/risk-distribution")
        assert resp.status_code == 200
        data = resp.json()
        # All risk levels should be present (defaults to 0)
        for key in ("safe", "low", "medium", "high", "critical", "blocked"):
            assert key in data
            assert isinstance(data[key], int)

    def test_status_distribution(self, client):
        """GET /api/stats/status-distribution returns status counts"""
        resp = client.get("/api/stats/status-distribution")
        assert resp.status_code == 200
        data = resp.json()
        for key in ("pending", "approved", "rejected", "blocked"):
            assert key in data
            assert isinstance(data[key], int)

    def test_findings_by_rule(self, client):
        """GET /api/stats/findings-by-rule returns aggregated findings"""
        resp = client.get("/api/stats/findings-by-rule")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        if len(data) > 0:
            item = data[0]
            assert "rule_id" in item
            assert "rule_name" in item
            assert "severity" in item
            assert "count" in item


# ==================== Skills ====================


class TestDashboardSkills:
    """Tests for skills listing, detail, and stubs"""

    def test_list_skills_default(self, client):
        """GET /api/skills returns paginated list"""
        resp = client.get("/api/skills")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert data["page"] == 1
        assert data["page_size"] == 20
        assert isinstance(data["items"], list)

    def test_list_skills_with_pagination(self, client):
        """GET /api/skills with custom page/page_size"""
        resp = client.get("/api/skills", params={"page": 1, "page_size": 5})
        assert resp.status_code == 200
        data = resp.json()
        assert data["page_size"] == 5
        assert len(data["items"]) <= 5

    def test_list_skills_with_sort(self, client):
        """GET /api/skills with sort_by and sort_order"""
        resp = client.get(
            "/api/skills",
            params={"sort_by": "name", "sort_order": "asc", "page_size": 5},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["items"], list)

    def test_list_skills_with_search(self, client):
        """GET /api/skills with search filter"""
        resp = client.get("/api/skills", params={"search": "skill", "page_size": 5})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["items"], list)

    def test_get_skill_found(self, client):
        """GET /api/skills/{skill_id} returns skill detail"""
        # Get a real skill_id from the list
        list_resp = client.get("/api/skills", params={"page_size": 1})
        items = list_resp.json()["items"]
        if len(items) == 0:
            pytest.skip("No skills in governance DB")

        skill_id = items[0]["skill_id"]
        resp = client.get(f"/api/skills/{skill_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["skill_id"] == skill_id
        assert "name" in data
        assert "status" in data
        assert "risk_level" in data

    def test_get_skill_not_found(self, client):
        """GET /api/skills/nonexistent returns 404"""
        resp = client.get("/api/skills/nonexistent-skill-xyz-99999")
        assert resp.status_code == 404

    def test_trigger_scan_stub(self, client):
        """POST /api/skills/scan returns queued status (stub)"""
        resp = client.post("/api/skills/scan")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "queued"
        assert "queued" in data["message"]

    def test_trigger_scan_with_skill_id(self, client):
        """POST /api/skills/scan?skill_id=xxx includes skill in message"""
        resp = client.post("/api/skills/scan", params={"skill_id": "test-skill"})
        assert resp.status_code == 200
        data = resp.json()
        assert "test-skill" in data["message"]

    def test_trigger_test_stub(self, client):
        """POST /api/skills/test returns queued status (stub)"""
        resp = client.post("/api/skills/test")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "queued"


# ==================== Reviews ====================


class TestDashboardReviews:
    """Tests for review endpoints"""

    def test_list_pending_reviews(self, client):
        """GET /api/reviews returns list of pending skills"""
        resp = client.get("/api/reviews")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        # Each item should have SkillSummary fields
        if len(data) > 0:
            item = data[0]
            assert "skill_id" in item
            assert "name" in item
            assert "status" in item

    def test_approve_skill(self, client):
        """POST /api/reviews/{id}/approve approves a pending skill"""
        # Find a pending skill
        reviews = client.get("/api/reviews").json()
        if len(reviews) == 0:
            pytest.skip("No pending reviews to test approval")

        skill_id = reviews[0]["skill_id"]
        resp = client.post(
            f"/api/reviews/{skill_id}/approve",
            json={"reviewer": "test-admin", "reason": "Integration test approval"},
        )
        # May succeed or fail depending on state
        assert resp.status_code in (200, 400)
        if resp.status_code == 200:
            data = resp.json()
            assert data["status"] == "approved"
            assert data["skill_id"] == skill_id

    def test_reject_skill(self, client):
        """POST /api/reviews/{id}/reject rejects a skill"""
        reviews = client.get("/api/reviews").json()
        if len(reviews) == 0:
            pytest.skip("No pending reviews to test rejection")

        skill_id = reviews[0]["skill_id"]
        resp = client.post(
            f"/api/reviews/{skill_id}/reject",
            json={"reviewer": "test-admin", "reason": "Integration test rejection"},
        )
        assert resp.status_code in (200, 400)
        if resp.status_code == 200:
            data = resp.json()
            assert data["status"] == "rejected"

    def test_approve_invalid_skill(self, client):
        """POST /api/reviews/invalid/approve returns 400"""
        resp = client.post(
            "/api/reviews/nonexistent-xyz/approve",
            json={"reviewer": "admin", "reason": "test"},
        )
        assert resp.status_code == 400

    def test_reject_missing_body(self, client):
        """POST /api/reviews/{id}/reject without body returns 422"""
        resp = client.post("/api/reviews/some-id/reject")
        assert resp.status_code == 422


# ==================== Scans ====================


class TestDashboardScans:
    """Tests for scan history endpoints"""

    def test_list_scans(self, client):
        """GET /api/scans returns list of recent scans"""
        resp = client.get("/api/scans")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        if len(data) > 0:
            item = data[0]
            assert "scan_id" in item
            assert "skill_id" in item
            assert "risk_level" in item

    def test_list_scans_with_limit(self, client):
        """GET /api/scans?limit=5 respects limit"""
        resp = client.get("/api/scans", params={"limit": 5})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) <= 5

    def test_get_skill_scans(self, client):
        """GET /api/scans/{skill_id} returns scan history"""
        # Get a skill that has scans
        scans = client.get("/api/scans", params={"limit": 1}).json()
        if len(scans) == 0:
            pytest.skip("No scans in governance DB")

        skill_id = scans[0]["skill_id"]
        resp = client.get(f"/api/scans/{skill_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_export_scan_found(self, client):
        """GET /api/scans/{skill_id}/export returns export data"""
        scans = client.get("/api/scans", params={"limit": 1}).json()
        if len(scans) == 0:
            pytest.skip("No scans for export test")

        skill_id = scans[0]["skill_id"]
        resp = client.get(f"/api/scans/{skill_id}/export")
        assert resp.status_code == 200
        data = resp.json()
        assert "skill_name" in data
        assert "scan" in data
        assert "detection_standards" in data

    def test_export_scan_html(self, client):
        """GET /api/scans/{skill_id}/export?format=html returns HTML"""
        scans = client.get("/api/scans", params={"limit": 1}).json()
        if len(scans) == 0:
            pytest.skip("No scans for HTML export test")

        skill_id = scans[0]["skill_id"]
        resp = client.get(
            f"/api/scans/{skill_id}/export", params={"format": "html"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "html" in data
        assert "<!DOCTYPE html>" in data["html"]

    def test_export_scan_not_found(self, client):
        """GET /api/scans/nonexistent/export returns 404"""
        resp = client.get("/api/scans/nonexistent-xyz-99/export")
        assert resp.status_code == 404


# ==================== Audit ====================


class TestDashboardAudit:
    """Tests for audit log endpoint"""

    def test_audit_log_default(self, client):
        """GET /api/audit returns paginated audit log"""
        resp = client.get("/api/audit")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert data["page"] == 1
        assert data["page_size"] == 50
        assert isinstance(data["items"], list)

    def test_audit_log_pagination(self, client):
        """GET /api/audit with custom page_size"""
        resp = client.get("/api/audit", params={"page_size": 5})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) <= 5

    def test_audit_log_filter_by_event_type(self, client):
        """GET /api/audit with event_type filter"""
        resp = client.get("/api/audit", params={"event_type": "scan"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["items"], list)

    def test_audit_log_filter_by_skill_id(self, client):
        """GET /api/audit with skill_id filter"""
        resp = client.get("/api/audit", params={"skill_id": "some-skill"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["items"], list)


# ==================== Error Handling ====================


class TestDashboardErrors:
    """Tests for error responses"""

    def test_404_unknown_route(self, client):
        """Unknown route returns 404"""
        resp = client.get("/api/nonexistent")
        assert resp.status_code in (404, 405)

    def test_invalid_page_param(self, client):
        """GET /api/skills?page=0 returns 422"""
        resp = client.get("/api/skills", params={"page": 0})
        assert resp.status_code == 422

    def test_invalid_page_size_too_large(self, client):
        """GET /api/skills?page_size=200 returns 422"""
        resp = client.get("/api/skills", params={"page_size": 200})
        assert resp.status_code == 422


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
