"""
Pytest Configuration
====================

Shared fixtures and configuration for all tests.
"""

import pytest
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set test environment variables
os.environ.setdefault("API_SECRET", "test-api-secret")
os.environ.setdefault("ADMIN_PASSWORD", "test-admin-password")


@pytest.fixture(scope="session")
def openai_available():
    """Check if OpenAI API key is available."""
    return bool(os.environ.get("OPENAI_API_KEY"))


@pytest.fixture(scope="session")
def test_workspace_id():
    """Generate a unique test workspace ID."""
    import uuid
    return f"test_workspace_{uuid.uuid4().hex[:8]}"


def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (require API keys)"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running"
    )


def pytest_collection_modifyitems(config, items):
    """Skip integration tests if API keys are not available."""
    if not os.environ.get("OPENAI_API_KEY"):
        skip_integration = pytest.mark.skip(
            reason="OPENAI_API_KEY not available"
        )
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)
