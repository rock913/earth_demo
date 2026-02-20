# TDD修复总结 - 地图刷新优化

## 问题描述

原始代码中地图刷新频率过高，导致：
1. 每次组件重渲染都会创建新的地图实例
2. 用户体验差（闪烁、加载慢）
3. 资源浪费（重复请求 GEE 数据）

## TDD修复流程

### 第1阶段：问题定位测试

创建 `tests/test_map_refresh.py`，包含4个测试用例：

1. **test_refresh_timestamp_only_updates_on_state_change**
   - 验证时间戳仅在状态变化时更新
   - ✅ 通过：逻辑正确，但实现有问题

2. **test_map_key_should_be_stable_within_same_state**
   - 检测 `_create_map` 中是否使用不稳定的 `perf_counter()`
   - ❌ 失败：发现 Line 948 使用了 `perf_counter()`

3. **test_render_map_uses_stable_timestamp**
   - 检测 `_render_map` 是否使用稳定时间戳
   - ✅ 通过

4. **test_state_key_includes_all_relevant_params**
   - 验证状态 key 包含所有相关参数
   - ✅ 通过

### 第2阶段：代码修复

基于测试失败结果，进行以下修复：

#### 修复1：移除不必要的 map_key 生成

```python
# 修复前：
map_key = f"map_{lat}_{lon}_{zoom}_{compare_mode}_{ai_opacity}_{perf_counter()}"

# 修复后：
# 完全移除，不需要在此处生成动态 key
```

**原因**：每次调用 `perf_counter()` 都会生成新值，导致无意义的刷新。

#### 修复2：使用稳定的初始时间戳

```python
# 修复前：
last_update = st.session_state.get('last_update_ts', perf_counter())

# 修复后：
_ensure_runtime_state()
if 'last_update_ts' not in st.session_state:
    st.session_state['last_update_ts'] = 0.0
last_update = st.session_state.get('last_update_ts', 0.0)
```

**原因**：默认值不应该是动态的，否则首次渲染也会导致不稳定。

#### 修复3：修正拼写错误并增强状态检测

```python
# 修复前：
state_key_str = f"{mode}_{loc_name}_{compare_mode}_{zoom}"
if st.session_state.get('last_sate_str') != state_key_str:  # 拼写错误
    st.session_state['last_sate_str'] = state_key_str

# 修复后：
ai_opacity = float(st.session_state.get("ui_ai_opacity", 0.85))
state_key_str = f"{mode}_{loc_name}_{compare_mode}_{zoom}_{ai_opacity}"
if st.session_state.get('last_state_str') != state_key_str:
    st.session_state['last_state_str'] = state_key_str
    st.session_state['last_update_ts'] = perf_counter()
```

**改进**：
- 修复拼写：`last_sate_str` → `last_state_str`
- 增加透明度参数到状态 key，确保透明度变化时也触发刷新

#### 修复4：简化 _render_map 逻辑

```python
# 修复前：使用 map_container 包裹
map_container = st.empty()
with map_container:
    m.to_streamlit(height=800)

# 修复后：直接渲染
m.to_streamlit(height=800)
# 或者对于 folium
map_key = f"folium_map_{last_update}"
st_folium(m, height=800, width=None, key=map_key)
```

**原因**：`st.empty()` 容器不是必需的，简化代码逻辑。

### 第3阶段：验证修复

再次运行测试：

```bash
pytest tests/test_map_refresh.py -v
```

**结果**：✅ 4/4 测试通过

运行全部测试：

```bash
pytest tests/ -v
```

**结果**：✅ 13/13 测试通过

## 修复效果

### 修复前
- ❌ 每次 Streamlit 重渲染都刷新地图
- ❌ 无意义的 GEE 瓦片请求
- ❌ 用户体验差（频繁闪烁）

### 修复后
- ✅ 仅在以下情况刷新地图：
  - 切换城市位置
  - 切换监测场景（地表DNA、变化雷达等）
  - 切换显示方式（叠加/分屏）
  - 调整缩放级别
  - 调整 AI 图层透明度
- ✅ 相同状态下不重复刷新
- ✅ 性能优化，减少不必要的计算

## 测试覆盖

| 测试文件 | 测试用例数 | 覆盖功能 |
|---------|----------|---------|
| test_map_refresh.py | 4 | 地图刷新逻辑 |
| test_map_creation.py | 2 | 地图创建与变量命名 |
| test_smart_cache.py | 5 | 智能缓存机制 |
| test_app_smoke.py | 2 | 应用启动与导入 |
| **总计** | **13** | **核心功能全覆盖** |

## 最佳实践总结

1. **稳定的状态标识**
   - 使用固定初始值（如 `0.0`）而非动态函数（`perf_counter()`）
   - 状态 key 应包含所有影响渲染的参数

2. **TDD 工作流**
   - 先写测试定义预期行为
   - 运行测试发现问题
   - 修复代码通过测试
   - 回归测试确保无副作用

3. **性能优化原则**
   - 避免无意义的组件重渲染
   - 使用稳定的 key 控制刷新时机
   - 状态变化检测应精确且高效

## 相关文件

- 代码修复：[app.py](../app.py#L930-L1010)
- 测试用例：[tests/test_map_refresh.py](test_map_refresh.py)
- 总测试数：13 个（全部通过 ✅）
