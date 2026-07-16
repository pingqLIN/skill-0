"""Shared test fixtures for Skill-0 API tests."""

import json
import os
import sys
from pathlib import Path

import pytest

# Ensure project root is on sys.path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Set test environment variables BEFORE importing app
# api/main.py calls enforce_production_security_configuration() at module level,
# so these must be set before any import of api.main.
os.environ["SKILL0_ENV"] = "development"
os.environ["SKILL0_DEVICE"] = "cpu"
os.environ["JWT_SECRET_KEY"] = "skill0-test-jwt-secret-key-0123456789"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["API_USERNAME"] = "testadmin"
os.environ["API_PASSWORD"] = "testpass123"
os.environ["API_RATE_LIMIT"] = "1000/minute"
os.environ["AUTH_RATE_LIMIT"] = "100/minute"
os.environ["SKILL0_RUNTIME_BINDING_KEY"] = (
    "skill0-test-runtime-binding-key-0123456789"
)
os.environ["SKILL0_RUNTIME_DECISION_ACTORS"] = "testadmin,reviewer-1"


@pytest.fixture
def root() -> Path:
    return ROOT


@pytest.fixture
def read_json():
    def _read(relative: str):
        return json.loads((ROOT / relative).read_text(encoding="utf-8"))

    return _read
