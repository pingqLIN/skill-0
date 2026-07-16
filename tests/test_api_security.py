"""Unit tests for API security and rate-limit configuration helpers."""

import sqlite3
from unittest.mock import patch
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import api.main as api_module

from api.main import (
    _is_local_origin,
    _parse_rate_limit,
    _is_rate_limit_exempt_path,
    _extract_client_ip,
    find_production_security_issues,
    generate_request_id,
    is_production_env,
    validate_login_credentials,
)


def test_is_production_env_variants():
    assert is_production_env('production') is True
    assert is_production_env('prod') is True
    assert is_production_env('PRODUCTION') is True
    assert is_production_env('development') is False


def test_is_local_origin_detects_loopback_and_wildcard():
    assert _is_local_origin('*') is True
    assert _is_local_origin('http://localhost:3000') is True
    assert _is_local_origin('https://127.0.0.1:8443') is True
    assert _is_local_origin('https://example.com') is False


def test_generate_request_id_is_short_hex():
    request_id = generate_request_id()
    assert len(request_id) == 8
    assert int(request_id, 16) >= 0


def test_find_production_security_issues_returns_empty_for_non_production():
    issues = find_production_security_issues(
        env_value='development',
        cors_origins=['http://localhost:3000'],
        jwt_secret_key='dev-secret-change-in-production',
        default_jwt_secret_key='dev-secret-change-in-production',
        configured_username=None,
        configured_password=None,
    )
    assert issues == []


def test_find_production_security_issues_detects_expected_misconfigurations():
    issues = find_production_security_issues(
        env_value='production',
        cors_origins=['https://app.example.com', 'http://localhost:3000', '*'],
        jwt_secret_key='dev-secret-change-in-production',
        default_jwt_secret_key='dev-secret-change-in-production',
        configured_username='',
        configured_password=None,
    )

    assert len(issues) == 3
    assert any('JWT_SECRET_KEY' in issue for issue in issues)
    assert any('CORS_ORIGINS' in issue for issue in issues)
    assert any('API_USERNAME and API_PASSWORD' in issue for issue in issues)


def test_production_security_rejects_runtime_placeholders_and_accepts_independent_key():
    base = {
        "env_value": "production",
        "cors_origins": ["https://app.example.com"],
        "jwt_secret_key": "production-jwt-secret-key-0123456789",
        "default_jwt_secret_key": "dev-secret-change-in-production",
        "configured_username": "admin",
        "configured_password": "strong-password",
        "validate_runtime": True,
    }
    issues = find_production_security_issues(
        **base,
        runtime_binding_key="CHANGE_ME_TO_AN_INDEPENDENT_RUNTIME_SECRET",
        runtime_decision_actors="CHANGE_ME_APPROVER_SUBJECTS",
        runtime_hitl_ttl_seconds="0",
        runtime_journal_mode="DELETE",
    )
    assert len(issues) == 4
    assert any("SKILL0_RUNTIME_BINDING_KEY" in issue for issue in issues)
    assert any("SKILL0_RUNTIME_DECISION_ACTORS" in issue for issue in issues)
    assert any("SKILL0_RUNTIME_HITL_TTL_SECONDS" in issue for issue in issues)
    assert any("SKILL0_RUNTIME_JOURNAL_MODE" in issue for issue in issues)

    assert find_production_security_issues(
        **base,
        runtime_binding_key="independent-runtime-secret-key-9876543210",
        runtime_decision_actors="runtime-reviewer",
        runtime_hitl_ttl_seconds="86400",
        runtime_journal_mode="WAL",
    ) == []


def test_validate_login_credentials_uses_constant_time_comparisons(monkeypatch):
    monkeypatch.setenv("API_USERNAME", "admin")
    monkeypatch.setenv("API_PASSWORD", "secret")

    calls = []

    def fake_compare_digest(left: bytes, right: bytes) -> bool:
        calls.append((left, right))
        return left == right

    with patch("api.main.hmac.compare_digest", side_effect=fake_compare_digest):
        assert validate_login_credentials("wrong-admin", "wrong-secret") is False

    assert len(calls) == 2
    assert all(isinstance(left, bytes) and isinstance(right, bytes) for left, right in calls)
    assert all(len(left) == 32 and len(right) == 32 for left, right in calls)


def test_parse_rate_limit_valid_values():
    assert _parse_rate_limit('100/minute') == (100, 60)
    assert _parse_rate_limit('10/second') == (10, 1)
    assert _parse_rate_limit('5/hour') == (5, 3600)
    assert _parse_rate_limit('7') == (7, 60)


@pytest.mark.parametrize('invalid_value', ['abc', '10/day', '/minute', ''])
def test_parse_rate_limit_invalid_values(invalid_value: str):
    with pytest.raises(ValueError):
        _parse_rate_limit(invalid_value)


def test_rate_limit_exempt_paths():
    assert _is_rate_limit_exempt_path('/') is True
    assert _is_rate_limit_exempt_path('/health') is True
    assert _is_rate_limit_exempt_path('/metrics') is True
    assert _is_rate_limit_exempt_path('/docs') is True
    assert _is_rate_limit_exempt_path('/docs/oauth2-redirect') is True
    assert _is_rate_limit_exempt_path('/api/search') is False


def _make_request(peer_host: str, headers: dict[str, str] | None = None):
    return SimpleNamespace(
        client=SimpleNamespace(host=peer_host),
        headers=headers or {},
    )


def test_extract_client_ip_ignores_forwarded_headers_when_proxy_trust_disabled(monkeypatch):
    monkeypatch.setenv("SKILL0_TRUST_PROXY_HEADERS", "false")

    request = _make_request(
        "127.0.0.1",
        headers={"X-Forwarded-For": "198.51.100.8"},
    )

    assert _extract_client_ip(request) == "127.0.0.1"


def test_extract_client_ip_uses_forwarded_for_when_trusted_proxy_enabled(monkeypatch):
    monkeypatch.setenv("SKILL0_TRUST_PROXY_HEADERS", "true")
    monkeypatch.setenv("SKILL0_TRUSTED_PROXY_CIDRS", "127.0.0.1/32")

    request = _make_request(
        "127.0.0.1",
        headers={"X-Forwarded-For": "198.51.100.8, 203.0.113.1"},
    )

    assert _extract_client_ip(request) == "198.51.100.8"


def test_extract_client_ip_prefers_cf_connecting_ip(monkeypatch):
    monkeypatch.setenv("SKILL0_TRUST_PROXY_HEADERS", "true")
    monkeypatch.setenv("SKILL0_TRUSTED_PROXY_CIDRS", "127.0.0.1/32")

    request = _make_request(
        "127.0.0.1",
        headers={
            "CF-Connecting-IP": "203.0.113.99",
            "X-Forwarded-For": "198.51.100.8",
        },
    )

    assert _extract_client_ip(request) == "203.0.113.99"


def test_extract_client_ip_falls_back_to_peer_on_invalid_forwarded_value(monkeypatch):
    monkeypatch.setenv("SKILL0_TRUST_PROXY_HEADERS", "true")
    monkeypatch.setenv("SKILL0_TRUSTED_PROXY_CIDRS", "127.0.0.1/32")

    request = _make_request(
        "127.0.0.1",
        headers={"X-Forwarded-For": "not-an-ip"},
    )

    assert _extract_client_ip(request) == "127.0.0.1"


def test_health_endpoint_does_not_initialize_search_engine(monkeypatch, tmp_path):
    db_path = tmp_path / "skills.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE skills (id INTEGER PRIMARY KEY, name TEXT NOT NULL)")
        conn.execute("INSERT INTO skills (name) VALUES ('fixture-skill')")
        conn.commit()

    monkeypatch.setattr(api_module, "DB_PATH", str(db_path))

    def _unexpected_engine_call():
        raise AssertionError("/health 不應初始化 search engine")

    monkeypatch.setattr(api_module, "get_search_engine", _unexpected_engine_call)

    client = TestClient(api_module.app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["total_skills"] == 1
