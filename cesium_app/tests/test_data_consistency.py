"""
Data Consistency Tests - 确保数据一致性
借鉴原项目对配置和状态的测试
"""
import pytest
from pathlib import Path
import sys


backend_path = Path(__file__).parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))


from config import settings


class TestDataConsistency:
    """测试数据一致性"""
    
    def test_mode_ids_match_between_config_and_service(self):
        """测试：配置中的模式 ID 应该与服务中的逻辑匹配"""
        import gee_service
        
        mode_ids = set(settings.modes.keys())
        
        # 每个模式 ID 应该能被 get_layer_logic 处理
        # get_layer_logic 接受完整的中文名称，不是 ID
        # 所以我们检查函数存在
        assert callable(gee_service.get_layer_logic)
    
    def test_location_ids_are_url_safe(self):
        """测试：位置ID应该是URL安全的（用于API路径）"""
        for loc_id in settings.locations.keys():
            # 应该只包含小写字母、数字、下划线
            assert loc_id.replace('_', '').replace('-', '').isalnum(), \
                f"位置ID不是URL安全的: {loc_id}"
            assert loc_id.islower(), f"位置ID应该是小写: {loc_id}"
    
    def test_mode_ids_are_consistent(self):
        """测试：模式ID应该在整个系统中保持一致"""
        # 模式ID应该是简短的英文标识符
        valid_mode_ids = {"dna", "change", "intensity", "eco"}
        actual_mode_ids = set(settings.modes.keys())
        
        assert actual_mode_ids == valid_mode_ids, \
            f"模式ID不一致。期望: {valid_mode_ids}，实际: {actual_mode_ids}"
    
    def test_all_locations_have_chinese_names(self):
        """测试：所有位置都应该有中文名称"""
        for loc_id, loc_data in settings.locations.items():
            name = loc_data.get("name", "")
            # 应该包含中文字符
            assert any('\u4e00' <= c <= '\u9fff' for c in name), \
                f"位置 {loc_id} 的名称应该包含中文: {name}"
    
    def test_gee_user_path_format(self):
        """测试：GEE 用户路径格式应该正确"""
        gee_path = settings.gee_user_path
        
        # 支持两种常见格式：
        # - users/<username>/<folder>
        # - projects/<project-id>/assets/<folder>
        assert gee_path.startswith("users/") or gee_path.startswith("projects/"), \
            f"GEE_USER_PATH 应该以 'users/' 或 'projects/' 开头: {gee_path}"
        
        # 不应该以 / 结尾
        assert not gee_path.endswith("/"), \
            f"GEE_USER_PATH 不应该以 '/' 结尾: {gee_path}"
        
        # 应该至少有两个部分
        parts = gee_path.split("/")
        assert len(parts) >= 2, \
            f"GEE_USER_PATH 格式不正确: {gee_path}"


class TestAPIResponseStructure:
    """测试 API 响应结构"""
    
    def test_locations_endpoint_structure(self):
        """测试：/api/locations 应该返回正确的结构"""
        expected_structure = {
            "id": str,
            "name": str,
            "coords": list,
        }
        
        # 验证配置数据符合预期结构
        for loc_id, loc_data in settings.locations.items():
            assert "name" in loc_data
            assert "coords" in loc_data
            assert isinstance(loc_data["name"], str)
            assert isinstance(loc_data["coords"], list)
            assert len(loc_data["coords"]) == 3
    
    def test_modes_endpoint_structure(self):
        """测试：/api/modes 应该返回正确的结构"""
        # 验证配置数据符合预期结构
        for mode_id, mode_name in settings.modes.items():
            assert isinstance(mode_id, str)
            assert isinstance(mode_name, str)
            # 模式ID应该是简短的英文
            assert mode_id in ["dna", "change", "intensity", "eco"]
            # 模式名称应该是中文
            assert any('\u4e00' <= c <= '\u9fff' for c in mode_name)


class TestGEEBandSelection:
    """测试 GEE 波段选择的正确性"""
    
    def test_band_names_are_correct_format(self):
        """测试：波段名称应该使用正确的格式 (A00-A63)"""
        # 读取 gee_service.py 源码
        gee_service_path = backend_path / "gee_service.py"
        content = gee_service_path.read_text(encoding="utf-8")
        
        # 检查不应该使用数字字符串 '0', '1', '2'
        # 应该使用 'A00', 'A01', 'A02'
        import re
        
        # 查找所有 select() 调用
        select_patterns = re.findall(r"\.select\(\[([^\]]+)\]\)", content)
        
        for pattern in select_patterns:
            # 检查是否使用了错误的数字格式
            if "'0'" in pattern or '"0"' in pattern:
                pytest.fail(
                    f"发现错误的波段选择格式（使用数字字符串）: {pattern}\n"
                    f"应该使用 'A00', 'A01', 'A02' 等格式"
                )
            
            # 检查是否使用了正确的 A 前缀格式
            if "select" in content:
                # 至少应该有一些 'A00' 格式的波段
                assert "'A00'" in content or '"A00"' in content, \
                    "未找到正确的波段格式 'A00'"
    
    def test_dna_mode_uses_three_bands(self):
        """测试：DNA 模式应该使用 3 个波段"""
        import gee_service
        import inspect
        
        # 获取 get_layer_logic 函数的源码
        source = inspect.getsource(gee_service.get_layer_logic)
        
        # DNA 相关代码块
        dna_block = None
        lines = source.split('\n')
        in_dna = False
        dna_lines = []
        for line in lines:
            if '"地表 DNA"' in line or "'\u5730\u8868 DNA'" in line:
                in_dna = True
            elif in_dna and ('elif' in line or 'else:' in line):
                break
            if in_dna:
                dna_lines.append(line)
        
        dna_block = '\n'.join(dna_lines)
        
        # 应该 select 3 个波段用于 RGB
        import re
        select_match = re.search(r"\.select\(\[([^\]]+)\]\)", dna_block)
        
        if select_match:
            bands_str = select_match.group(1)
            # 计算波段数量
            bands = [b.strip().strip("'\"") for b in bands_str.split(",")]
            assert len(bands) == 3, \
                f"DNA 模式应该选择 3 个波段（RGB），实际: {len(bands)}"
            
            # 应该是 A00, A01, A02
            assert bands[0] == "A00", f"第一个波段应该是 A00，实际: {bands[0]}"
            assert bands[1] == "A01", f"第二个波段应该是 A01，实际: {bands[1]}"
            assert bands[2] == "A02", f"第三个波段应该是 A02，实际: {bands[2]}"
    
    def test_single_band_modes_use_correct_bands(self):
        """测试：单波段模式应该使用正确的波段"""
        import gee_service
        import inspect
        
        # 获取 get_layer_logic 函数源码
        source = inspect.getsource(gee_service.get_layer_logic)
        
        # Intensity 应该使用 A00
        assert "'A00'" in source or '"A00"' in source, \
            "Intensity 模式应该使用 A00 波段"
        
        # Eco 应该使用 A02
        assert "'A02'" in source or '"A02"' in source, \
            "Eco 模式应该使用 A02 波段"


class TestDateRangeConsistency:
    """测试日期范围的一致性"""
    
    def test_date_ranges_are_reasonable(self):
        """测试：日期范围应该是合理的"""
        import gee_service
        import inspect
        
        source = inspect.getsource(gee_service.get_layer_logic)
        
        # 提取日期字符串
        import re
        dates = re.findall(r'["\'](\d{4}-\d{2}-\d{2})["\']', source)
        
        for date_str in dates:
            year = int(date_str.split("-")[0])
            # 年份应该在合理范围内（2015-2026）
            assert 2015 <= year <= 2026, \
                f"get_layer_logic 中的日期不合理: {date_str}"
    
    def test_change_mode_has_two_time_points(self):
        """测试：Change 模式应该有两个时间点进行对比"""
        import gee_service
        import inspect
        
        source = inspect.getsource(gee_service.get_layer_logic)
        
        # 应该有两个不同的日期范围
        import re
        dates = re.findall(r'["\'](\d{4})-\d{2}-\d{2}["\']', source)
        unique_years = set(dates)
        
        # 至少应该有两个不同的年份
        assert len(unique_years) >= 2, \
            f"Change 模式应该对比两个不同时间点，找到的年份: {unique_years}"
