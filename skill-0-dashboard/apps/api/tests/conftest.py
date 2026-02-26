"""Shared fixtures for Dashboard API tests."""

import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

# 設定環境變數必須在 import app 之前
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("SKILL0_GOVERNANCE_DB_PATH", ":memory:")

# 確保 skill-0-dashboard 目錄在 sys.path 中，使得 from apps.api.xxx import 可用
_DASHBOARD_ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "..")
sys.path.insert(0, os.path.abspath(_DASHBOARD_ROOT))

import jwt as pyjwt
from fastapi.testclient import TestClient


def _make_token(sub: str = "testuser", secret: str = "test-secret") -> str:
    """有效 JWT 產生器（測試用）"""
    payload = {
        "sub": sub,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    return pyjwt.encode(payload, secret, algorithm="HS256")


@pytest.fixture()
def auth_header():
    """帶有效 JWT 的 Authorization header。"""
    token = _make_token()
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def expired_token_header():
    """帶過期 JWT 的 Authorization header。"""
    payload = {
        "sub": "testuser",
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
    }
    token = pyjwt.encode(payload, "test-secret", algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def mock_service():
    """Mock GovernanceService，預設傳回值涵蓋所有 router 使用的方法。"""
    service = MagicMock()

    # --- stats ---
    service.get_stats_overview.return_value = {
        "total_skills": 10,
        "pending_count": 3,
        "approved_count": 5,
        "rejected_count": 1,
        "blocked_count": 1,
        "high_risk_count": 2,
        "avg_equivalence_score": 0.85,
    }
    service.get_risk_distribution.return_value = {
        "safe": 3,
        "low": 2,
        "medium": 2,
        "high": 2,
        "critical": 1,
        "blocked": 0,
    }
    service.get_status_distribution.return_value = {
        "pending": 3,
        "approved": 5,
        "rejected": 1,
        "blocked": 1,
    }
    service.get_findings_by_rule.return_value = [
        {
            "rule_id": "SEC001",
            "rule_name": "Prompt Injection",
            "severity": "high",
            "count": 5,
        },
    ]

    # --- skills ---
    service.list_skills.return_value = {
        "items": [
            {
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
                "version": "1.0.0",
                "created_at": "2026-01-01T00:00:00",
                "updated_at": "2026-01-01T00:00:00",
            }
        ],
        "total": 1,
        "page": 1,
        "page_size": 20,
    }
    service.get_skill.return_value = None  # 各測試自行 override

    # --- reviews ---
    service.get_pending_reviews.return_value = []
    service.approve_skill.return_value = True
    service.reject_skill.return_value = True

    # --- scans ---
    service.list_scans.return_value = []
    service.get_skill_scans.return_value = []

    # --- audit ---
    service.get_audit_log.return_value = {
        "items": [],
        "total": 0,
        "page": 1,
        "page_size": 50,
    }

    return service


@pytest.fixture()
def client(mock_service):
    """TestClient，使用 mock GovernanceService 取代真實 DB 連線。"""
    from apps.api.dependencies import get_governance_service
    from apps.api.main import app

    app.dependency_overrides[get_governance_service] = lambda: mock_service
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
