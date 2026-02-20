"""
Pytest fixtures for Cesium app testing
"""
import pytest
import os


@pytest.fixture
def mock_gee_user_path():
    """Mock GEE user path for testing"""
    return "users/test_user/aef_demo"


@pytest.fixture
def mock_locations():
    """Mock location data"""
    return {
        "shanghai": {"coords": [31.2304, 121.5000, 14], "name": "上海 · 陆家嘴"},
        "xiongan": {"coords": [39.0500, 115.9800, 12], "name": "河北 · 雄安"},
        "beijing": {"coords": [39.9042, 116.7000, 13], "name": "北京 · 通州"},
    }


@pytest.fixture
def mock_modes():
    """Mock AI mode data"""
    return {
        "dna": "地表 DNA (语义视图)",
        "change": "变化雷达 (敏捷治理)",
        "intensity": "建设强度 (宏观管控)",
        "eco": "生态韧性 (绿色底线)",
    }


@pytest.fixture(autouse=True)
def set_test_env():
    """Set test environment variables"""
    os.environ["GEE_USER_PATH"] = "users/test_user/aef_demo"
    os.environ["TESTING"] = "1"
    yield
    if "TESTING" in os.environ:
        del os.environ["TESTING"]
