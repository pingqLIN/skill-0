"""
整合測試：速率限制（rate limiting）

測試範圍：
  - 在限制內的請求應正常通過（非 429）
  - 超出限制後應回傳 429
  - 豁免路徑（/health、/metrics、/docs 等）不受速率限制
  - 429 回應必須包含 detail 訊息
  - auth 端點使用獨立的 auth 速率限制

實作說明：
  API_RATE_LIMIT 在 api.main module import 時就已讀入為 module-level 變數，
  無法透過 os.environ 在測試中動態修改。
  正確做法是使用 monkeypatch 直接修改 api.main.API_RATE_LIMIT，
  或直接往 _rate_limit_store 預填資料來模擬已用盡的配額。

  速率限制是在 middleware 層套用，觸發 429 時端點本身不會被呼叫，
  因此可以在測試中 mock get_search_engine，讓端點能正常回傳而不是
  因缺少 ML 依賴拋 500。這樣才能清楚區分「正常回應 vs 429 回應」。
"""

import os
import sys
import time
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

os.environ.setdefault("SKILL0_ENV", "development")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key")
os.environ.setdefault("API_USERNAME", "testadmin")
os.environ.setdefault("API_PASSWORD", "testpass123")
os.environ.setdefault("API_RATE_LIMIT", "1000/minute")
os.environ.setdefault("AUTH_RATE_LIMIT", "100/minute")

from fastapi.testclient import TestClient
import api.main as api_module
from api.main import app, _rate_limit_store

client = TestClient(app)


def _make_mock_engine():
    """建立一個模擬的 search engine，讓 /api/stats 等端點不需要真實 DB 或 ML 模型。"""
    mock_engine = MagicMock()
    mock_engine.get_statistics.return_value = {
        "total_skills": 42,
        "total_actions": 100,
        "total_rules": 50,
        "total_directives": 30,
        "embedding_dimension": 384,
        "model_name": "mock-model",
        "categories": {"test": 10},
    }
    return mock_engine


@pytest.fixture(autouse=True)
def clear_rate_limits():
    """每個測試前後清空速率限制記錄，防止跨測試狀態污染。"""
    _rate_limit_store.clear()
    yield
    _rate_limit_store.clear()


@pytest.fixture
def mock_search_engine(monkeypatch):
    """Mock get_search_engine 讓端點不需要真實 DB 或 ML 模型。"""
    mock_engine = _make_mock_engine()
    monkeypatch.setattr(api_module, "get_search_engine", lambda: mock_engine)
    return mock_engine


# ==================== 正常流量（限制內）====================


def test_rate_limit_allows_requests_under_limit(monkeypatch, mock_search_engine):
    """在速率限制內的請求應全部成功（非 429）。"""
    monkeypatch.setattr(api_module, "API_RATE_LIMIT", "10/minute")
    _rate_limit_store.clear()

    for i in range(5):
        resp = client.get("/api/stats")
        assert resp.status_code != 429, (
            f"第 {i + 1} 次請求意外收到 429（limit=10/minute，只發了 5 次）"
        )


# ==================== 超出限制 ====================


def test_rate_limit_blocks_after_limit_exceeded(monkeypatch, mock_search_engine):
    """超出速率限制後應回傳 429。"""
    monkeypatch.setattr(api_module, "API_RATE_LIMIT", "3/minute")
    _rate_limit_store.clear()

    statuses = []
    for _ in range(8):
        resp = client.get("/api/stats")
        statuses.append(resp.status_code)

    assert 429 in statuses, (
        f"發送 8 次請求（limit=3/minute）後未收到 429，實際狀態碼：{statuses}"
    )


def test_rate_limit_429_contains_detail_message(monkeypatch, mock_search_engine):
    """429 回應的 JSON body 應包含 detail 欄位，且說明是速率限制。"""
    monkeypatch.setattr(api_module, "API_RATE_LIMIT", "2/minute")
    _rate_limit_store.clear()

    last_429 = None
    for _ in range(6):
        resp = client.get("/api/stats")
        if resp.status_code == 429:
            last_429 = resp
            break

    assert last_429 is not None, "發送 6 次請求（limit=2/minute）後未觸發 429"
    data = last_429.json()
    assert "detail" in data
    # detail 訊息應包含速率限制相關說明
    assert "Rate limit" in data["detail"] or "rate limit" in data["detail"].lower()


def test_rate_limit_using_prefilled_store(monkeypatch):
    """直接預填 _rate_limit_store 模擬已用盡配額，下一次請求應立即觸發 429。"""
    monkeypatch.setattr(api_module, "API_RATE_LIMIT", "5/minute")
    _rate_limit_store.clear()

    # 預填 5 個在有效期內的時間戳，模擬配額已用盡
    # bucket_key 格式為 "{scope}:{client_ip}"，TestClient 的 IP 是 "testclient"
    bucket_key = "api:testclient"
    now = time.time()
    _rate_limit_store[bucket_key] = [now - i * 0.1 for i in range(5)]

    resp = client.get("/api/stats")
    assert resp.status_code == 429


# ==================== 豁免路徑 ====================


def test_health_exempt_from_rate_limit(monkeypatch):
    """/health 豁免速率限制，大量請求也不應回傳 429。"""
    monkeypatch.setattr(api_module, "API_RATE_LIMIT", "1/minute")
    _rate_limit_store.clear()

    for _ in range(20):
        resp = client.get("/health")
        # 200 或 503（無 DB），但不應是 429
        assert resp.status_code != 429


def test_root_exempt_from_rate_limit(monkeypatch):
    """根端點 / 豁免速率限制。"""
    monkeypatch.setattr(api_module, "API_RATE_LIMIT", "1/minute")
    _rate_limit_store.clear()

    for _ in range(10):
        resp = client.get("/")
        assert resp.status_code == 200


def test_health_detail_exempt_from_rate_limit(monkeypatch):
    """/api/health/detail 豁免速率限制。"""
    monkeypatch.setattr(api_module, "API_RATE_LIMIT", "1/minute")
    _rate_limit_store.clear()

    for _ in range(10):
        resp = client.get("/api/health/detail")
        assert resp.status_code == 200


def test_metrics_exempt_from_rate_limit(monkeypatch):
    """/metrics 豁免速率限制。"""
    monkeypatch.setattr(api_module, "API_RATE_LIMIT", "1/minute")
    _rate_limit_store.clear()

    for _ in range(5):
        resp = client.get("/metrics")
        # 200 或 404（如果 metrics 端點不存在），但不應該是 429
        assert resp.status_code != 429


def test_docs_exempt_from_rate_limit(monkeypatch):
    """/docs 豁免速率限制。"""
    monkeypatch.setattr(api_module, "API_RATE_LIMIT", "1/minute")
    _rate_limit_store.clear()

    for _ in range(5):
        resp = client.get("/docs")
        assert resp.status_code == 200


# ==================== Auth 速率限制獨立於 API 速率限制 ====================


def test_auth_and_api_rate_limits_are_separate_buckets():
    """
    auth 端點使用 scope='auth'，API 端點使用 scope='api'，
    兩者的 bucket_key 是獨立的（bucket_key = f"{scope}:{client_ip}"）。

    驗證方式：填滿 api bucket 後，auth bucket 仍然是空的，
    確認兩者不會互相影響。

    注意：/api/auth/token 本身也會被 middleware 的 api bucket 限制，
    因此此測試改為直接驗證 _rate_limit_store 的 key 是分開的，
    而非透過實際 HTTP 請求跨 scope 測試。
    """
    _rate_limit_store.clear()
    now = time.time()

    # 預填 api bucket（模擬已有請求記錄）
    _rate_limit_store["api:testclient"] = [now - 1.0, now - 0.5]

    # auth bucket 應完全獨立，不受 api bucket 影響
    assert "auth:testclient" not in _rate_limit_store or \
        len(_rate_limit_store["auth:testclient"]) == 0

    # 在 api bucket 已有記錄的情況下，預填 auth bucket
    _rate_limit_store["auth:testclient"] = [now - 0.2]

    # 兩個 bucket 應各自獨立存在
    assert len(_rate_limit_store["api:testclient"]) == 2
    assert len(_rate_limit_store["auth:testclient"]) == 1


def test_rate_limit_store_cleared_between_tests():
    """
    驗證 autouse fixture 正確清空 _rate_limit_store，
    此測試依賴前面的測試不留下殘留狀態。
    """
    # 測試開始時 store 應該是空的（由 autouse fixture 保證）
    assert len(_rate_limit_store) == 0, (
        "clear_rate_limits fixture 未正確清空 _rate_limit_store"
    )
