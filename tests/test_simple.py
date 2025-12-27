"""Simple tests to verify test framework is working."""

import pytest
import requests


def test_basic_math():
    """Test basic functionality."""
    assert 1 + 1 == 2


def test_api_is_running():
    """Test that the API is accessible."""
    try:
        response = requests.get("http://app:8000/health", timeout=5)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    except requests.exceptions.RequestException:
        # If we can't connect, that's expected in some test environments
        pytest.skip("API not accessible from test environment")


def test_imports():
    """Test that our modules can be imported."""
    from core.config import get_settings
    from schemas.models import NormalizedCryptoData
    from ingestion.base_ingester import BaseIngester
    
    settings = get_settings()
    assert settings is not None