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
        "current_revision_id": "rev_002",
        "revision_id": "rev_002",
        "revision_number": 2,
        "name": "Test Skill",
        "status": "approved",
        "risk_level": "low",
        "risk_score": 15,
        "fidelity_score": 0.92,
        "equivalence_score": 0.92,
        "author_name": "test",
        "license_spdx": "MIT",
        "source_url": "",
        "source_checksum": "checksum-002",
        "source_type": "github",
        "source_path": "/path/to/skill",
        "version": "1.0.0",
        "created_at": "2026-01-01T00:00:00",
        "updated_at": "2026-01-01T00:00:00",
        "security_findings": [],
        "scan_history": [],
        "test_history": [],
        "audit_events": [],
        "revision_history": [],
    }
    response = client.get("/api/skills/sk_001", headers=auth_header)
    assert response.status_code == 200
    data = response.json()
    assert data["skill_id"] == "sk_001"
    assert data["name"] == "Test Skill"
    assert data["current_revision_id"] == "rev_002"
    assert data["revision_number"] == 2
    assert data["fidelity_score"] == 0.92


def test_get_skill_not_found(client, auth_header, mock_service):
    """GET /api/skills/{skill_id} 找不到技能時回傳 404。"""
    mock_service.get_skill.return_value = None
    response = client.get("/api/skills/nonexistent_id", headers=auth_header)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_skill_revisions(client, auth_header, mock_service):
    """GET /api/skills/{skill_id}/revisions 回傳 revision 清單。"""
    mock_service.get_skill_revisions.return_value = [
        {
            "revision_id": "rev_002",
            "revision_number": 2,
            "status": "approved",
            "version": "2.0.0",
            "source_commit": "def45678",
            "source_path": "/path/to/skill",
            "source_checksum": "checksum-002",
            "risk_level": "low",
            "risk_score": 10,
            "fidelity_score": 0.95,
            "equivalence_score": 0.95,
            "approved_by": "admin",
            "approved_at": "2026-01-02T00:00:00",
            "created_at": "2026-01-02T00:00:00",
            "updated_at": "2026-01-02T00:00:00",
            "is_current": True,
        }
    ]

    response = client.get("/api/skills/sk_001/revisions", headers=auth_header)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["revision_id"] == "rev_002"
    assert data[0]["revision_number"] == 2
    mock_service.get_skill_revisions.assert_called_once_with("sk_001")


def test_trigger_scan_action_result(client, auth_header):
    """POST /api/skills/scan 回傳目前 ActionResult 格式。"""
    response = client.post(
        "/api/skills/scan",
        headers=auth_header,
        params={"skill_id": "sk_001"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["skill_id"] == "sk_001"
    assert data["processed"] == 1
    assert data["results"][0]["skill_id"] == "sk_001"


def test_trigger_test_batch_action_result(client, auth_header):
    """POST /api/skills/test（未指定 skill）回傳批次 ActionResult。"""
    response = client.post(
        "/api/skills/test",
        headers=auth_header,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "noop"
    assert data["processed"] == 0
    assert data["results"] == []


def test_enqueue_scan_job(client, auth_header, mock_service):
    response = client.post(
        "/api/skills/scan-jobs",
        headers=auth_header,
        json={"skill_ids": ["sk_001"], "selection_mode": "explicit", "max_attempts": 2},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["job_type"] == "scan_batch"
    assert data["status"] == "queued"
    mock_service.enqueue_action_job.assert_called_once_with(
        job_type="scan_batch",
        skill_ids=["sk_001"],
        requested_by="testuser",
        selection_mode="explicit",
        max_attempts=2,
    )


def test_get_action_job(client, auth_header, mock_service):
    response = client.get(
        "/api/skills/action-jobs/job_scan_20260402_001",
        headers=auth_header,
    )
    assert response.status_code == 200
    assert response.json()["job_id"] == "job_scan_20260402_001"
    mock_service.get_action_job.assert_called_once_with("job_scan_20260402_001")


def test_get_action_job_items(client, auth_header, mock_service):
    mock_service.get_action_job_items.return_value = [
        {
            "item_id": "job_scan_20260402_001_item_sk_001_01",
            "job_id": "job_scan_20260402_001",
            "skill_id": "sk_001",
            "target_revision_id": "rev_001",
            "action_type": "scan",
            "status": "running",
            "attempt_number": 1,
            "max_attempts": 2,
            "started_at": "2026-04-03T01:00:00Z",
            "completed_at": None,
            "claimed_by": "worker-a",
            "lease_expires_at": "2026-04-03T01:05:00Z",
            "result": None,
            "error_code": None,
            "error_message": None,
            "retry_of_item_id": None,
        }
    ]
    response = client.get(
        "/api/skills/action-jobs/job_scan_20260402_001/items",
        headers=auth_header,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["item_id"] == "job_scan_20260402_001_item_sk_001_01"
    assert data[0]["claimed_by"] == "worker-a"
    assert data[0]["lease_expires_at"] == "2026-04-03T01:05:00Z"
    mock_service.get_action_job_items.assert_called_once_with("job_scan_20260402_001")


def test_retry_action_job_failures(client, auth_header, mock_service):
    response = client.post(
        "/api/skills/action-jobs/job_scan_20260402_001/retry-failures",
        headers=auth_header,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "queued"
    mock_service.retry_action_job_failures.assert_called_once_with(
        job_id="job_scan_20260402_001",
        requested_by="testuser",
    )


def test_cancel_action_job(client, auth_header, mock_service):
    response = client.post(
        "/api/skills/action-jobs/job_scan_20260402_001/cancel",
        headers=auth_header,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "queued"
    mock_service.cancel_action_job.assert_called_once_with(
        job_id="job_scan_20260402_001",
        requested_by="testuser",
    )


def test_retry_action_job_item(client, auth_header, mock_service):
    response = client.post(
        "/api/skills/action-jobs/job_scan_20260402_001/items/job_scan_20260402_001_item_sk_001_01/retry",
        headers=auth_header,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "queued"
    mock_service.retry_action_job_item.assert_called_once_with(
        job_id="job_scan_20260402_001",
        item_id="job_scan_20260402_001_item_sk_001_01",
        requested_by="testuser",
    )
