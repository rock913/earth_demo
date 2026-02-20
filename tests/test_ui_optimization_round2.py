"""
测试UI优化需求 (TDD) - 第二轮
"""
import pytest


class TestUIOptimizationRound2:
    """测试第二轮UI优化需求"""

    def test_shanghai_not_in_locations(self):
        """测试：上海不应出现在核心监测区列表中"""
        with open("app.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # 查找 locations 字典定义
        lines = content.split("\n")
        in_locations_dict = False
        shanghai_found = False
        
        for i, line in enumerate(lines):
            if 'locations = {' in line:
                in_locations_dict = True
            elif in_locations_dict and '}' in line and 'coords' not in line:
                break
            
            if in_locations_dict and "上海" in line:
                shanghai_found = True
                pytest.fail(f"Line {i+1}: 发现'上海'在核心监测区列表中，应该被移除")
        
        assert not shanghai_found, "上海应该从核心监测区中移除"

    def test_debug_mode_near_demo_preset(self):
        """测试：调试模式按钮应该在一键演示按钮附近"""
        with open("app.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        lines = content.split("\n")
        demo_preset_line = None
        debug_mode_line = None
        
        for i, line in enumerate(lines):
            if 'btn_demo_preset' in line and 'st.button' in line:
                demo_preset_line = i
            if 'chk_debug_mode' in line or ('debug' in line.lower() and 'checkbox' in line):
                if demo_preset_line and abs(i - demo_preset_line) <= 5:
                    debug_mode_line = i
                    break
        
        if demo_preset_line:
            assert debug_mode_line is not None, \
                f"调试模式按钮应该在一键演示按钮(Line {demo_preset_line + 1})附近(±5行内)"

    def test_no_duplicate_locations_definition(self):
        """测试：locations 字典不应该重复定义"""
        with open("app.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        lines = content.split("\n")
        locations_definitions = []
        
        for i, line in enumerate(lines):
            # 只检查 locations = {，不检查 all_locations = {（用于批量预热）
            if 'locations = {' in line.strip() and 'all_locations' not in line:
                locations_definitions.append(i + 1)
        
        assert len(locations_definitions) <= 1, \
            f"locations 字典定义了 {len(locations_definitions)} 次(Lines: {locations_definitions})，应该只定义一次"

    def test_no_duplicate_selectbox(self):
        """测试：核心监测区的 selectbox 不应该重复"""
        with open("app.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # 在 _sidebar_controls 函数中查找
        lines = content.split("\n")
        in_sidebar_controls = False
        selectbox_count = 0
        selectbox_lines = []
        
        for i, line in enumerate(lines):
            if "def _sidebar_controls(" in line:
                in_sidebar_controls = True
            elif in_sidebar_controls and line.startswith("def ") and "_sidebar_controls" not in line:
                break
            
            if in_sidebar_controls and "st.selectbox" in line and ("核心监测区" in line or "监测区" in line):
                selectbox_count += 1
                selectbox_lines.append(i + 1)
        
        assert selectbox_count == 1, \
            f"核心监测区选择框出现了 {selectbox_count} 次(Lines: {selectbox_lines})，应该只有1次"

    def test_map_fullscreen_css(self):
        """测试：地图应该铺满屏幕(100vh)"""
        with open("app.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # 检查 CSS 中是否有 iframe 100vh 设置
        assert "iframe { height: 100vh" in content or "iframe{height:100vh" in content, \
            "CSS 中应该包含 'iframe { height: 100vh' 使地图铺满屏幕"
        
        # 检查 padding 是否为 0
        assert "padding: 0" in content or "padding:0" in content, \
            "block-container 的 padding 应该为 0"

    def test_layer_control_visible(self):
        """测试：图层控制应该可见且易于操作"""
        with open("app.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # 检查是否添加了图层控制
        assert "LayerControl" in content or "add_layer_control" in content, \
            "地图应该包含图层控制按钮"

    def test_geemap_height_fullscreen(self):
        """测试：geemap 地图高度应该设置为适配全屏"""
        with open("app.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        lines = content.split("\n")
        in_create_map = False
        geemap_height_found = False
        
        for line in lines:
            if "def _create_map(" in line:
                in_create_map = True
            elif in_create_map and line.startswith("def ") and "_create_map" not in line:
                break
            
            if in_create_map and "geemap.Map" in line:
                # 检查接下来几行是否设置了 height
                if 'height=' in line:
                    geemap_height_found = True
        
        assert geemap_height_found, "geemap.Map 应该设置 height 参数以适配屏幕"
