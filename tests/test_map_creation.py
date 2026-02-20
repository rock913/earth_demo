"""
测试地图创建逻辑 (TDD)
"""
import pytest


class TestMapCreation:
    """测试 _create_map 函数的各种场景"""

    def test_create_map_variable_naming_consistency(self):
        """测试变量命名一致性 - 确保不使用未定义变量"""
        # 这是一个静态代码检查的补充测试
        import ast
        
        # 直接读取源文件，避免导入问题
        with open("app.py", "r", encoding="utf-8") as f:
            source = f.read()
        
        # 查找 _create_map 函数
        tree = ast.parse(source)
        
        create_map_func = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_create_map":
                create_map_func = node
                break
        
        assert create_map_func is not None, "_create_map 函数未找到"
        
        # 收集所有变量名使用
        used_names = set()
        defined_names = set()
        
        for node in ast.walk(create_map_func):
            if isinstance(node, ast.Name):
                if isinstance(node.ctx, ast.Store):
                    defined_names.add(node.id)
                elif isinstance(node.ctx, ast.Load):
                    used_names.add(node.id)
        
        # 检查 'ai_layer_vis' 不应该被使用（除非被定义）
        if "ai_layer_vis" in used_names:
            assert "ai_layer_vis" in defined_names, \
                "变量 'ai_layer_vis' 被使用但未定义！应使用 'ai_rgb' 或 'layer_img'"
        
        # 验证应该使用 ai_rgb
        assert "ai_rgb" in used_names, "应该使用 'ai_rgb' 变量"

    def test_folium_fallback_uses_correct_variable(self):
        """测试 folium fallback 代码块使用正确的变量"""
        with open("app.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # 查找 _add_ee_layer 调用
        # 确保 fallback 部分不使用 ai_layer_vis
        lines = content.split("\n")
        
        in_create_map = False
        in_folium_fallback = False
        fallback_lines = []
        
        for i, line in enumerate(lines):
            if "def _create_map(" in line:
                in_create_map = True
            elif in_create_map and "def " in line and "_create_map" not in line:
                break
            
            if in_create_map and "# Fallback to pure folium" in line:
                in_folium_fallback = True
            
            if in_folium_fallback:
                fallback_lines.append((i+1, line))
                if "return m" in line and in_create_map:
                    break
        
        # 在 fallback 部分，不应该有 ai_layer_vis
        for line_num, line in fallback_lines:
            if "ai_layer_vis" in line:
                pytest.fail(
                    f"Line {line_num}: folium fallback 中不应使用 'ai_layer_vis'，应使用 'ai_rgb'\n"
                    f"问题行: {line}"
                )
        
        # 应该有使用 ai_rgb
        has_ai_rgb = any("ai_rgb" in line for _, line in fallback_lines)
        assert has_ai_rgb, "folium fallback 应该使用 'ai_rgb' 变量"

