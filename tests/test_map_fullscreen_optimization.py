"""
TDD Test: 地图铺满屏幕优化
测试目标：
1. 确保地图在右侧区域完全铺满（无白边、无滚动条）
2. 验证地图容器的CSS配置正确
3. 确保分屏对比模式下地图显示正常
"""

import re
from pathlib import Path


def test_streamlit_container_zero_padding():
    """测试：Streamlit容器应该零padding以避免白边"""
    app_path = Path(__file__).parent.parent / "app.py"
    content = app_path.read_text(encoding="utf-8")
    
    # 检查 block-container 的 padding 设置
    assert re.search(
        r"\.block-container\s*\{[^}]*padding:\s*0\s*!important[^}]*\}",
        content,
        re.DOTALL
    ), "block-container 应该设置 padding: 0 !important"
    
    # 检查 main block-container 的 padding-top
    assert re.search(
        r"\.main\s+\.block-container\s*\{[^}]*padding-top:\s*0\s*!important[^}]*\}",
        content,
        re.DOTALL
    ), "main block-container 应该设置 padding-top: 0 !important"


def test_map_iframe_fullscreen():
    """测试：地图iframe应该设置100vh高度以铺满屏幕"""
    app_path = Path(__file__).parent.parent / "app.py"
    content = app_path.read_text(encoding="utf-8")
    
    # 检查 iframe 的高度和宽度设置
    iframe_style = re.search(
        r"iframe\s*\{[^}]*\}",
        content,
        re.DOTALL
    )
    
    assert iframe_style is not None, "未找到 iframe CSS 规则"
    
    iframe_css = iframe_style.group(0)
    assert "height: 100vh" in iframe_css and "!important" in iframe_css, (
        "iframe 应该设置 height: 100vh !important"
    )
    assert "width: 100%" in iframe_css and "!important" in iframe_css, (
        "iframe 应该设置 width: 100% !important"
    )


def test_no_overflow_scroll_on_main():
    """测试：主容器不应有overflow:scroll，避免双滚动条"""
    app_path = Path(__file__).parent.parent / "app.py"
    content = app_path.read_text(encoding="utf-8")
    
    # 提取CSS部分
    css_match = re.search(r"<style>(.*?)</style>", content, re.DOTALL)
    assert css_match, "未找到CSS样式块"
    
    css_content = css_match.group(1)
    
    # 不应该有 overflow: scroll 或 overflow: auto 在主容器上
    # 除非明确需要（但通常100vh的iframe不需要）
    assert not re.search(r"\.main[^{]*\{[^}]*overflow:\s*scroll", css_content), (
        "主容器不应设置 overflow: scroll（会导致双滚动条）"
    )


def test_hide_streamlit_header_footer():
    """测试：隐藏Streamlit默认header/footer以最大化地图空间"""
    app_path = Path(__file__).parent.parent / "app.py"
    content = app_path.read_text(encoding="utf-8")
    
    # 检查是否隐藏了MainMenu和footer
    assert "#MainMenu {visibility: hidden;}" in content or "#MainMenu { visibility: hidden; }" in content, (
        "应该隐藏Streamlit的MainMenu"
    )
    assert "footer {visibility: hidden;}" in content or "footer { visibility: hidden; }" in content, (
        "应该隐藏Streamlit的footer"
    )


def test_sidebar_preserved():
    """测试：侧边栏应该保留可见（不能为了铺满而隐藏侧边栏）"""
    app_path = Path(__file__).parent.parent / "app.py"
    content = app_path.read_text(encoding="utf-8")
    
    # header 应该保留 visible，因为它包含侧边栏的展开/收起按钮
    assert re.search(r"header\s*\{[^}]*visibility:\s*visible", content), (
        "header 应该保留 visible 以支持侧边栏操作"
    )


def test_render_map_uses_adequate_height():
    """测试：_render_map应该使用足够的高度（800px或更高）"""
    app_path = Path(__file__).parent.parent / "app.py"
    content = app_path.read_text(encoding="utf-8")
    
    # 提取 _render_map 函数
    render_map_match = re.search(
        r"def _render_map\(.*?\):(.*?)(?=\ndef |\nif __name__|$)",
        content,
        re.DOTALL
    )
    
    assert render_map_match, "_render_map 函数未找到"
    render_map_code = render_map_match.group(1)
    
    # 检查 height 参数
    height_matches = re.findall(r"height\s*=\s*(\d+)", render_map_code)
    
    for height_str in height_matches:
        height = int(height_str)
        assert height >= 800, (
            f"_render_map 中的高度 {height}px 过小，应该 ≥800px 以充分利用屏幕空间"
        )


def test_geemap_split_map_support():
    """测试：geemap分屏对比模式应该正确配置"""
    app_path = Path(__file__).parent.parent / "app.py"
    content = app_path.read_text(encoding="utf-8")
    
    # 检查 _create_map 中的 split_map 调用
    create_map_match = re.search(
        r"def _create_map\(.*?\):(.*?)(?=\ndef |\nif __name__|$)",
        content,
        re.DOTALL
    )
    
    assert create_map_match, "_create_map 函数未找到"
    create_map_code = create_map_match.group(1)
    
    # 应该包含 split_map 调用
    assert "split_map" in create_map_code or "compare_mode" in create_map_code, (
        "_create_map 应该支持分屏对比模式"
    )


def test_dark_basemap_for_visibility():
    """测试：应该使用暗黑底图以确保AI图层可见"""
    app_path = Path(__file__).parent.parent / "app.py"
    content = app_path.read_text(encoding="utf-8")
    
    # 检查是否使用了暗黑底图
    assert "CartoDB.DarkMatter" in content or "dark_all" in content, (
        "应该使用暗黑底图（CartoDB.DarkMatter 或 dark_all）以确保AI图层可见性"
    )


def test_layer_control_enlarged():
    """测试：图层控制按钮应该放大以便操作"""
    app_path = Path(__file__).parent.parent / "app.py"
    content = app_path.read_text(encoding="utf-8")
    
    # 检查 Leaflet 图层控制按钮的样式
    assert re.search(
        r"\.leaflet-control-layers-toggle\s*\{[^}]*width:\s*44px\s*!important",
        content,
        re.DOTALL
    ), "图层控制按钮应该设置 width: 44px !important"
    
    assert re.search(
        r"\.leaflet-control-layers-toggle\s*\{[^}]*height:\s*44px\s*!important",
        content,
        re.DOTALL
    ), "图层控制按钮应该设置 height: 44px !important"


def test_css_optimization_complete():
    """测试：CSS优化应该完整且无冲突"""
    app_path = Path(__file__).parent.parent / "app.py"
    content = app_path.read_text(encoding="utf-8")
    
    # 提取完整的CSS
    css_match = re.search(r"<style>(.*?)</style>", content, re.DOTALL)
    assert css_match, "未找到CSS样式块"
    
    css_content = css_match.group(1)
    
    # 确保关键优化都存在
    optimizations = [
        (r"\.block-container.*padding:\s*0\s*!important", "容器零padding"),
        (r"iframe.*height:\s*100vh\s*!important", "地图100vh高度"),
        (r"iframe.*width:\s*100%\s*!important", "地图100%宽度"),
        (r"\.leaflet-control-layers-toggle.*width:\s*44px", "图层按钮放大"),
        (r"#MainMenu.*visibility:\s*hidden", "隐藏菜单"),
        (r"footer.*visibility:\s*hidden", "隐藏footer"),
    ]
    
    for pattern, desc in optimizations:
        assert re.search(pattern, css_content, re.DOTALL | re.IGNORECASE), (
            f"CSS优化缺失：{desc}（模式：{pattern}）"
        )
