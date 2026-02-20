"""
TDD Unit Tests for GEE Service Layer
测试先行：定义期望的 GEE 服务行为
"""
import pytest
from unittest.mock import Mock, patch, MagicMock


class TestLayerLogic:
    """测试图层计算逻辑"""
    
    def test_get_layer_logic_dna_mode(self, mock_gee_user_path):
        """测试地表 DNA 模式的计算逻辑"""
        from cesium_app.backend.gee_service import get_layer_logic
        
        # 模拟输入
        mode = "地表 DNA (语义视图)"
        mock_region = Mock()
        
        with patch('cesium_app.backend.gee_service.ee') as mock_ee:
            # 模拟 GEE API
            mock_collection = Mock()
            mock_mosaic = Mock()
            mock_ee.ImageCollection.return_value = mock_collection
            mock_collection.filterBounds.return_value.filterDate.return_value.mosaic.return_value = mock_mosaic
            mock_mosaic.select.return_value = mock_mosaic
            mock_mosaic.clip.return_value = mock_mosaic
            
            # 执行
            result_image, vis_params, suffix = get_layer_logic(mode, mock_region)
            
            # 验证
            assert suffix == "dna"
            assert vis_params['min'] == -0.1
            assert vis_params['max'] == 0.1
            assert vis_params['gamma'] == 1.6
            # DNA 模式应该使用 A00, A01, A02 波段
            mock_mosaic.select.assert_called_once_with(['A00', 'A01', 'A02'])
    
    def test_get_layer_logic_change_mode(self):
        """测试变化雷达模式的计算逻辑"""
        from cesium_app.backend.gee_service import get_layer_logic
        
        mode = "变化雷达 (敏捷治理)"
        mock_region = Mock()
        
        with patch('cesium_app.backend.gee_service.ee') as mock_ee:
            mock_collection = Mock()
            mock_image_19 = Mock()
            mock_image_24 = Mock()
            mock_ee.ImageCollection.return_value = mock_collection
            
            # 模拟两年数据（filterBounds().filterDate().mosaic()）
            def filter_date_side_effect(start, end):
                mock_filter = Mock()
                if '2019' in start:
                    mock_filter.mosaic.return_value = mock_image_19
                else:
                    mock_filter.mosaic.return_value = mock_image_24
                return mock_filter

            # 2019 分支：emb_col.filterBounds(region).filterDate(...).mosaic()
            mock_collection.filterBounds.return_value.filterDate.side_effect = filter_date_side_effect
            
            # 模拟距离计算链
            mock_image_19.subtract.return_value.pow.return_value.reduce.return_value.sqrt.return_value = mock_image_24
            mock_image_24.updateMask.return_value = mock_image_24
            mock_image_24.gt.return_value = Mock()
            mock_image_24.clip.return_value = mock_image_24
            
            result_image, vis_params, suffix = get_layer_logic(mode, mock_region)
            
            assert suffix == "change"
            assert 'palette' in vis_params
            assert 'FF0000' in vis_params['palette']
    
    def test_get_layer_logic_intensity_mode(self):
        """测试建设强度模式"""
        from cesium_app.backend.gee_service import get_layer_logic
        
        mode = "建设强度 (宏观管控)"
        mock_region = Mock()
        
        with patch('cesium_app.backend.gee_service.ee') as mock_ee:
            mock_collection = Mock()
            mock_mosaic = Mock()
            mock_ee.ImageCollection.return_value = mock_collection
            mock_collection.filterBounds.return_value.filterDate.return_value.mosaic.return_value = mock_mosaic
            mock_mosaic.select.return_value.rename.return_value.unitScale.return_value = mock_mosaic
            mock_mosaic.updateMask.return_value = mock_mosaic
            mock_mosaic.gt.return_value = Mock()
            mock_mosaic.clip.return_value = mock_mosaic
            
            result_image, vis_params, suffix = get_layer_logic(mode, mock_region)
            
            assert suffix == "intensity"
            assert vis_params['min'] == 0.4
    
    def test_get_layer_logic_eco_mode(self):
        """测试生态韧性模式"""
        from cesium_app.backend.gee_service import get_layer_logic
        
        mode = "生态韧性 (绿色底线)"
        mock_region = Mock()
        
        with patch('cesium_app.backend.gee_service.ee') as mock_ee:
            mock_collection = Mock()
            mock_mosaic = Mock()
            mock_ee.ImageCollection.return_value = mock_collection
            mock_collection.filterBounds.return_value.filterDate.return_value.mosaic.return_value = mock_mosaic
            mock_mosaic.select.return_value.rename.return_value.multiply.return_value = mock_mosaic
            mock_mosaic.updateMask.return_value = mock_mosaic
            mock_mosaic.gt.return_value = Mock()
            mock_mosaic.clip.return_value = mock_mosaic
            
            result_image, vis_params, suffix = get_layer_logic(mode, mock_region)
            
            assert suffix == "eco"
            assert '00FF00' in vis_params['palette']


class TestSmartLoad:
    """测试智能缓存加载逻辑"""
    
    def test_smart_load_cache_hit(self, mock_gee_user_path):
        """测试缓存命中场景"""
        from cesium_app.backend.gee_service import smart_load
        
        mode = "变化雷达 (敏捷治理)"
        mock_region = Mock()
        loc_code = "shanghai"
        
        with patch('cesium_app.backend.gee_service.ee') as mock_ee:
            # 模拟 Asset 存在
            mock_ee.data.getAsset.return_value = {"type": "Image"}
            mock_ee.Image.return_value = Mock()
            
            # 模拟图层计算
            with patch('cesium_app.backend.gee_service.get_layer_logic') as mock_get_layer:
                mock_img = Mock()
                mock_get_layer.return_value = (mock_img, {'min': 0}, 'change')
                
                layer, vis, status, is_cached, asset_id, raw_img = smart_load(
                    mode, mock_region, loc_code, mock_gee_user_path
                )
                
                # 验证缓存命中
                assert is_cached is True
                assert "极速缓存" in status or "cached" in status.lower()
                assert asset_id == f"{mock_gee_user_path}/shanghai_change"
    
    def test_smart_load_cache_miss(self, mock_gee_user_path):
        """测试缓存未命中场景 - 实时计算"""
        from cesium_app.backend.gee_service import smart_load
        
        mode = "地表 DNA (语义视图)"
        mock_region = Mock()
        loc_code = "xiongan"
        
        with patch('cesium_app.backend.gee_service.ee') as mock_ee:
            # 模拟 Asset 不存在
            mock_ee.data.getAsset.side_effect = Exception("Asset not found")
            
            with patch('cesium_app.backend.gee_service.get_layer_logic') as mock_get_layer:
                mock_img = Mock()
                mock_get_layer.return_value = (mock_img, {'min': -0.1}, 'dna')
                
                layer, vis, status, is_cached, asset_id, raw_img = smart_load(
                    mode, mock_region, loc_code, mock_gee_user_path
                )
                
                # 验证实时计算
                assert is_cached is False
                assert "实时计算" in status or "live" in status.lower()
                assert layer == mock_img
    
    def test_asset_id_generation(self, mock_gee_user_path):
        """测试 Asset ID 生成逻辑"""
        from cesium_app.backend.gee_service import generate_asset_id
        
        loc_code = "beijing"
        suffix = "intensity"
        
        asset_id = generate_asset_id(loc_code, suffix, mock_gee_user_path)
        
        assert asset_id == f"{mock_gee_user_path}/beijing_intensity"
        assert asset_id.startswith("users/test_user/aef_demo/")


class TestTileURLGeneration:
    """测试 Tile URL 生成"""
    
    def test_get_tile_url_success(self):
        """测试成功获取 Tile URL"""
        from cesium_app.backend.gee_service import get_tile_url
        
        mock_image = Mock()
        vis_params = {'min': 0, 'max': 1, 'palette': ['000000', 'FFFFFF']}
        
        with patch('cesium_app.backend.gee_service.ee') as mock_ee:
            mock_map_id = {
                'tile_fetcher': Mock(url_format='https://earthengine.googleapis.com/v1/{z}/{x}/{y}')
            }
            mock_image.getMapId.return_value = mock_map_id
            
            url = get_tile_url(mock_image, vis_params)
            
            assert 'earthengine.googleapis.com' in url
            assert '{z}' in url
            assert '{x}' in url
            assert '{y}' in url
    
    def test_get_tile_url_with_token(self):
        """测试带 Token 的 URL 生成"""
        from cesium_app.backend.gee_service import get_tile_url
        
        mock_image = Mock()
        vis_params = {'min': 0, 'max': 1}
        
        with patch('cesium_app.backend.gee_service.ee') as mock_ee:
            mock_map_id = {
                'tile_fetcher': Mock(url_format='https://earthengine.googleapis.com/v1/{z}/{x}/{y}?token=abc123')
            }
            mock_image.getMapId.return_value = mock_map_id
            
            url = get_tile_url(mock_image, vis_params)
            
            # Token 应该被包含在 URL 中
            assert 'token=' in url or url.endswith('abc123')


class TestExportTask:
    """测试缓存导出任务"""
    
    def test_trigger_export_task(self, mock_gee_user_path):
        """测试触发导出任务"""
        from cesium_app.backend.gee_service import trigger_export_task
        
        mock_image = Mock()
        description = "Cache_shanghai_change"
        asset_id = f"{mock_gee_user_path}/shanghai_change"
        mock_region = Mock()
        
        with patch('cesium_app.backend.gee_service.ee') as mock_ee:
            mock_task = Mock()
            mock_task.id = "TASK_12345"
            mock_ee.batch.Export.image.toAsset.return_value = mock_task
            
            task_id = trigger_export_task(mock_image, description, asset_id, mock_region)
            
            assert task_id == "TASK_12345"
            mock_task.start.assert_called_once()
    
    def test_export_task_parameters(self, mock_gee_user_path):
        """测试导出任务参数正确性"""
        from cesium_app.backend.gee_service import trigger_export_task
        
        mock_image = Mock()
        description = "Test_Export"
        asset_id = "users/test/asset"
        mock_region = Mock()
        
        with patch('cesium_app.backend.gee_service.ee') as mock_ee:
            mock_task = Mock()
            mock_task.id = "TASK_001"
            mock_export = mock_ee.batch.Export.image.toAsset
            mock_export.return_value = mock_task
            
            trigger_export_task(mock_image, description, asset_id, mock_region)
            
            # 验证调用参数
            call_kwargs = mock_export.call_args[1]
            assert call_kwargs['image'] == mock_image
            assert call_kwargs['description'] == description
            assert call_kwargs['assetId'] == asset_id
            assert call_kwargs['scale'] == 10
            assert call_kwargs['maxPixels'] >= 1e9
