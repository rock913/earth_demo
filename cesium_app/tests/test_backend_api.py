"""
TDD Tests for FastAPI Backend
测试 REST API 端点
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, Mock, patch
import re
import httpx


@pytest.fixture
def test_client():
    """创建测试客户端"""
    # 添加 backend 目录到 Python 路径
    import sys
    from pathlib import Path
    backend_path = Path(__file__).parent.parent / "backend"
    sys.path.insert(0, str(backend_path))
    
    # 延迟导入以避免 GEE 初始化
    from main import app
    import main as main_module
    # 模拟 GEE 已初始化
    main_module.gee_initialized = True
    return TestClient(app)


class TestHealthEndpoint:
    """测试健康检查端点"""
    
    def test_health_check(self, test_client):
        """测试 /health 端点"""
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "gee_initialized" in data


class TestLocationsEndpoint:
    """测试地点列表端点"""
    
    def test_get_locations(self, test_client):
        """测试获取所有地点"""
        response = test_client.get("/api/locations")
        assert response.status_code == 200
        data = response.json()
        
        # API 返回字典格式: {"shanghai": {...}, "xiongan": {...}}
        assert isinstance(data, dict)
        # 验证某个位置存在
        assert "shanghai" in data
        shanghai = data["shanghai"]
        assert "coords" in shanghai
        assert len(shanghai["coords"]) == 3
    
    def test_get_specific_location(self, test_client):
        """测试获取特定地点"""
        response = test_client.get("/api/locations/xiongan")
        assert response.status_code == 200
        data = response.json()
        
        assert data["code"] == "xiongan"
        assert "雄安" in data["name"]
    
    def test_get_nonexistent_location(self, test_client):
        """测试获取不存在的地点"""
        response = test_client.get("/api/locations/invalid_city")
        assert response.status_code == 404


class TestModesEndpoint:
    """测试 AI 模式列表端点"""
    
    def test_get_modes(self, test_client):
        """测试获取所有 AI 模式"""
        response = test_client.get("/api/modes")
        assert response.status_code == 200
        data = response.json()
        
        # API 返回字典格式: {"dna": "地表 DNA", "change": "..."}
        assert isinstance(data, dict)
        assert len(data) == 4  # 4 种模式
        # 验证 DNA 和 change 模式存在
        assert "dna" in data
        assert "change" in data


class TestLayerEndpoint:
    """测试图层获取端点"""
    
    @patch('main.ee.Geometry.Point')
    @patch('main.smart_load')
    @patch('main.get_tile_url')
    def test_get_layer_success(self, mock_get_tile, mock_smart_load, mock_point, test_client):
        """测试成功获取图层"""
        # 模拟 GEE Geometry
        mock_viewport = Mock()
        mock_point.return_value.buffer.return_value = mock_viewport
        
        # 模拟返回值
        mock_image = Mock()
        mock_vis = {'min': 0, 'max': 1}
        mock_smart_load.return_value = (
            mock_image,  # layer
            mock_vis,    # vis_params
            "cached",    # status_html
            True,        # is_cached
            "asset_id",  # asset_id
            mock_image   # raw_img
        )
        mock_get_tile.return_value = "https://earthengine.googleapis.com/v1/{z}/{x}/{y}"
        
        response = test_client.get("/api/layers?mode=change&location=shanghai")
        assert response.status_code == 200
        
        data = response.json()
        assert "tile_url" in data
        assert re.search(r"/api/tiles/[0-9a-f]{24}/\{z\}/\{x\}/(\{y\}|\{reverseY\})$", data["tile_url"])
        assert "is_cached" in data
        assert data["is_cached"] is True
        assert "asset_id" in data
        assert "vis_params" in data
    
    def test_get_layer_missing_params(self, test_client):
        """测试缺少必需参数"""
        response = test_client.get("/api/layers?mode=change")
        assert response.status_code == 422  # Validation error
    
    @patch('main.smart_load')
    def test_get_layer_invalid_location(self, mock_smart_load, test_client):
        """测试无效地点"""
        response = test_client.get("/api/layers?mode=change&location=invalid")
        assert response.status_code == 400
        assert "Invalid location" in response.json()["detail"]
    
    @patch('main.ee.Geometry.Point')
    @patch('main.smart_load')
    @patch('main.get_tile_url')
    def test_get_layer_cache_miss(self, mock_get_tile, mock_smart_load, mock_point, test_client):
        """测试缓存未命中场景"""
        mock_viewport = Mock()
        mock_point.return_value.buffer.return_value = mock_viewport
        
        mock_image = Mock()
        mock_smart_load.return_value = (
            mock_image, {'min': 0, 'max': 1}, "live", False, "asset_id", mock_image
        )
        mock_get_tile.return_value = "https://earthengine.googleapis.com/v1/{z}/{x}/{y}"
        
        response = test_client.get("/api/layers?mode=dna&location=beijing")
        assert response.status_code == 200
        
        data = response.json()
        assert re.search(r"/api/tiles/[0-9a-f]{24}/\{z\}/\{x\}/(\{y\}|\{reverseY\})$", data["tile_url"])
        assert data["is_cached"] is False
        assert "live" in data["status"].lower() or "实时" in data["status"]


class TestTileProxyEndpoint:
    """测试同源瓦片代理端点"""

    @patch("main.ee.Geometry.Point")
    @patch("main.smart_load")
    @patch("main.get_tile_url")
    def test_tile_proxy_returns_image_and_cors(self, mock_get_tile, mock_smart_load, mock_point, test_client):
        mock_viewport = Mock()
        mock_point.return_value.buffer.return_value = mock_viewport

        mock_image = Mock()
        mock_smart_load.return_value = (
            mock_image,
            {"min": 0, "max": 1},
            "cached",
            True,
            "asset_id",
            mock_image,
        )
        mock_get_tile.return_value = "https://earthengine.googleapis.com/v1/tiles/{z}/{x}/{y}"

        # 先调用 /api/layers 注册 tile_id
        layer_resp = test_client.get("/api/layers?mode=dna&location=xiongan")
        assert layer_resp.status_code == 200
        tile_url = layer_resp.json()["tile_url"]
        m = re.search(r"/api/tiles/(?P<tile_id>[0-9a-f]{24})/\{z\}/\{x\}/(\{y\}|\{reverseY\})$", tile_url)
        assert m
        tile_id = m.group("tile_id")

        upstream_resp = Mock()
        upstream_resp.status_code = 200
        upstream_resp.headers = {
            "Content-Type": "image/png",
            "Cache-Control": "private, max-age=3600",
        }
        upstream_resp.content = b"\x89PNG\r\n\x1a\n..."
        upstream_resp.raise_for_status = Mock()

        with patch("main.http_client", new=Mock(get=AsyncMock(return_value=upstream_resp))):
            tile_resp = test_client.get(
                f"/api/tiles/{tile_id}/7/105/48",
                headers={"Origin": "http://127.0.0.1:8502"},
            )

        assert tile_resp.status_code == 200
        assert tile_resp.headers.get("content-type", "").startswith("image/png")
        assert tile_resp.content.startswith(b"\x89PNG")

        # CORS: allow_origins="*" 时通常返回 "*"
        assert tile_resp.headers.get("access-control-allow-origin") in ("*", "http://127.0.0.1:8502")

    @patch("main.ee.Geometry.Point")
    @patch("main.smart_load")
    @patch("main.get_tile_url")
    def test_tile_proxy_upstream_400_returns_blank_png(self, mock_get_tile, mock_smart_load, mock_point, test_client):
        """上游 400/404 时后端应返回可用 PNG(200)，避免 Cesium 蓝底和错误风暴。"""
        mock_viewport = Mock()
        mock_point.return_value.buffer.return_value = mock_viewport

        mock_image = Mock()
        mock_smart_load.return_value = (
            mock_image,
            {"min": 0, "max": 1},
            "cached",
            True,
            "asset_id",
            mock_image,
        )
        mock_get_tile.return_value = "https://earthengine.googleapis.com/v1/tiles/{z}/{x}/{y}"

        layer_resp = test_client.get("/api/layers?mode=dna&location=xiongan")
        assert layer_resp.status_code == 200
        tile_url = layer_resp.json()["tile_url"]
        m = re.search(r"/api/tiles/(?P<tile_id>[0-9a-f]{24})/\{z\}/\{x\}/(\{y\}|\{reverseY\})$", tile_url)
        assert m
        tile_id = m.group("tile_id")

        upstream_resp = httpx.Response(
            status_code=400,
            headers={"Content-Type": "application/json"},
            content=b"{\"error\":\"Bad Request\"}",
        )

        with patch("main.http_client", new=Mock(get=AsyncMock(return_value=upstream_resp))):
            tile_resp = test_client.get(f"/api/tiles/{tile_id}/0/0/0")

        assert tile_resp.status_code == 200
        assert tile_resp.headers.get("content-type", "").startswith("image/png")
        assert tile_resp.content.startswith(b"\x89PNG")

        # Ensure the fallback tile is 256x256 (Cesium imagery tiles expect this)
        # PNG IHDR stores width/height as big-endian uint32 at bytes 16..23
        width = int.from_bytes(tile_resp.content[16:20], "big")
        height = int.from_bytes(tile_resp.content[20:24], "big")
        assert (width, height) == (256, 256)


class TestExportEndpoint:
    """测试缓存导出端点"""
    
    @patch('main.ee.Geometry.Point')
    @patch('main.trigger_export_task')
    @patch('main.get_layer_logic')
    def test_export_cache_success(self, mock_get_layer, mock_trigger, mock_point, test_client):
        """测试成功触发导出"""
        mock_viewport = Mock()
        mock_point.return_value.buffer.return_value = mock_viewport
        
        mock_image = Mock()
        mock_get_layer.return_value = (mock_image, {'min': 0}, 'change')
        mock_trigger.return_value = "TASK_12345"
        
        payload = {
            "mode": "change",  # ✅ 使用mode ID而不是完整名称
            "location": "xiongan"
        }
        response = test_client.post("/api/cache/export", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["task_id"] == "TASK_12345"
        assert data["status"] == "submitted"
    
    def test_export_cache_missing_fields(self, test_client):
        """测试缺少必需字段"""
        payload = {"mode": "变化雷达"}
        response = test_client.post("/api/cache/export", json=payload)
        assert response.status_code == 422


class TestCORSHeaders:
    """测试 CORS 配置"""
    
    def test_cors_headers_present(self, test_client):
        """测试 CORS 头是否正确设置"""
        response = test_client.options(
            "/api/locations",
            headers={
                "Origin": "http://localhost:8502",
                "Access-Control-Request-Method": "GET"
            }
        )
        # FastAPI 的 CORS 中间件应该返回正确的头
        assert response.status_code in [200, 204]


class TestErrorHandling:
    """测试错误处理"""
    
    @patch('main.ee.Geometry.Point')
    @patch('main.smart_load')
    def test_gee_error_handling(self, mock_smart_load, mock_point, test_client):
        """测试 GEE 错误处理"""
        mock_viewport = Mock()
        mock_point.return_value.buffer.return_value = mock_viewport
        mock_smart_load.side_effect = Exception("GEE computation failed")
        
        response = test_client.get("/api/layers?mode=change&location=shanghai")
        assert response.status_code == 500
        assert "error" in response.json()["detail"]
