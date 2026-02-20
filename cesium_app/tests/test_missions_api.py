"""TDD tests for V5 mission-driven demo API.

V5 白皮书引入 Missions（任务驱动）作为演示主线：
- 农业安全：河南周口
- 生态红线：毛乌素沙地
- 城市治理：粤港澳大湾区

这些测试固定 `/api/missions` 的返回结构，确保前后端契约稳定。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    backend_path = Path(__file__).parent.parent / "backend"
    sys.path.insert(0, str(backend_path))

    from main import app  # noqa: WPS433 (test import)

    return TestClient(app)


class TestMissionsEndpoint:
    def test_missions_endpoint_exists(self, client: TestClient):
        resp = client.get("/api/missions")
        assert resp.status_code == 200

    def test_missions_schema_and_references_are_valid(self, client: TestClient):
        # Load reference sets
        modes = client.get("/api/modes").json()
        locations = client.get("/api/locations").json()

        resp = client.get("/api/missions")
        assert resp.status_code == 200
        data = resp.json()

        assert isinstance(data, list)
        assert len(data) >= 3

        required_keys = {
            "id",
            "name",
            "api_mode",
            "location",
            "title",
            "narrative",
            "formula",
            "camera",
        }

        for m in data:
            assert isinstance(m, dict)
            assert required_keys.issubset(m.keys())

            assert isinstance(m["id"], str) and m["id"]
            assert isinstance(m["name"], str) and m["name"]
            assert isinstance(m["api_mode"], str) and m["api_mode"]
            assert isinstance(m["location"], str) and m["location"]

            assert m["api_mode"] in modes, f"Unknown api_mode: {m['api_mode']}"
            assert m["location"] in locations, f"Unknown location: {m['location']}"

            cam = m["camera"]
            assert isinstance(cam, dict)
            for k in ("lat", "lon", "height", "duration_s"):
                assert k in cam
            assert isinstance(cam["lat"], (int, float))
            assert isinstance(cam["lon"], (int, float))
            assert isinstance(cam["height"], (int, float))
            assert isinstance(cam["duration_s"], (int, float))

    def test_missions_have_stable_order(self, client: TestClient):
        resp = client.get("/api/missions")
        ids = [m["id"] for m in resp.json()]

        # V5 flagship order: agri -> eco -> urban
        assert ids[:3] == ["agri_zhoukou", "eco_maowusu", "urban_gba"]
