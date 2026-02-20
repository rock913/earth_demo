"""
TDD Test: 代码清理与优化
测试目标：
1. 验证已废弃代码注释被清理
2. 验证地图铺满屏幕的CSS配置
3. 确保清理后功能不受影响
"""

import re
from pathlib import Path


def test_no_deprecated_function_comments():
    """测试：已废弃函数的注释应该被清理"""
    app_path = Path(__file__).parent.parent / "app.py"
    content = app_path.read_text(encoding="utf-8")
    
    # 不应该有 "已废弃：" 这样的注释残留
    deprecated_comments = re.findall(r"#\s*已废弃[：:].*", content)
    
    assert len(deprecated_comments) == 0, (
        f"发现 {len(deprecated_comments)} 个已废弃函数注释未清理：\n"
        + "\n".join(deprecated_comments)
    )


def test_no_commented_hud_css():
    """测试：已废弃的HUD CSS应该被清理"""
    app_path = Path(__file__).parent.parent / "app.py"
    content = app_path.read_text(encoding="utf-8")
    
    # 不应该有注释掉的HUD样式
    hud_css_comments = re.findall(r"/\*\s*已废弃.*HUD.*\*/", content, re.DOTALL)
    
    assert len(hud_css_comments) == 0, (
        f"发现 {len(hud_css_comments)} 个已废弃HUD CSS注释未清理"
    )


def test_map_fullscreen_css_configuration():
    """测试：地图铺满屏幕的CSS配置"""
    app_path = Path(__file__).parent.parent / "app.py"
    content = app_path.read_text(encoding="utf-8")
    
    # 检查关键CSS规则
    required_css = [
        r"\.block-container\s*\{[^}]*padding:\s*0\s*!important",  # 容器无padding
        r"\.main\s+\.block-container\s*\{[^}]*padding-top:\s*0\s*!important",  # 顶部无padding
        r"iframe\s*\{[^}]*height:\s*100vh\s*!important",  # iframe 100vh
        r"iframe\s*\{[^}]*width:\s*100%\s*!important",  # iframe 100%宽度
    ]
    
    for pattern in required_css:
        match = re.search(pattern, content, re.DOTALL)
        assert match is not None, (
            f"地图铺满屏幕的关键CSS缺失：{pattern}"
        )


def test_map_container_no_extra_margin():
    """测试：地图容器不应有额外的margin"""
    app_path = Path(__file__).parent.parent / "app.py"
    content = app_path.read_text(encoding="utf-8")
    
    # block-container 应该有 margin: 0
    assert re.search(r"\.block-container\s*\{[^}]*margin:\s*0\s*!important", content, re.DOTALL), (
        "地图容器应该设置 margin: 0 !important"
    )


def test_sidebar_width_not_affecting_map():
    """测试：侧边栏宽度配置不应影响地图显示"""
    app_path = Path(__file__).parent.parent / "app.py"
    content = app_path.read_text(encoding="utf-8")
    
    # 地图应该使用 width: 100%，自动适应剩余空间
    # 而不是硬编码宽度
    assert "iframe" in content and "width: 100%" in content, (
        "地图应该使用弹性宽度（100%）以适应侧边栏"
    )


def test_no_fixed_height_in_render_map():
    """测试：_render_map 不应使用固定高度（已使用CSS控制）"""
    app_path = Path(__file__).parent.parent / "app.py"
    content = app_path.read_text(encoding="utf-8")
    
    # 提取 _render_map 函数
    render_map_match = re.search(
        r"def _render_map\(.*?\):\s*\n(.*?)(?=\ndef |\nif __name__|$)",
        content,
        re.DOTALL
    )
    
    assert render_map_match, "_render_map 函数未找到"
    
    render_map_code = render_map_match.group(1)
    
    # 应该使用 height=800 作为默认值（被CSS覆盖）
    # 或者移除height参数，完全由CSS控制
    # 这里我们允许 height=800，因为CSS会覆盖
    # 主要确保不是太小的固定值（如 height=400）
    
    # 检查是否有小于600的height值
    small_height_matches = re.findall(r"height\s*=\s*(\d+)", render_map_code)
    for height_str in small_height_matches:
        height = int(height_str)
        assert height >= 600, (
            f"_render_map 中发现过小的固定高度：{height}px（应该 ≥600 或由CSS完全控制）"
        )


def test_essential_functions_exist():
    """测试：确保清理后核心函数仍然存在"""
    app_path = Path(__file__).parent.parent / "app.py"
    content = app_path.read_text(encoding="utf-8")
    
    essential_functions = [
        "_set_theme",
        "_init_gee",
        "_sidebar_controls",
        "_create_map",
        "_render_map",
        "smart_load",
        "get_layer_logic",
        "_build_s2_layer",
        "main",
    ]
    
    for func_name in essential_functions:
        pattern = rf"def {func_name}\("
        assert re.search(pattern, content), (
            f"核心函数 {func_name} 在清理后丢失！"
        )


def test_no_duplicate_session_state_init():
    """测试：session_state 初始化不应重复"""
    app_path = Path(__file__).parent.parent / "app.py"
    content = app_path.read_text(encoding="utf-8")
    
    # 提取 _sidebar_controls 函数
    sidebar_match = re.search(
        r"def _sidebar_controls\(.*?\):\s*\n(.*?)(?=\ndef |\nif __name__|$)",
        content,
        re.DOTALL
    )
    
    assert sidebar_match, "_sidebar_controls 函数未找到"
    sidebar_code = sidebar_match.group(1)
    
    # 统计同一个 session_state key 的 setdefault 调用次数
    # 每个 key 应该只出现一次
    state_keys = [
        "ui_compare_mode",
        "ui_ai_opacity",
        "ai_force_full",
        "th_change",
        "th_intensity",
        "th_eco",
    ]
    
    for key in state_keys:
        pattern = rf'st\.session_state\.setdefault\(["\']' + key
        matches = re.findall(pattern, sidebar_code)
        assert len(matches) <= 1, (
            f"session_state.setdefault('{key}') 在 _sidebar_controls 中重复定义 {len(matches)} 次"
        )
