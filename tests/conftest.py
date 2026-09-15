"""
Pytest configuration and fixtures for test suite.

Provides fixtures for cache management and test isolation.
"""
import pytest
from api.cache import clear_response_cache


@pytest.fixture(autouse=True)
def clear_cache_before_each_test():
    """
    Automatically clear response cache before each test to ensure test isolation.
    
    This prevents cache state from one test affecting another test's results.
    """
    clear_response_cache()
    yield
    # Optional: Clear after test as well for extra safety
    clear_response_cache()
