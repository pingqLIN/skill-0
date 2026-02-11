"""
Integration tests for the Core Skill-0 API (api/main.py)

Tests all 14+ endpoints with real skills.db:
  - Root, health, detailed health
  - Search (POST + GET), similar (POST + GET)
  - Cluster, stats, skills list, skill detail
  - Auth (token, me), protected index endpoint
  - Rate limiting, error cases
"""

import sys
from pathlib import Path

import pytest

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi.testclient import TestClient
from api.main import app, create_access_token, _rate_limit_store, search_engine as _global_engine


@pytest.fixture(autouse=True)
def clear_rate_limits():
    """Clear rate limit store before each test"""
    _rate_limit_store.clear()
    yield
    _rate_limit_store.clear()


@pytest.fixture
def client():
    """TestClient for the core API"""
    # Reset the global search engine to avoid stale SQLite connections
    import api.main as api_module
    api_module.search_engine = None
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Valid JWT authorization headers"""
    token = create_access_token({"sub": "testuser"})
    return {"Authorization": f"Bearer {token}"}


# ==================== Root & Health ====================


class TestRootAndHealth:
    """Tests for root and health endpoints"""

    def test_root_returns_api_info(self, client):
        """GET / returns API name and version"""
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Skill-0 API"
        assert data["version"] == "2.1.0"
        assert "endpoints" in data

    def test_health_check(self, client):
        """GET /health returns healthy status"""
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "total_skills" in data
        assert data["total_skills"] > 0

    def test_health_detail(self, client):
        """GET /api/health/detail returns detailed metrics"""
        resp = client.get("/api/health/detail")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("healthy", "degraded")
        assert data["version"] == "2.1.0"
        assert data["db_exists"] is True
        assert data["db_size_bytes"] > 0
        assert data["total_skills"] > 0
        assert data["uptime_seconds"] >= 0
        assert isinstance(data["embedding_model"], str)


# ==================== Search ====================


class TestSearch:
    """Tests for search endpoints"""

    def test_search_post(self, client):
        """POST /api/search returns results for a valid query"""
        resp = client.post("/api/search", json={"query": "PDF processing", "limit": 3})
        assert resp.status_code == 200
        data = resp.json()
        assert data["query"] == "PDF processing"
        assert data["count"] > 0
        assert data["count"] <= 3
        assert len(data["results"]) == data["count"]
        assert data["latency_ms"] >= 0
        # Each result has required fields
        r = data["results"][0]
        assert "name" in r
        assert "id" in r

    def test_search_get(self, client):
        """GET /api/search?q=... returns results"""
        resp = client.get("/api/search", params={"q": "document", "limit": 5})
        assert resp.status_code == 200
        data = resp.json()
        assert data["query"] == "document"
        assert data["count"] > 0

    def test_search_post_empty_query_rejected(self, client):
        """POST /api/search rejects empty query"""
        resp = client.post("/api/search", json={"query": "", "limit": 5})
        assert resp.status_code == 422

    def test_search_get_missing_query_rejected(self, client):
        """GET /api/search without q param returns 422"""
        resp = client.get("/api/search")
        assert resp.status_code == 422

    def test_search_limit_clamped(self, client):
        """POST /api/search rejects limit > 50"""
        resp = client.post("/api/search", json={"query": "test", "limit": 100})
        assert resp.status_code == 422

    def test_search_limit_zero_rejected(self, client):
        """POST /api/search rejects limit < 1"""
        resp = client.post("/api/search", json={"query": "test", "limit": 0})
        assert resp.status_code == 422


# ==================== Similar ====================


class TestSimilar:
    """Tests for similar skill endpoints"""

    def test_similar_post(self, client):
        """POST /api/similar finds similar skills by name"""
        # First list skills to get a real name
        skills_resp = client.get("/api/skills", params={"page": 1, "per_page": 1})
        skill_name = skills_resp.json()["skills"][0]["name"]

        resp = client.post(
            "/api/similar", json={"skill_name": skill_name, "limit": 3}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] > 0

    def test_similar_get(self, client):
        """GET /api/similar/{skill_name} finds similar skills"""
        skills_resp = client.get("/api/skills", params={"page": 1, "per_page": 1})
        skill_name = skills_resp.json()["skills"][0]["name"]

        resp = client.get(f"/api/similar/{skill_name}", params={"limit": 3})
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] > 0

    def test_similar_not_found(self, client):
        """POST /api/similar returns 404 for nonexistent skill"""
        resp = client.post(
            "/api/similar",
            json={"skill_name": "nonexistent-skill-xyz-12345", "limit": 3},
        )
        assert resp.status_code == 404


# ==================== Cluster ====================


class TestCluster:
    """Tests for cluster analysis endpoint"""

    def test_cluster_default(self, client):
        """GET /api/cluster returns cluster data"""
        resp = client.get("/api/cluster")
        assert resp.status_code == 200
        data = resp.json()
        assert data["n_clusters"] == 5  # default
        assert data["total_skills"] > 0
        assert isinstance(data["clusters"], dict)

    def test_cluster_custom_n(self, client):
        """GET /api/cluster?n=3 returns requested clusters"""
        resp = client.get("/api/cluster", params={"n": 3})
        assert resp.status_code == 200
        data = resp.json()
        assert data["n_clusters"] == 3

    def test_cluster_invalid_n(self, client):
        """GET /api/cluster?n=1 rejects out-of-range"""
        resp = client.get("/api/cluster", params={"n": 1})
        assert resp.status_code == 422


# ==================== Stats ====================


class TestStats:
    """Tests for statistics endpoint"""

    def test_stats(self, client):
        """GET /api/stats returns full statistics"""
        resp = client.get("/api/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_skills"] > 0
        assert data["total_actions"] >= 0
        assert data["total_rules"] >= 0
        assert data["total_directives"] >= 0
        assert data["embedding_dimension"] == 384
        assert isinstance(data["model_name"], str)
        assert isinstance(data["categories"], dict)


# ==================== Skills ====================


class TestSkills:
    """Tests for skills listing and detail endpoints"""

    def test_list_skills_default(self, client):
        """GET /api/skills returns paginated list"""
        resp = client.get("/api/skills")
        assert resp.status_code == 200
        data = resp.json()
        assert "skills" in data
        assert data["page"] == 1
        assert data["per_page"] == 20
        assert data["total"] > 0
        assert data["total_pages"] >= 1
        assert len(data["skills"]) <= data["per_page"]

    def test_list_skills_pagination(self, client):
        """GET /api/skills with page/per_page pagination works"""
        resp = client.get("/api/skills", params={"page": 1, "per_page": 2})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["skills"]) <= 2

        # Page 2 should return different results (if enough skills)
        if data["total"] > 2:
            resp2 = client.get("/api/skills", params={"page": 2, "per_page": 2})
            data2 = resp2.json()
            assert data2["page"] == 2
            # Different skills than page 1
            ids_p1 = {s["id"] for s in data["skills"]}
            ids_p2 = {s["id"] for s in data2["skills"]}
            assert ids_p1.isdisjoint(ids_p2)

    def test_skill_by_id_found(self, client):
        """GET /api/skills/{id} returns skill details"""
        # Get a real skill ID first
        resp_list = client.get("/api/skills", params={"page": 1, "per_page": 1})
        skill_id = resp_list.json()["skills"][0]["id"]

        resp = client.get(f"/api/skills/{skill_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == skill_id
        assert "name" in data

    def test_skill_by_id_not_found(self, client):
        """GET /api/skills/999999 returns 404"""
        resp = client.get("/api/skills/999999")
        assert resp.status_code == 404

    def test_skill_by_id_with_json(self, client):
        """GET /api/skills/{id}?include_json=true includes JSON data"""
        resp_list = client.get("/api/skills", params={"page": 1, "per_page": 1})
        skill_id = resp_list.json()["skills"][0]["id"]

        resp = client.get(
            f"/api/skills/{skill_id}", params={"include_json": True}
        )
        assert resp.status_code == 200


# ==================== Auth ====================


class TestAuth:
    """Tests for authentication endpoints"""

    def test_login_success(self, client):
        """POST /api/auth/token returns access token"""
        resp = client.post(
            "/api/auth/token",
            json={"username": "admin", "password": "secret"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0

    def test_login_empty_credentials(self, client):
        """POST /api/auth/token rejects empty username"""
        resp = client.post(
            "/api/auth/token",
            json={"username": "", "password": "secret"},
        )
        assert resp.status_code == 401

    def test_get_current_user_authenticated(self, client, auth_headers):
        """GET /api/auth/me returns user info with valid token"""
        resp = client.get("/api/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "testuser"
        assert "exp" in data

    def test_get_current_user_no_token(self, client):
        """GET /api/auth/me returns 401 without token"""
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401

    def test_get_current_user_invalid_token(self, client):
        """GET /api/auth/me returns 401 with invalid token"""
        headers = {"Authorization": "Bearer invalid-token-xyz"}
        resp = client.get("/api/auth/me", headers=headers)
        assert resp.status_code == 401

    def test_get_current_user_expired_token(self, client):
        """GET /api/auth/me returns 401 with expired token"""
        from datetime import timedelta

        token = create_access_token(
            {"sub": "testuser"}, expires_delta=timedelta(seconds=-1)
        )
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.get("/api/auth/me", headers=headers)
        assert resp.status_code == 401


# ==================== Protected Endpoints ====================


class TestProtectedEndpoints:
    """Tests for endpoints requiring authentication"""

    def test_index_requires_auth(self, client):
        """POST /api/index returns 401 without token"""
        resp = client.post("/api/index", json={"parsed_dir": "parsed"})
        assert resp.status_code == 401

    def test_index_with_auth(self, client, auth_headers):
        """POST /api/index succeeds with valid token"""
        resp = client.post(
            "/api/index",
            json={"parsed_dir": "parsed"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["indexed_count"] > 0
        assert data["elapsed_seconds"] > 0
        assert "Successfully indexed" in data["message"]


# ==================== Error Handling ====================


class TestErrorHandling:
    """Tests for error responses and edge cases"""

    def test_404_for_unknown_route(self, client):
        """Unknown route returns 404"""
        resp = client.get("/api/nonexistent")
        assert resp.status_code == 404

    def test_search_invalid_json(self, client):
        """POST /api/search with invalid JSON returns 422"""
        resp = client.post(
            "/api/search",
            content="not json",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 422

    def test_similar_missing_body(self, client):
        """POST /api/similar without body returns 422"""
        resp = client.post("/api/similar")
        assert resp.status_code == 422


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
