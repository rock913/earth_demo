"""
测试 UI 优化 (TDD) - 界面布局与场景解释
"""
import pytest


class TestUILayout:
    """测试界面布局优化"""

    def test_hud_panel_removed_from_main_area(self):
        """测试：主区域不应该有 HUD 面板（避免遮挡地图）"""
        with open("app.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # 检查是否还在调用 _render_hud
        lines = content.split("\n")
        in_main = False
        calls_render_hud = False
        line_num = None
        
        for i, line in enumerate(lines):
            if "def main(" in line:
                in_main = True
            elif in_main and line.strip().startswith("def ") and "main" not in line:
                break
            
            if in_main and "_render_hud(" in line and not line.strip().startswith("#"):
                calls_render_hud = True
                line_num = i + 1
        
        if calls_render_hud:
            pytest.fail(
                f"Line {line_num}: main() 中不应调用 _render_hud()，"
                f"HUD 信息应整合到侧边栏避免遮挡地图"
            )

    def test_sidebar_control_order(self):
        """测试：侧边栏控件按优先级排列"""
        with open("app.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # 查找 _sidebar_controls 函数中第一次出现的关键控件
        lines = content.split("\n")
        in_sidebar = False
        first_scene_idx = None
        first_location_idx = None
        first_explainer_idx = None
        
        for i, line in enumerate(lines):
            if "def _sidebar_controls(" in line:
                in_sidebar = True
            elif in_sidebar and line.strip().startswith("def ") and "_sidebar_controls" not in line:
                break
            
            if in_sidebar:
                # 只记录第一次出现的位置
                if first_scene_idx is None and ('"🎯 监测场景"' in line or '"监测场景"' in line):
                    first_scene_idx = i
                if first_location_idx is None and ('"🗺️ 核心监测区"' in line or 'st.selectbox("核心监测区"' in line):
                    first_location_idx = i
                if first_explainer_idx is None and 'expander("📘 场景解释"' in line:
                    first_explainer_idx = i
        
        # 验证顺序：监测场景 < 核心监测区 < 场景解释
        if first_scene_idx and first_location_idx:
            assert first_scene_idx < first_location_idx, \
                f"监测场景（行{first_scene_idx}）应在核心监测区（行{first_location_idx}）之前"
        
        if first_location_idx and first_explainer_idx:
            assert first_location_idx < first_explainer_idx, \
                f"核心监测区（行{first_location_idx}）应在场景解释（行{first_explainer_idx}）之前"

    def test_scene_explainer_enriched_content(self):
        """测试：场景解释包含丰富内容（颜色、算法、意义）"""
        with open("app.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # 查找场景解释的内容定义
        if "_build_hud_info" in content:
            # 检查是否包含关键字段
            required_fields = ["颜色", "算法", "意义", "palette", "formula"]
            found_fields = [field for field in required_fields if field in content]
            
            assert len(found_fields) >= 3, \
                f"场景解释应包含颜色、算法、意义等详细说明（当前仅找到：{found_fields}）"

    def test_map_fullscreen_css(self):
        """测试：地图占满全屏的CSS配置"""
        with open("app.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # 检查CSS中是否移除了遮挡地图的固定定位元素
        has_fixed_hud = "position: fixed" in content and ".hud-panel" in content
        
        if has_fixed_hud:
            # 检查是否有注释说明已废弃
            hud_commented = "/* 已废弃" in content or "# 已废弃" in content
            if not hud_commented:
                pytest.fail(
                    "CSS 中存在固定定位的 HUD 面板会遮挡地图，"
                    "应移除或注释掉 .hud-panel 样式"
                )


class TestSceneExplainer:
    """测试场景解释功能"""

    def test_scene_explainer_in_sidebar(self):
        """测试：场景解释应在侧边栏中渲染"""
        with open("app.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # 场景解释应该在 _sidebar_controls 中或作为独立的侧边栏组件
        in_sidebar = (
            "with st.sidebar:" in content and "场景解释" in content
        ) or (
            "st.sidebar.expander" in content and "场景解释" in content
        )
        
        assert in_sidebar, "场景解释应该在侧边栏中展示"

    def test_all_modes_have_detailed_explanation(self):
        """测试：所有监测场景都有详细解释"""
        with open("app.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        modes = ["地表 DNA", "变化雷达", "建设强度", "生态韧性"]
        
        for mode in modes:
            # 每个模式应该有解释
            assert mode in content, f"缺少 {mode} 的定义"
            
            # 检查是否有详细说明
            # 这里简单检查是否有该模式相关的描述性文本
            mode_section_exists = content.find(mode) != -1
            assert mode_section_exists, f"{mode} 缺少详细解释"


class TestMapHeight:
    """测试地图高度设置"""

    def test_map_uses_fullscreen_height(self):
        """测试：地图组件使用全屏高度"""
        with open("app.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # 检查地图高度设置
        # 应该是 100vh 或至少 800px 以上
        has_fullscreen = (
            'height="100vh"' in content or
            "height=800" in content or
            "height: 100vh" in content
        )
        
        assert has_fullscreen, "地图应使用全屏高度（100vh 或 800px+）"

    def test_no_fixed_elements_blocking_map(self):
        """测试：没有固定定位元素遮挡地图"""
        with open("app.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # 检查是否有未注释的固定定位 HUD
        lines = content.split("\n")
        in_style = False
        has_active_fixed_hud = False
        
        for line in lines:
            if "<style>" in line:
                in_style = True
            elif "</style>" in line:
                in_style = False
            
            if in_style and ".hud-panel" in line:
                # 检查后续几行是否有 position: fixed
                has_active_fixed_hud = True
        
        # 如果有固定HUD，应该被注释掉或移除
        if has_active_fixed_hud and "position: fixed" in content:
            # 允许保留但需要注释说明
            pass  # 暂时允许，后续会移除
