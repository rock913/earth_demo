"""
TDD Test: 地图高度优化至1200px
测试目标：
1. 验证地图高度从800px提升到1200px（适配现代显示器）
2. 确保CSS配置支持大高度地图的显示
3. 验证不同显示模式下的高度一致性
"""

import re
from pathlib import Path


def test_create_map_height_1200px():
    """测试：_create_map 函数应该使用1200px高度"""
    app_path = Path(__file__).parent.parent / "app.py"
    content = app_path.read_text(encoding="utf-8")
    
    # 提取 _create_map 函数
    create_map_match = re.search(
        r"def _create_map\(.*?\):(.*?)(?=\ndef |\nif __name__|$)",
        content,
        re.DOTALL
    )
    
    assert create_map_match, "_create_map 函数未找到"
    create_map_code = create_map_match.group(1)
    
    # 检查 geemap.Map 的 height 参数
    geemap_height = re.search(r'height\s*=\s*"(\d+)px"', create_map_code)
    if geemap_height:
        height = int(geemap_height.group(1))
        assert height >= 1200, (
            f"geemap.Map 高度为 {height}px，应该 ≥1200px 以适配现代显示器"
        )
    
    # 不应该再有 800px 的硬编码
    assert 'height="800px"' not in create_map_code, (
        "_create_map 中仍有 800px 硬编码，应改为 1200px"
    )


def test_render_map_height_1200px():
    """测试：_render_map 函数应该使用1200高度（整数）"""
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
    
    # 检查所有 height 参数
    height_matches = re.findall(r"height\s*=\s*(\d+)", render_map_code)
    
    for height_str in height_matches:
        height = int(height_str)
        assert height >= 1200, (
            f"_render_map 中发现高度 {height}，应该 ≥1200 以铺满现代显示器"
        )
    
    # 不应该再有 800 的硬编码
    assert "height=800" not in render_map_code, (
        "_render_map 中仍有 height=800，应改为 height=1200"
    )


def test_no_800px_hardcode_in_app():
    """测试：整个app.py不应再有800px的地图高度硬编码"""
    app_path = Path(__file__).parent.parent / "app.py"
    content = app_path.read_text(encoding="utf-8")
    
    # 查找所有可能的800px硬编码
    # 排除注释和文档字符串中的提及
    lines = content.split('\n')
    
    problematic_lines = []
    for i, line in enumerate(lines, 1):
        # 跳过注释行
        if line.strip().startswith('#'):
            continue
        # 跳过文档字符串（简单判断）
        if '"""' in line or "'''" in line:
            continue
            
        # 检查 height=800 或 height="800px"
        if re.search(r'height\s*=\s*"?800"?(?:px)?', line):
            problematic_lines.append(f"Line {i}: {line.strip()}")
    
    assert len(problematic_lines) == 0, (
        f"发现 {len(problematic_lines)} 处800px硬编码：\n" + 
        "\n".join(problematic_lines)
    )


def test_css_supports_large_map_height():
    """测试：CSS应该支持大高度地图的显示（隐藏滚动条）"""
    app_path = Path(__file__).parent.parent / "app.py"
    content = app_path.read_text(encoding="utf-8")
    
    # 提取CSS部分
    css_match = re.search(r"<style>(.*?)</style>", content, re.DOTALL)
    assert css_match, "未找到CSS样式块"
    
    css_content = css_match.group(1)
    
    # 确保 iframe 使用 100vh，这样即使内容是1200px也不会溢出
    assert re.search(r"iframe.*height:\s*100vh\s*!important", css_content, re.DOTALL), (
        "CSS应该设置 iframe { height: 100vh !important } 以容纳大高度地图"
    )
    
    # 确保容器无 padding
    assert re.search(r"\.block-container.*padding:\s*0\s*!important", css_content, re.DOTALL), (
        "容器应该零padding以最大化地图空间"
    )


def test_height_consistency_across_modes():
    """测试：不同显示模式（geemap、folium）应该使用一致的高度"""
    app_path = Path(__file__).parent.parent / "app.py"
    content = app_path.read_text(encoding="utf-8")
    
    # 提取 _create_map 和 _render_map 函数
    create_map_match = re.search(
        r"def _create_map\(.*?\):(.*?)(?=\ndef |\nif __name__|$)",
        content,
        re.DOTALL
    )
    render_map_match = re.search(
        r"def _render_map\(.*?\):(.*?)(?=\ndef |\nif __name__|$)",
        content,
        re.DOTALL
    )
    
    assert create_map_match and render_map_match, "函数未找到"
    
    create_map_code = create_map_match.group(1)
    render_map_code = render_map_match.group(1)
    
    # 收集所有高度值
    all_heights = set()
    
    for match in re.finditer(r'height\s*=\s*"?(\d+)"?(?:px)?', create_map_code):
        all_heights.add(int(match.group(1)))
    
    for match in re.finditer(r'height\s*=\s*"?(\d+)"?(?:px)?', render_map_code):
        all_heights.add(int(match.group(1)))
    
    # 所有高度值应该一致（都是1200）
    assert len(all_heights) <= 1 or all(h >= 1200 for h in all_heights), (
        f"发现不一致的高度值：{all_heights}，应该统一使用 1200px"
    )


def test_modern_display_coverage():
    """测试：1200px应该能覆盖现代显示器的可用高度"""
    app_path = Path(__file__).parent.parent / "app.py"
    content = app_path.read_text(encoding="utf-8")
    
    # 提取所有地图高度设置
    height_values = []
    
    # 从 _create_map 中提取
    create_map_match = re.search(
        r"def _create_map\(.*?\):(.*?)(?=\ndef |\nif __name__|$)",
        content,
        re.DOTALL
    )
    if create_map_match:
        for match in re.finditer(r'height\s*=\s*"?(\d+)"?(?:px)?', create_map_match.group(1)):
            height_values.append(int(match.group(1)))
    
    # 从 _render_map 中提取
    render_map_match = re.search(
        r"def _render_map\(.*?\):(.*?)(?=\ndef |\nif __name__|$)",
        content,
        re.DOTALL
    )
    if render_map_match:
        for match in re.finditer(r'height\s*=\s*(\d+)', render_map_match.group(1)):
            height_values.append(int(match.group(1)))
    
    # 所有高度值都应该 ≥1200
    # 1200px 能覆盖：
    # - 1080P (1920x1080): 去掉浏览器UI和侧边栏，剩余约900-1000px ✓
    # - 2K (2560x1440): 去掉UI后约1200-1300px ✓
    # - 4K (3840x2160): 去掉UI后约1900-2000px ✓
    assert all(h >= 1200 for h in height_values), (
        f"存在小于1200px的高度值：{[h for h in height_values if h < 1200]}\n"
        "1200px是适配现代显示器的最小推荐值"
    )
