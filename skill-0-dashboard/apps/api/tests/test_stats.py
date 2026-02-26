"""Stats router 測試（/api/stats/*）"""

import pytest


def test_get_stats_overview(client, auth_header):
    """GET /api/stats 回傳概覽統計資料。"""
    response = client.get("/api/stats", headers=auth_header)
    assert response.status_code == 200
    data = response.json()
    assert "total_skills" in data
    assert data["total_skills"] == 10
    assert "pending_count" in data
    assert "approved_count" in data
    assert "rejected_count" in data
    assert "blocked_count" in data
    assert "high_risk_count" in data
    assert "avg_equivalence_score" in data


def test_get_risk_distribution(client, auth_header):
    """GET /api/stats/risk-distribution 回傳各風險等級分佈。"""
    response = client.get("/api/stats/risk-distribution", headers=auth_header)
    assert response.status_code == 200
    data = response.json()
    # 確認預設 mock 數據的 key 都存在
    for key in ("safe", "low", "medium", "high", "critical", "blocked"):
        assert key in data
    assert data["safe"] == 3
    assert data["high"] == 2


def test_get_status_distribution(client, auth_header):
    """GET /api/stats/status-distribution 回傳各狀態分佈。"""
    response = client.get("/api/stats/status-distribution", headers=auth_header)
    assert response.status_code == 200
    data = response.json()
    for key in ("pending", "approved", "rejected", "blocked"):
        assert key in data
    assert data["approved"] == 5
    assert data["pending"] == 3


def test_get_findings_by_rule(client, auth_header):
    """GET /api/stats/findings-by-rule 回傳依規則彙總的 findings 清單。"""
    response = client.get("/api/stats/findings-by-rule", headers=auth_header)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    finding = data[0]
    assert finding["rule_id"] == "SEC001"
    assert finding["rule_name"] == "Prompt Injection"
    assert finding["severity"] == "high"
    assert finding["count"] == 5


def test_stats_unauthorized(client):
    """不帶 token 訪問 /api/stats 應回傳 401。"""
    response = client.get("/api/stats")
    assert response.status_code == 401
