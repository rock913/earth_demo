"""
测试所有 AI 监测模式的 GEE 计算逻辑
基于 TDD 方法论验证核心功能
"""
import pytest
import sys
import os

# 添加 backend 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from unittest.mock import Mock, patch, MagicMock
import ee


@pytest.fixture
def mock_ee_init():
    """模拟 Earth Engine 初始化"""
    with patch('ee.Initialize'):
        with patch('ee.Geometry') as mock_geometry:
            mock_geometry.Point.return_value.buffer.return_value = Mock()
            yield mock_geometry


@pytest.fixture
def test_region():
    """测试用的区域几何"""
    mock_region = MagicMock()
    return mock_region


def test_dna_mode_band_selection(mock_ee_init, test_region):
    """测试地表 DNA 模式的波段选择是否正确"""
    from gee_service import get_layer_logic
    
    # 创建 mock ImageCollection 和 Image
    mock_collection = MagicMock()
    mock_mosaic = MagicMock()
    
    # 模拟 filterBounds().filterDate().mosaic() 返回 Image
    mock_collection.filterBounds.return_value.filterDate.return_value.mosaic.return_value = mock_mosaic
    
    # 模拟 select 返回新 Image
    mock_selected = MagicMock()
    mock_mosaic.select.return_value = mock_selected
    mock_selected.clip.return_value = mock_selected
    
    with patch('ee.ImageCollection', return_value=mock_collection):
        img, vis, suffix = get_layer_logic("地表 DNA (语义视图)", test_region)
        
        # 验证：应该选择 A00, A01, A02 三个波段
        mock_mosaic.select.assert_called_once()
        call_args = mock_mosaic.select.call_args[0][0]
        assert call_args == ['A00', 'A01', 'A02'], f"波段选择错误: {call_args}"
        assert suffix == "dna"


def test_intensity_mode_band_selection(mock_ee_init, test_region):
    """测试建设强度模式的波段选择"""
    from gee_service import get_layer_logic
    
    mock_collection = MagicMock()
    mock_mosaic = MagicMock()
    mock_collection.filterBounds.return_value.filterDate.return_value.mosaic.return_value = mock_mosaic
    
    # 模拟链式调用
    mock_selected = MagicMock()
    mock_renamed = MagicMock()
    mock_scaled = MagicMock()
    mock_masked = MagicMock()
    
    mock_mosaic.select.return_value = mock_selected
    mock_selected.rename.return_value = mock_renamed
    mock_renamed.unitScale.return_value = mock_scaled
    mock_scaled.updateMask.return_value = mock_masked
    mock_masked.clip.return_value = mock_masked
    
    with patch('ee.ImageCollection', return_value=mock_collection):
        img, vis, suffix = get_layer_logic("建设强度 (宏观管控)", test_region)
        
        # 验证：应该选择 A00 波段
        mock_mosaic.select.assert_called_once_with(['A00'])
        assert suffix == "intensity"
        # vis_params may omit 'bands' to avoid brittle band-name issues in cached assets
        assert "min" in vis and "max" in vis


def test_eco_mode_band_selection(mock_ee_init, test_region):
    """测试生态韧性模式的波段选择"""
    from gee_service import get_layer_logic
    
    mock_collection = MagicMock()
    mock_mosaic = MagicMock()
    mock_collection.filterBounds.return_value.filterDate.return_value.mosaic.return_value = mock_mosaic
    
    # 模拟链式调用
    mock_selected = MagicMock()
    mock_renamed = MagicMock()
    mock_inverted = MagicMock()
    mock_masked = MagicMock()
    
    mock_mosaic.select.return_value = mock_selected
    mock_selected.rename.return_value = mock_renamed
    mock_renamed.multiply.return_value = mock_inverted
    mock_inverted.updateMask.return_value = mock_masked
    mock_masked.clip.return_value = mock_masked
    
    with patch('ee.ImageCollection', return_value=mock_collection):
        img, vis, suffix = get_layer_logic("生态韧性 (绿色底线)", test_region)
        
        # 验证：应该选择 A02 波段
        mock_mosaic.select.assert_called_once_with(['A02'])
        mock_renamed.multiply.assert_called_once_with(-1)
        assert suffix == "eco"


def test_change_mode_calculation(mock_ee_init, test_region):
    """测试变化雷达模式的计算逻辑"""
    from gee_service import get_layer_logic
    
    mock_collection = MagicMock()
    mock_img19 = MagicMock()
    mock_img24 = MagicMock()
    
    # 模拟不同年份的图像（现在使用 filterBounds().filterDate().mosaic()）
    def mock_filter_date(start, end):
        mock_filtered = MagicMock()
        if '2019' in start:
            mock_filtered.mosaic.return_value = mock_img19
        else:
            mock_filtered.mosaic.return_value = mock_img24
        return mock_filtered

    mock_collection.filterBounds.return_value.filterDate.side_effect = mock_filter_date
    
    # 模拟欧氏距离计算
    mock_diff = MagicMock()
    mock_pow = MagicMock()
    mock_reduced = MagicMock()
    mock_dist = MagicMock()
    mock_masked = MagicMock()
    
    mock_img19.subtract.return_value = mock_diff
    mock_diff.pow.return_value = mock_pow
    mock_pow.reduce.return_value = mock_reduced
    mock_reduced.sqrt.return_value = mock_dist
    mock_dist.updateMask.return_value = mock_masked
    mock_masked.clip.return_value = mock_masked
    
    with patch('ee.ImageCollection', return_value=mock_collection):
        with patch('ee.Reducer.sum', return_value=Mock()):
            img, vis, suffix = get_layer_logic("变化雷达 (敏捷治理)", test_region)
            
            # 验证：应该计算两个时期的差异
            mock_img19.subtract.assert_called_once_with(mock_img24)
            mock_diff.pow.assert_called_once_with(2)
            assert suffix == "change"


def test_all_modes_return_correct_structure(mock_ee_init, test_region):
    """测试所有模式都返回正确的数据结构"""
    from gee_service import get_layer_logic
    
    modes = [
        "地表 DNA (语义视图)",
        "变化雷达 (敏捷治理)",
        "建设强度 (宏观管控)",
        "生态韧性 (绿色底线)"
    ]
    
    for mode in modes:
        # 创建基础 mock
        mock_collection = MagicMock()
        mock_image = MagicMock()
        mock_collection.filterDate.return_value.first.return_value = mock_image
        
        # 模拟所有可能的链式调用
        for attr in ['select', 'rename', 'unitScale', 'multiply', 'updateMask', 
                     'subtract', 'pow', 'reduce', 'sqrt', 'clip']:
            setattr(getattr(mock_image, attr, lambda *a, **k: mock_image)(), attr, 
                   lambda *a, **k: mock_image)
        
        mock_image.clip.return_value = mock_image
        
        with patch('ee.ImageCollection', return_value=mock_collection):
            with patch('ee.Reducer.sum', return_value=Mock()):
                img, vis, suffix = get_layer_logic(mode, test_region)
                
                # 验证返回类型
                assert img is not None, f"{mode} 返回的 image 为 None"
                assert isinstance(vis, dict), f"{mode} vis_params 不是字典"
                assert isinstance(suffix, str), f"{mode} suffix 不是字符串"
                assert len(suffix) > 0, f"{mode} suffix 为空"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
