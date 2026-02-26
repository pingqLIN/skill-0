"""Auth / JWT 認證相關測試。

測試範圍：
- 無需認證的公開端點（/, /health, /docs, /openapi.json）
- /api/* 端點的 401 行為（無 token、過期 token、無效 token）
- 帶有效 token 時可正常訪問 /api/stats
"""

import pytest


def test_health_no_auth_required(client):
    """/health 端點不需要 JWT。"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_root_no_auth_required(client):
    """根路由 / 不需要 JWT。"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Skill-0 Governance API"
    assert "docs" in data


def test_docs_no_auth_required(client):
    """/docs (Swagger UI) 不需要 JWT。"""
    response = client.get("/docs")
    assert response.status_code == 200


def test_openapi_no_auth_required(client):
    """/openapi.json schema 端點不需要 JWT。"""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert "openapi" in response.json()


def test_api_endpoint_requires_auth(client):
    """不帶 token 訪問 /api/stats 應回傳 401。"""
    response = client.get("/api/stats")
    assert response.status_code == 401


def test_api_endpoint_with_valid_token(client, auth_header):
    """帶有效 token 訪問 /api/stats 應回傳 200。"""
    response = client.get("/api/stats", headers=auth_header)
    assert response.status_code == 200


def test_api_endpoint_with_expired_token(client, expired_token_header):
    """帶過期 token 訪問 /api/stats 應回傳 401。"""
    response = client.get("/api/stats", headers=expired_token_header)
    assert response.status_code == 401


def test_api_endpoint_with_invalid_token(client):
    """帶無效（亂碼）token 訪問 /api/stats 應回傳 401。"""
    response = client.get(
        "/api/stats",
        headers={"Authorization": "Bearer this.is.not.a.valid.jwt"},
    )
    assert response.status_code == 401
