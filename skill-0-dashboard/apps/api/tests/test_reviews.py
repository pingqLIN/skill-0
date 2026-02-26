"""Reviews router 測試（/api/reviews/*）"""

import pytest


def test_list_pending_reviews(client, auth_header, mock_service):
    """GET /api/reviews 回傳待審技能清單（空清單為預設）。"""
    response = client.get("/api/reviews", headers=auth_header)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0  # mock 預設回傳空清單


def test_approve_skill_success(client, auth_header, mock_service):
    """POST /api/reviews/{skill_id}/approve 成功時回傳 200 與 approved 狀態。"""
    mock_service.approve_skill.return_value = True
    response = client.post(
        "/api/reviews/sk_001/approve",
        headers=auth_header,
        json={"reviewer": "admin", "reason": "LGTM"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "approved"
    assert data["skill_id"] == "sk_001"
    assert data["reviewer"] == "admin"
    assert data["reason"] == "LGTM"
    mock_service.approve_skill.assert_called_once_with(
        "sk_001", reviewer="admin", reason="LGTM"
    )


def test_approve_skill_fail(client, auth_header, mock_service):
    """POST /api/reviews/{skill_id}/approve 失敗（service 回傳 False）時應回傳 400。"""
    mock_service.approve_skill.return_value = False
    response = client.post(
        "/api/reviews/sk_blocked/approve",
        headers=auth_header,
        json={"reviewer": "admin", "reason": "Try anyway"},
    )
    assert response.status_code == 400
    assert "detail" in response.json()


def test_reject_skill_success(client, auth_header, mock_service):
    """POST /api/reviews/{skill_id}/reject 成功時回傳 200 與 rejected 狀態。"""
    mock_service.reject_skill.return_value = True
    response = client.post(
        "/api/reviews/sk_001/reject",
        headers=auth_header,
        json={"reviewer": "admin", "reason": "Security issue"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "rejected"
    assert data["skill_id"] == "sk_001"
    assert data["reviewer"] == "admin"
    assert data["reason"] == "Security issue"
    mock_service.reject_skill.assert_called_once_with(
        "sk_001", reviewer="admin", reason="Security issue"
    )


def test_reject_skill_fail(client, auth_header, mock_service):
    """POST /api/reviews/{skill_id}/reject 失敗（service 回傳 False）時應回傳 400。"""
    mock_service.reject_skill.return_value = False
    response = client.post(
        "/api/reviews/nonexistent/reject",
        headers=auth_header,
        json={"reviewer": "admin", "reason": "Reason"},
    )
    assert response.status_code == 400
    assert "detail" in response.json()
