"""
Pytest configuration for Matomo API tests.

Configure test parameters here or via environment variables.
"""

import os
import pytest


# Test configuration - override via environment variables if needed
TEST_SITE_ID = int(os.environ.get("MATOMO_TEST_SITE_ID", "117"))
TEST_PERIOD = os.environ.get("MATOMO_TEST_PERIOD", "month")
TEST_DATE = os.environ.get("MATOMO_TEST_DATE", "2025-12-01")
TEST_DIMENSION_ID = int(os.environ.get("MATOMO_TEST_DIMENSION_ID", "1"))
TEST_SEGMENT = os.environ.get("MATOMO_TEST_SEGMENT", "pageUrl=@/gps/")


@pytest.fixture
def site_id():
    """Test site ID."""
    return TEST_SITE_ID


@pytest.fixture
def period():
    """Test period."""
    return TEST_PERIOD


@pytest.fixture
def date():
    """Test date."""
    return TEST_DATE


@pytest.fixture
def dimension_id():
    """Test dimension ID."""
    return TEST_DIMENSION_ID


@pytest.fixture
def segment():
    """Test segment filter."""
    return TEST_SEGMENT
