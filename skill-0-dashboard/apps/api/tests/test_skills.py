"""Skills router 測試（/api/skills/*）"""

import pytest


def test_list_skills_default(client, auth_header):
    """GET /api/skills 回傳預設分頁的技能清單。"""
    response = client.get("/api/skills", headers=auth_header)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert data["total"] == 1
    assert data["page"] == 1
    assert len(data["items"]) == 1
    skill = data["items"][0]
    assert skill["skill_id"] == "sk_001"
    assert skill["name"] == "Test Skill"


def test_list_skills_with_filters(client, auth_header, mock_service):
    """GET /api/skills 支援 status、risk_level、search 等過濾參數。"""
    response = client.get(
        "/api/skills",
        headers=auth_header,
        params={
            "status": "approved",
            "risk_level": "low",
            "search": "Test",
            "page": 1,
            "page_size": 10,
            "sort_by": "name",
            "sort_order": "asc",
        },
    )
    assert response.status_code == 200
    # 確認 service 被正確呼叫（帶上 filter 參數）
    mock_service.list_skills.assert_called_once_with(
        page=1,
        page_size=10,
        status="approved",
        risk_level="low",
        search="Test",
        sort_by="name",
        sort_order="asc",
    )


def test_get_skill_found(client, auth_header, mock_service):
    """GET /api/skills/{skill_id} 找到技能時回傳 200 與詳細資料。"""
    mock_service.get_skill.return_value = {
        "skill_id": "sk_001",
        "name": "Test Skill",
        "status": "approved",
        "risk_level": "low",
        "risk_score": 15,
        "equivalence_score": 0.92,
        "author_name": "test",
        "license_spdx": "MIT",
        "source_url": "",
        "source_type": "github",
        "source_path": "/path/to/skill",
        "version": "1.0.0",
        "created_at": "2026-01-01T00:00:00",
        "updated_at": "2026-01-01T00:00:00",
        "security_findings": [],
        "scan_history": [],
        "test_history": [],
        "audit_events": [],
    }
    response = client.get("/api/skills/sk_001", headers=auth_header)
    assert response.status_code == 200
    data = response.json()
    assert data["skill_id"] == "sk_001"
    assert data["name"] == "Test Skill"


def test_get_skill_not_found(client, auth_header, mock_service):
    """GET /api/skills/{skill_id} 找不到技能時回傳 404。"""
    mock_service.get_skill.return_value = None
    response = client.get("/api/skills/nonexistent_id", headers=auth_header)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_trigger_scan_stub(client, auth_header):
    """POST /api/skills/scan 回傳 queued 狀態（stub 端點）。"""
    response = client.post(
        "/api/skills/scan",
        headers=auth_header,
        params={"skill_id": "sk_001"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "queued"
    assert "sk_001" in data["message"]


def test_trigger_test_stub(client, auth_header):
    """POST /api/skills/test 回傳 queued 狀態（stub 端點）。"""
    response = client.post(
        "/api/skills/test",
        headers=auth_header,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "queued"
    assert "message" in data
