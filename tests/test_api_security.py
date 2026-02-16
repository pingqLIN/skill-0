"""Unit tests for API security and rate-limit configuration helpers."""

import pytest

from api.main import (
    _is_local_origin,
    _parse_rate_limit,
    _is_rate_limit_exempt_path,
    find_production_security_issues,
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
