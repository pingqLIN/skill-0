"""Shared test fixtures for Skill-0 API tests."""

import os
import sys

import pytest

# Ensure project root is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Set test environment variables BEFORE importing app
# api/main.py calls enforce_production_security_configuration() at module level,
# so these must be set before any import of api.main.
os.environ["SKILL0_ENV"] = "development"
os.environ["JWT_SECRET_KEY"] = "test-secret-key"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["API_USERNAME"] = "testadmin"
os.environ["API_PASSWORD"] = "testpass123"
os.environ["API_RATE_LIMIT"] = "1000/minute"
os.environ["AUTH_RATE_LIMIT"] = "100/minute"
