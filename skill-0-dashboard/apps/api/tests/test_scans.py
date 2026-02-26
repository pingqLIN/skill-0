"""Scans router 測試（/api/scans/*）"""

import pytest


def test_list_scans(client, auth_header, mock_service):
    """GET /api/scans 回傳掃描清單（空清單為預設）。"""
    response = client.get("/api/scans", headers=auth_header)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0
    mock_service.list_scans.assert_called_once()


def test_get_skill_scans(client, auth_header, mock_service):
    """GET /api/scans/{skill_id} 回傳指定技能的掃描歷史。"""
    response = client.get("/api/scans/sk_001", headers=auth_header)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    mock_service.get_skill_scans.assert_called_once_with("sk_001")


def test_export_scan_json(client, auth_header, mock_service):
    """GET /api/scans/{skill_id}/export 找到技能與掃描時回傳 JSON export。"""
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
    mock_service.get_skill_scans.return_value = [
        {
            "scan_id": "scan_001",
            "scanned_at": "2026-01-15T10:00:00",
            "risk_level": "low",
            "risk_score": 10,
            "findings_count": 1,
            "findings": [],
            "files_scanned": 3,
            "blocked": False,
        }
    ]
    response = client.get(
        "/api/scans/sk_001/export",
        headers=auth_header,
        params={"format": "json"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["skill_id"] == "sk_001"
    assert data["skill_name"] == "Test Skill"
    assert "scan" in data
    assert "detection_standards" in data
    assert "export_date" in data


def test_export_scan_not_found(client, auth_header, mock_service):
    """GET /api/scans/{skill_id}/export 找不到技能時應回傳 404。"""
    mock_service.get_skill.return_value = None
    response = client.get(
        "/api/scans/nonexistent/export",
        headers=auth_header,
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
