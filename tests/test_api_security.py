"""Unit tests for API security and rate-limit configuration helpers."""

from types import SimpleNamespace

import pytest

from api.main import (
    _is_local_origin,
    _parse_rate_limit,
    _is_rate_limit_exempt_path,
    _extract_client_ip,
    find_production_security_issues,
    generate_request_id,
    is_production_env,
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
