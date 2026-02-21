"""
pytest configuration for Banking Data Assistant tests
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture(scope="session")
def test_database():
    """Setup test database"""
    from backend.db import init_database
    init_database()
    yield
    # Cleanup after tests if needed


@pytest.fixture
def sample_queries():
    """Provide sample test queries"""
    return {
        "simple": "Show all customers",
        "filtered": "Show transactions above 1000",
        "join": "Show customers with accounts",
        "aggregation": "What is total transaction amount",
        "malicious": "DROP TABLE customers",
        "injection": "SELECT * FROM customers; DELETE FROM accounts;",
    }


@pytest.fixture
def expected_outputs():
    """Expected output structure"""
    return {
        "ai_output": {
            "validated_sql": str,
            "summary": str,
            "chart_suggestion": str,
            "error_message": (str, type(None))
        },
        "backend_success": {
            "success": bool,
            "data": list,
            "row_count": int,
            "execution_time_ms": (float, type(None))
        },
        "backend_error": {
            "success": bool,
            "error": str,
            "row_count": int
        }
    }


def pytest_configure(config):
    """Configure pytest"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "security: marks tests as security tests"
    )
    config.addinivalue_line(
        "markers", "ai: marks tests as AI agent tests"
    )
