"""
TDD Test: 变量作用域修复
测试目标：确保批量预热功能中的 gee_user_path 正确获取
"""

import re
from pathlib import Path


def test_batch_preheat_button_no_undefined_variable():
    """测试：批量预热按钮回调中不应有未定义的变量"""
    app_path = Path(__file__).parent.parent / "app.py"
    content = app_path.read_text(encoding="utf-8")
    
    # 提取批量预热按钮的代码块
    batch_button_pattern = r'if st\.button\("🚀 开始全量预热".*?\):(.*?)(?=\n        st\.markdown|$)'
    match = re.search(batch_button_pattern, content, re.DOTALL)
    
    assert match, "未找到批量预热按钮代码块"
    button_code = match.group(1)
    
    # 应该先计算 gee_user_path（通过 _get_gee_user_path 和 _resolve_effective_gee_user_path）
    assert "_get_gee_user_path()" in button_code, (
        "批量预热按钮应该先调用 _get_gee_user_path() 获取路径"
    )
    
    assert "_resolve_effective_gee_user_path" in button_code, (
        "批量预热按钮应该调用 _resolve_effective_gee_user_path 计算有效路径"
    )
    
    # 应该使用计算后的路径（effective_path 或类似变量）
    assert "effective_path" in button_code or "current_path" in button_code, (
        "批量预热按钮应该使用计算后的路径变量"
    )
    
    # 不应该直接使用未定义的 gee_user_path
    # 检查 _batch_export_all 的调用
    batch_call_match = re.search(r'_batch_export_all\(([^)]+)\)', button_code)
    assert batch_call_match, "未找到 _batch_export_all 调用"
    
    param = batch_call_match.group(1).strip()
    assert param != "gee_user_path", (
        f"_batch_export_all 不应直接使用未定义的 gee_user_path，而应使用计算后的变量。当前参数：{param}"
    )


def test_sidebar_controls_returns_asset_path():
    """测试：_sidebar_controls 应该返回 asset_path_override"""
    app_path = Path(__file__).parent.parent / "app.py"
    content = app_path.read_text(encoding="utf-8")
    
    # 提取 _sidebar_controls 的 return 语句
    sidebar_match = re.search(
        r"def _sidebar_controls\(.*?\):(.*?)(?=\ndef |\nif __name__|$)",
        content,
        re.DOTALL
    )
    
    assert sidebar_match, "_sidebar_controls 函数未找到"
    sidebar_code = sidebar_match.group(1)
    
    # 找到 return 语句
    return_match = re.search(r"return\s+(.+)", sidebar_code)
    assert return_match, "_sidebar_controls 未找到 return 语句"
    
    return_values = return_match.group(1)
    
    # 应该返回 asset_path_override
    assert "asset_path_override" in return_values, (
        "_sidebar_controls 应该返回 asset_path_override 以便在 main 中使用"
    )


def test_main_function_gets_effective_path():
    """测试：main 函数应该正确计算 gee_user_path"""
    app_path = Path(__file__).parent.parent / "app.py"
    content = app_path.read_text(encoding="utf-8")
    
    # 直接在整个文件中查找 main 函数中的关键代码
    # 应该有 gee_user_path = _resolve_effective_gee_user_path(...) 的赋值
    assert re.search(r'gee_user_path\s*=\s*_resolve_effective_gee_user_path', content), (
        "main 函数应该通过 _resolve_effective_gee_user_path 计算 gee_user_path"
    )
    
    # 应该接收 asset_path_override 从 _sidebar_controls
    assert re.search(r'_sidebar_controls\(\).*asset_path_override', content, re.DOTALL), (
        "main 函数应该从 _sidebar_controls 接收 asset_path_override"
    )
