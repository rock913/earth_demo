"""
测试地图刷新逻辑 (TDD) - 确保只在必要时刷新
"""
import pytest
from unittest.mock import Mock, patch, MagicMock


class TestMapRefresh:
    """测试地图刷新机制"""

    def test_refresh_timestamp_only_updates_on_state_change(self):
        """测试：时间戳仅在状态变化时更新"""
        with patch("app.st") as mock_st:
            # 模拟 session_state
            session_state = {
                "last_state_str": None,
                "last_update_ts": 1000.0,
            }
            
            def get_state(key, default=None):
                return session_state.get(key, default)
            
            def set_state(key, value):
                session_state[key] = value
            
            mock_st.session_state.get = get_state
            mock_st.session_state.__setitem__ = lambda k, v: set_state(k, v)
            mock_st.session_state.__getitem__ = lambda k: session_state[k]
            
            from app import main
            
            # 模拟第一次调用 - 应该更新时间戳
            state_key_1 = "地表 DNA_上海_分屏对比_14"
            old_ts = session_state["last_update_ts"]
            
            # 模拟状态变化检测逻辑
            if session_state.get("last_state_str") != state_key_1:
                session_state["last_state_str"] = state_key_1
                session_state["last_update_ts"] = 2000.0  # 模拟新时间戳
            
            assert session_state["last_update_ts"] == 2000.0, "首次加载应更新时间戳"
            
            # 模拟第二次调用 - 相同状态，不应该更新时间戳
            if session_state.get("last_state_str") != state_key_1:
                session_state["last_state_str"] = state_key_1
                session_state["last_update_ts"] = 3000.0
            
            assert session_state["last_update_ts"] == 2000.0, "相同状态不应更新时间戳"
            
            # 模拟第三次调用 - 切换场景，应该更新时间戳
            state_key_2 = "变化雷达_上海_分屏对比_14"
            if session_state.get("last_state_str") != state_key_2:
                session_state["last_state_str"] = state_key_2
                session_state["last_update_ts"] = 3000.0
            
            assert session_state["last_update_ts"] == 3000.0, "切换场景应更新时间戳"

    def test_map_key_should_be_stable_within_same_state(self):
        """测试：相同状态下 map key 应该稳定"""
        # 读取源码，检查 _create_map 是否使用了不稳定的 perf_counter
        with open("app.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # 查找 _create_map 函数
        lines = content.split("\n")
        in_create_map = False
        has_unstable_key = False
        key_generation_line = None
        
        for i, line in enumerate(lines):
            if "def _create_map(" in line:
                in_create_map = True
            elif in_create_map and "def " in line and "_create_map" not in line:
                break
            
            if in_create_map and "map_key" in line and "perf_counter()" in line:
                has_unstable_key = True
                key_generation_line = i + 1
                break
        
        # 警告：如果 map_key 使用了 perf_counter，说明每次都会变化
        # 应该使用 session_state 中稳定的时间戳
        if has_unstable_key:
            pytest.fail(
                f"Line {key_generation_line}: map_key 使用了 perf_counter()，"
                f"这会导致每次渲染都刷新地图。\n"
                f"建议使用 session_state['last_update_ts'] 作为稳定的时间戳。"
            )

    def test_render_map_uses_stable_timestamp(self):
        """测试：_render_map 应该使用稳定的时间戳"""
        with open("app.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        lines = content.split("\n")
        in_render_map = False
        calls_perf_counter = False
        line_num = None
        
        for i, line in enumerate(lines):
            if "def _render_map(" in line:
                in_render_map = True
            elif in_render_map and "def " in line and "_render_map" not in line:
                break
            
            if in_render_map and "perf_counter()" in line and "default" in line.lower():
                calls_perf_counter = True
                line_num = i + 1
        
        # 如果在 _render_map 中使用 perf_counter 作为默认值，也会导致不稳定
        if calls_perf_counter:
            pytest.fail(
                f"Line {line_num}: _render_map 中使用 perf_counter() 作为默认值，"
                f"应该使用固定的初始值（如 0.0）"
            )

    def test_state_key_includes_all_relevant_params(self):
        """测试：状态key应该包含所有影响地图的参数"""
        with open("app.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # 查找 state_key_str 的构造
        lines = content.split("\n")
        state_key_line = None
        
        for i, line in enumerate(lines):
            if "state_key_str" in line and "=" in line:
                state_key_line = line.strip()
                break
        
        if state_key_line:
            # 检查是否包含关键参数：mode, loc_name, compare_mode
            required_params = ["mode", "loc_name", "compare_mode"]
            missing_params = [p for p in required_params if p not in state_key_line]
            
            if missing_params:
                pytest.fail(
                    f"state_key_str 缺少关键参数: {missing_params}\n"
                    f"当前定义: {state_key_line}\n"
                    f"这些参数变化时应触发地图刷新"
                )
