"""Audit router 測試（/api/audit）"""

import pytest


def test_get_audit_log_default(client, auth_header, mock_service):
    """GET /api/audit 使用預設參數回傳 audit log。"""
    response = client.get("/api/audit", headers=auth_header)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert isinstance(data["items"], list)
    assert data["total"] == 0
    assert data["page"] == 1
    # 確認 service 以預設值被呼叫
    mock_service.get_audit_log.assert_called_once_with(
        page=1,
        page_size=50,
        skill_id=None,
        event_type=None,
        from_date=None,
        to_date=None,
    )


def test_get_audit_log_with_filters(client, auth_header, mock_service):
    """GET /api/audit 支援 skill_id 與 event_type 過濾。"""
    response = client.get(
        "/api/audit",
        headers=auth_header,
        params={
            "skill_id": "sk_001",
            "event_type": "approved",
        },
    )
    assert response.status_code == 200
    mock_service.get_audit_log.assert_called_once_with(
        page=1,
        page_size=50,
        skill_id="sk_001",
        event_type="approved",
        from_date=None,
        to_date=None,
    )


def test_get_audit_log_pagination(client, auth_header, mock_service):
    """GET /api/audit 支援 page / page_size 分頁參數。"""
    response = client.get(
        "/api/audit",
        headers=auth_header,
        params={"page": 2, "page_size": 10},
    )
    assert response.status_code == 200
    mock_service.get_audit_log.assert_called_once_with(
        page=2,
        page_size=10,
        skill_id=None,
        event_type=None,
        from_date=None,
        to_date=None,
    )


def test_audit_unauthorized(client):
    """不帶 token 訪問 /api/audit 應回傳 401。"""
    response = client.get("/api/audit")
    assert response.status_code == 401
