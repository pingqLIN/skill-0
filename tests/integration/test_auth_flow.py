"""
整合測試：認證流程（authentication flow）

測試範圍：
  - 登入成功 / 失敗
  - 受保護端點的 token 驗證（有效、過期、無效格式）
  - 不需要認證的公開端點
  - /api/auth/me 完整流程

前置條件：
  tests/conftest.py 在 import api.main 前設定好所有必要環境變數，
  包括 SKILL0_ENV=development、API_USERNAME=testadmin、API_PASSWORD=testpass123。
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

# 使用 setdefault 確保 conftest.py 優先設定的值不被覆蓋
os.environ.setdefault("SKILL0_ENV", "development")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key")
os.environ.setdefault("API_USERNAME", "testadmin")
os.environ.setdefault("API_PASSWORD", "testpass123")
os.environ.setdefault("API_RATE_LIMIT", "1000/minute")
os.environ.setdefault("AUTH_RATE_LIMIT", "100/minute")

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


# ==================== 登入端點 ====================


def test_login_success():
    """有效憑證回傳 JWT token。"""
    resp = client.post(
        "/api/auth/token",
        json={"username": "testadmin", "password": "testpass123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data.get("expires_in", 0) > 0


def test_login_invalid_credentials():
    """錯誤密碼應回傳 401。"""
    resp = client.post(
        "/api/auth/token",
        json={"username": "testadmin", "password": "wrongpassword"},
    )
    assert resp.status_code == 401


def test_login_wrong_username():
    """不存在的使用者名稱應回傳 401。"""
    resp = client.post(
        "/api/auth/token",
        json={"username": "nobody", "password": "testpass123"},
    )
    assert resp.status_code == 401


def test_login_missing_body():
    """缺少 request body 應回傳 422（驗證錯誤）。"""
    resp = client.post("/api/auth/token")
    assert resp.status_code == 422


def test_login_missing_password_field():
    """缺少 password 欄位應回傳 422。"""
    resp = client.post("/api/auth/token", json={"username": "testadmin"})
    assert resp.status_code == 422


# ==================== 受保護端點 - 無 token ====================


def test_protected_index_without_token():
    """不帶 token 存取 /api/index 應回傳 401。"""
    resp = client.post("/api/index", json={"parsed_dir": "parsed"})
    assert resp.status_code == 401


def test_protected_me_without_token():
    """不帶 token 存取 /api/auth/me 應回傳 401。"""
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


# ==================== 完整認證流程 ====================


def test_full_auth_flow_me_endpoint():
    """登入後使用 token 存取 /api/auth/me 應成功並回傳正確使用者資訊。"""
    # 登入
    login_resp = client.post(
        "/api/auth/token",
        json={"username": "testadmin", "password": "testpass123"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    assert token

    # 使用 token 存取 /api/auth/me
    me_resp = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_resp.status_code == 200
    data = me_resp.json()
    assert data["username"] == "testadmin"
    assert "exp" in data


def test_token_reusable_within_expiry():
    """同一個 token 可在有效期內重複使用。"""
    login_resp = client.post(
        "/api/auth/token",
        json={"username": "testadmin", "password": "testpass123"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 連續呼叫兩次，兩次都應成功
    for _ in range(2):
        resp = client.get("/api/auth/me", headers=headers)
        assert resp.status_code == 200


# ==================== 無效 token 場景 ====================


def test_expired_token_rejected():
    """過期的 JWT 應回傳 401。"""
    import jwt
    from datetime import datetime, timedelta, timezone

    expired_token = jwt.encode(
        {
            "sub": "testadmin",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        },
        "test-secret-key",
        algorithm="HS256",
    )
    resp = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert resp.status_code == 401


def test_invalid_token_string_rejected():
    """任意非 JWT 字串應回傳 401。"""
    resp = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert resp.status_code == 401


def test_token_with_wrong_secret_rejected():
    """用錯誤 secret 簽名的 JWT 應回傳 401。"""
    import jwt
    from datetime import datetime, timedelta, timezone

    forged_token = jwt.encode(
        {
            "sub": "testadmin",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        },
        "wrong-secret",
        algorithm="HS256",
    )
    resp = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {forged_token}"},
    )
    assert resp.status_code == 401


def test_malformed_auth_header_rejected():
    """Authorization header 格式錯誤（無 Bearer 前綴）應回傳 401/403。"""
    resp = client.get(
        "/api/auth/me",
        headers={"Authorization": "Token some-token"},
    )
    assert resp.status_code in (401, 403)


# ==================== 公開端點（不需要認證）====================


def test_health_no_auth():
    """
    健康檢查端點不需要認證。
    在沒有 DB 或 ML 模型的測試環境中，可能回傳 503（Service Unavailable）；
    但不應回傳 401（需要認證）或 405（方法不允許）。
    """
    resp = client.get("/health")
    # 200 表示 DB 存在且健康；503 表示 DB 或 ML 模型不可用
    # 無論如何，都不應回傳 401（認證問題）
    assert resp.status_code in (200, 503)


def test_health_detail_no_auth():
    """/api/health/detail 不需要認證，且回傳 status 欄位。"""
    resp = client.get("/api/health/detail")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data


def test_root_no_auth():
    """根端點 / 不需要認證。"""
    resp = client.get("/")
    assert resp.status_code == 200


def test_docs_accessible():
    """Swagger UI /docs 不需要認證。"""
    resp = client.get("/docs")
    assert resp.status_code == 200


def test_redoc_accessible():
    """ReDoc /redoc 不需要認證。"""
    resp = client.get("/redoc")
    assert resp.status_code == 200
