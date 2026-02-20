import os
from time import perf_counter
from typing import Any, Optional, Tuple
from datetime import datetime

import folium
import streamlit as st

try:
    import ee
except Exception as exc:  # pragma: no cover
    ee = None
    _ee_import_error = exc

try:
    import geemap.foliumap as geemap
except Exception as exc:  # pragma: no cover
    geemap = None
    _geemap_import_error = exc


APP_TITLE = "空间智能驾驶舱"
# 确保这里是您的真实 Cloud Project 路径
DEFAULT_GEE_USER_PATH = "projects/aef-project-487710/assets/aef_demo"
DEFAULT_LOCAL_ASSET_PATH = "/mnt/data/hyf/oneearth/aef_demo"

EMBEDDING_COLLECTION = "GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL"
S2_COLLECTION = "COPERNICUS/S2_SR"
DEFAULT_BUFFER_METERS = 5000

MODE_CONFIG = {
    "地表 DNA": {
        "suffix": "dna",
        "date_start": "2024-01-01",
        "date_end": "2024-12-31",
        "vis": {"min": -0.1, "max": 0.1, "gamma": 1.6},
    },
    "变化雷达": {
        "suffix": "change",
        "date_start_old": "2019-01-01",
        "date_end_old": "2019-12-31",
        "date_start_new": "2024-01-01",
        "date_end_new": "2024-12-31",
        "threshold": 0.06,
        "vis": {"min": 0.06, "max": 0.35, "palette": ["000000", "FF0000", "FFFF00", "FFFFFF"]},
    },
    "建设强度": {
        "suffix": "intensity",
        "date_start": "2024-01-01",
        "date_end": "2024-12-31",
        "threshold": 0.15,
        "scale_min": -0.12,
        "scale_max": 0.12,
        "vis": {"min": 0.15, "max": 0.65, "palette": ["000000", "BC13FE", "00F5FF", "FFFFFF"]},
    },
    "生态韧性": {
        "suffix": "eco",
        "date_start": "2024-01-01",
        "date_end": "2024-12-31",
        "threshold": -0.15,
        "vis": {"min": -0.15, "max": 0.15, "palette": ["000000", "004400", "00FF00", "CCFF00"]},
    },
}


def _set_theme() -> None:
    st.set_page_config(
        layout="wide",
        page_title="ALPHA EARTH COMMAND",
        initial_sidebar_state="expanded",
    )

    # v5 指挥舱样式
    st.markdown(
        """
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    /* 保留 header，避免侧栏关闭后无法重新打开 */
    header {visibility: visible;}

    .block-container { padding: 0 !important; margin: 0 !important; }
    .main .block-container { padding-top: 0 !important; }

    .stApp { background-color: #000000; }
    section[data-testid="stSidebar"] { background-color: #0b0f13; }
    h1, h2, h3, h4, p, span, label { color: #EDEDED; }

    .status-badge {
        padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;
    }
    .status-live { background: #FF4444; color: white; }
    .status-cached { background: #00AA00; color: white; }
    .status-warn { background: #C17A00; color: white; }

    /* 新增：呼吸灯动画定义 */
    @keyframes pulse-red {
        0% { box-shadow: 0 0 0 0 rgba(255, 68, 68, 0.7); }
        70% { box-shadow: 0 0 0 10px rgba(255, 68, 68, 0); }
        100% { box-shadow: 0 0 0 0 rgba(255, 68, 68, 0); }
    }

    /* 修改 status-live 样式，加入动画 */
    .status-live { 
        background: #FF4444; 
        color: white; 
        animation: pulse-red 2s infinite; /* 让它动起来 */
        box-shadow: 0 0 5px #FF4444;
    }

    /* 地图铺满屏幕 */
    iframe { height: 100vh !important; width: 100% !important; }
    
    /* 放大 Leaflet 图层控制按钮 */
    .leaflet-control-layers {
        font-size: 16px !important;
    }
    .leaflet-control-layers-toggle {
        width: 44px !important;
        height: 44px !important;
        background-size: 28px 28px !important;
    }
    .leaflet-control-layers label {
        font-size: 14px !important;
        padding: 8px !important;
    }
    .leaflet-control-layers input[type="checkbox"] {
        width: 18px !important;
        height: 18px !important;
        margin-right: 8px !important;
    }
</style>
        """,
        unsafe_allow_html=True,
    )


def _init_gee() -> Tuple[bool, Optional[str]]:
    if ee is None:
        return False, f"earthengine-api import 失败：{_ee_import_error}"

    # Option A: Use a service account (recommended for server deployments)
    service_account = os.environ.get("EE_SERVICE_ACCOUNT")
    private_key_file = os.environ.get("EE_PRIVATE_KEY_FILE")
    if service_account and private_key_file:
        try:
            credentials = ee.ServiceAccountCredentials(service_account, private_key_file)
            ee.Initialize(credentials)
            return True, None
        except Exception as exc:
            return False, (
                "检测到服务账号环境变量，但初始化失败。\n"
                "请检查 `EE_SERVICE_ACCOUNT` 与 `EE_PRIVATE_KEY_FILE` 是否正确、JSON key 是否可读。\n\n"
                f"详细错误：{exc}"
            )

    # Option B: Use local user credentials created by earthengine authenticate
    try:
        ee.Initialize()
        return True, None
    except Exception as exc:
        return False, (
            "GEE 未认证或初始化失败。\n\n"
            "方式 A（交互式授权，一次性，推荐先排障）：\n"
            "1) 在 ECS 终端执行（必须用运行服务的同一用户：alphaearth）：\n"
            "   - `sudo -u alphaearth -H /opt/oneearth/.venv/bin/earthengine authenticate --quiet --auth_mode=notebook --force`\n"
            "2) 按提示在本地浏览器完成授权并回填验证码\n"
            "3) 重启服务：`sudo systemctl restart alphaearth`\n\n"
            "方式 B（服务账号，适合生产常驻）：\n"
            "- 在 `/etc/alphaearth/alphaearth.env` 设置：\n"
            "  - `EE_SERVICE_ACCOUNT=xxx@yyy.iam.gserviceaccount.com`\n"
            "  - `EE_PRIVATE_KEY_FILE=/etc/alphaearth/service-account-key.json`\n"
            "- 确保 key 文件对 alphaearth 可读：`chown alphaearth:alphaearth /etc/alphaearth/service-account-key.json && chmod 600 /etc/alphaearth/service-account-key.json`\n"
            "- 然后重启服务：`sudo systemctl restart alphaearth`\n\n"
            f"详细错误：{exc}"
        )


def _get_gee_user_path() -> str:
    # 1. 最高优先级：如果代码硬编码了 Cloud Path (projects/ or users/)，直接使用
    # 无视环境变量里的本地路径干扰
    if DEFAULT_GEE_USER_PATH and not DEFAULT_GEE_USER_PATH.startswith("/"):
        return DEFAULT_GEE_USER_PATH

    # 2. 只有在硬编码未设置时，才读取环境变量
    env_path = os.environ.get("GEE_USER_PATH", "").strip()
    
    # 强制修正逻辑：如果环境变量是本地路径，但我们其实想要 Cloud 模式...
    # 这里直接返回硬编码备选，或者让用户必须在 secrets 里设
    if env_path and not env_path.startswith("/"):
        return env_path.rstrip("/")

    # 3. 尝试读取 Secrets
    try:
        secrets_path = str(st.secrets.get("GEE_USER_PATH", "")).strip()
        if secrets_path and not secrets_path.startswith("/"):
            return secrets_path.rstrip("/")
    except Exception:
        pass

    # 4. 如果所有 Cloud Path 都没有，最后才回退到 Local Sticky Path
    if env_path: return env_path.rstrip("/")
    
    return DEFAULT_GEE_USER_PATH


def _match_mode_key(mode: str) -> str:
    for key in MODE_CONFIG:
        if key in mode:
            return key
    return "地表 DNA"


def _validate_gee_user_path(path: str) -> tuple[bool, str]:
    value = (path or "").strip().rstrip("/")
    if not value:
        return False, "`GEE_USER_PATH` 不能为空。"
    if value.startswith("/"):
        return True, "检测到本地路径模式（仅实时计算，不启用 GEE Asset 缓存）"
    
    # 允许 projects/ 开头的路径
    if not (value.startswith("users/") or value.startswith("projects/")):
        return False, "`GEE_USER_PATH` 需以 `users/` 或 `projects/` 开头。"
    if " " in value:
        return False, "`GEE_USER_PATH` 不能包含空格。"
    if len([p for p in value.split("/") if p]) < 2: # projects/my-project 至少有2段
        return False, "路径格式不正确，建议形如 `projects/<project-id>/assets/<folder>`"
    return True, "路径格式有效"


def _classify_ee_error(exc: Exception) -> str:
    message = str(exc).lower()
    if any(k in message for k in ["not found", "asset not found", "cannot find", "does not exist"]):
        return "not_found"
    if any(
        k in message
        for k in ["permission", "forbidden", "not authorized", "access denied", "insufficient"]
    ):
        return "permission"
    if any(
        k in message
        for k in ["timed out", "deadline", "network", "connection", "temporarily unavailable"]
    ):
        return "transient"
    return "unknown"


def _check_asset_root_access(gee_user_path: str) -> tuple[bool, str]:
    if gee_user_path.startswith("/"):
        return True, "本地路径模式：跳过 GEE Asset 根目录检查"
    try:
        # 使用 listAssets 检查更稳健，但对于 project root 可能需要不同权限
        # 这里尝试列出根目录内容
        ee.data.listAssets({'parent': gee_user_path}) 
        return True, "Asset 根目录可访问"
    except Exception as exc:
        err_type = _classify_ee_error(exc)
        if err_type == "not_found":
            return False, "Asset 根目录不存在，请先在 GEE Assets 创建目录"
        if err_type == "permission":
            return False, "Asset 根目录权限不足，请检查 Earth Engine 授权"
        return False, f"Asset 根目录检查失败：{exc}"


def _check_dataset_access() -> tuple[bool, str]:
    try:
        size = (
            ee.ImageCollection(EMBEDDING_COLLECTION)
            .filterDate("2024-01-01", "2024-12-31")
            .limit(1)
            .size()
            .getInfo()
        )
        if int(size) > 0:
            return True, "AEF 数据集可访问"
        return False, "AEF 数据集返回为空"
    except Exception as exc:
        return False, f"AEF 数据集不可访问：{exc}"


def _check_asset_cache_state(asset_id: str) -> tuple[bool, str]:
    if asset_id.startswith("/"):
        return True, "本地路径模式：不检查 GEE Asset 缓存"
    try:
        ee.data.getAsset(asset_id)
        return True, "当前场景缓存已存在"
    except Exception as exc:
        err_type = _classify_ee_error(exc)
        if err_type == "not_found":
            return False, "当前场景缓存不存在（可点击缓存按钮预热）"
        if err_type == "permission":
            return False, "当前场景缓存检查失败（权限不足）"
        return False, f"当前场景缓存检查异常：{exc}"


def _run_preflight_checks(gee_user_path: str, current_asset_id: str) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []

    checks.append({"name": "GEE 初始化", "ok": ee is not None, "detail": "Earth Engine 模块已加载" if ee else "Earth Engine 模块不可用"})

    path_ok, path_msg = _validate_gee_user_path(gee_user_path)
    checks.append({"name": "GEE_USER_PATH 格式", "ok": path_ok, "detail": path_msg})

    if path_ok:
        root_ok, root_msg = _check_asset_root_access(gee_user_path)
        checks.append({"name": "Asset 根目录访问", "ok": root_ok, "detail": root_msg})

    ds_ok, ds_msg = _check_dataset_access()
    checks.append({"name": "AEF 数据集访问", "ok": ds_ok, "detail": ds_msg})

    cache_ok, cache_msg = _check_asset_cache_state(current_asset_id)
    checks.append({"name": "当前场景缓存状态", "ok": cache_ok, "detail": cache_msg})

    return checks


def _ensure_runtime_state() -> None:
    if "cache_tasks" not in st.session_state:
        st.session_state["cache_tasks"] = []
    if "stats_total_requests" not in st.session_state:
        st.session_state["stats_total_requests"] = 0
    if "stats_cache_hits" not in st.session_state:
        st.session_state["stats_cache_hits"] = 0
    if "stats_cache_miss" not in st.session_state:
        st.session_state["stats_cache_miss"] = 0
    if "stats_last_load_ms" not in st.session_state:
        st.session_state["stats_last_load_ms"] = 0.0
    if "stats_avg_load_ms" not in st.session_state:
        st.session_state["stats_avg_load_ms"] = 0.0
    if "stats_route_reason" not in st.session_state:
        st.session_state["stats_route_reason"] = ""
    if "preflight_enabled" not in st.session_state:
        st.session_state["preflight_enabled"] = False


def _record_load_metric(is_cached: bool, load_ms: float, route_reason: str) -> None:
    _ensure_runtime_state()
    st.session_state["stats_total_requests"] += 1
    if is_cached:
        st.session_state["stats_cache_hits"] += 1
    else:
        st.session_state["stats_cache_miss"] += 1

    total = float(st.session_state["stats_total_requests"])
    old_avg = float(st.session_state["stats_avg_load_ms"])
    st.session_state["stats_avg_load_ms"] = ((old_avg * (total - 1.0)) + float(load_ms)) / total
    st.session_state["stats_last_load_ms"] = float(load_ms)
    st.session_state["stats_route_reason"] = route_reason


def _render_metrics_panel() -> None:
    _ensure_runtime_state()
    with st.sidebar.expander("📊 运行指标", expanded=False):
        total = int(st.session_state["stats_total_requests"])
        hits = int(st.session_state["stats_cache_hits"])
        miss = int(st.session_state["stats_cache_miss"])
        hit_rate = (hits / total * 100.0) if total > 0 else 0.0

        st.caption(f"请求总数：{total}")
        st.caption(f"缓存命中：{hits} | 实时回退：{miss} | 命中率：{hit_rate:.1f}%")
        st.caption(f"本次加载：{st.session_state['stats_last_load_ms']:.1f} ms")
        st.caption(f"会话平均：{st.session_state['stats_avg_load_ms']:.1f} ms")
        if st.session_state["stats_route_reason"]:
            st.caption(f"最近分流原因：{st.session_state['stats_route_reason']}")


def _render_layer_health_panel(
    mode: str,
    compare_mode: str,
    s2_ok: bool,
    ai_ok: bool,
    map_ok: bool,
    detail: str,
) -> None:
    with st.sidebar.expander("🩺 图层健康", expanded=True):
        st.write(f"场景：**{_match_mode_key(mode)}**")
        st.caption(f"显示方式：{compare_mode}")

        st.write(f"{'✅' if s2_ok else '❌'} 2024 真实地表(光学)")
        st.write(f"{'✅' if ai_ok else '❌'} AI 图层")
        st.write(f"{'✅' if map_ok else '❌'} 地图渲染")

        if detail:
            st.caption(f"说明：{detail}")


def _render_preflight_panel(gee_user_path: str, current_asset_id: str) -> None:
    _ensure_runtime_state()
    with st.sidebar.expander("✅ 演示前检查", expanded=False):
        if st.button("运行检查", key="btn_preflight_run"):
            st.session_state["preflight_enabled"] = True
        if st.button("清空检查", key="btn_preflight_clear"):
            st.session_state["preflight_enabled"] = False

        if not st.session_state.get("preflight_enabled", False):
            st.caption("点击“运行检查”可验证当前演示环境")
            return

        checks = _run_preflight_checks(gee_user_path, current_asset_id)
        for item in checks:
            icon = "✅" if bool(item["ok"]) else "❌"
            st.write(f"{icon} {item['name']}")
            st.caption(str(item["detail"]))


def _apply_demo_preset():
    """Callback function for the demo preset button to avoid widget state conflicts."""
    st.session_state["ui_compare_mode"] = "分屏对比"
    st.session_state["ui_ai_opacity"] = 0.95
    st.session_state["ai_force_full"] = False
    st.session_state["th_change"] = 0.08
    st.session_state["th_intensity"] = 0.18
    st.session_state["th_eco"] = -0.15
    # Use st.toast if available for feedback without disrupting layout
    if hasattr(st, "toast"):
        st.toast("已应用演示预设 (分屏与智能掩膜)", icon="🎬")


def _sidebar_controls() -> tuple[str, str, dict, float, float, int, str, str, bool]:
    with st.sidebar:
        st.title("🎛️ 空间智能驾驶舱")
        st.markdown("---")

        # === 优先级 1: 监测场景 ===
        mode = st.radio(
            "🎯 监测场景",
            [
                "地表 DNA (语义视图)",
                "变化雷达 (敏捷治理)",
                "建设强度 (宏观管控)",
                "生态韧性 (绿色底线)",
            ],
        )

        st.markdown("---")

        # === 优先级 2: 核心监测区 ===
        locations = {
            "北京 · 通州": {"coords": [39.9042, 116.7000, 13], "code": "beijing"},
            "河北 · 雄安": {"coords": [39.0500, 115.9800, 12], "code": "xiongan"},
            "杭州 · 西湖": {"coords": [30.2450, 120.1400, 14], "code": "hangzhou"},
            "深圳 · 湾区": {"coords": [22.5000, 113.9500, 13], "code": "shenzhen"},
            "美国 · 纽约": {"coords": [40.7580, -73.9855, 13], "code": "nyc"},
        }

        loc_name = st.selectbox("🗺️ 核心监测区", list(locations.keys()))
        loc_data = locations[loc_name]
        lat, lon, zoom = loc_data["coords"]

        st.markdown("---")

        # === 优先级 3: 场景解释（整合 MODE_CONFIG）===
        mode_key = _match_mode_key(mode)
        scene_info = _build_scene_info(mode)
        
        with st.expander("📘 场景解释", expanded=True):
            st.markdown(f"### {scene_info['title']}")
            st.write(scene_info['desc'])
            
            st.markdown(scene_info['algorithm'])
            st.markdown(scene_info['color_meaning'])
            st.markdown(scene_info['usage'])
            
            st.code(scene_info['formula'], language="python")
            
            # 显示调色板
            if 'palette' in scene_info:
                palette_html = " ".join([f"<span style='display:inline-block;width:20px;height:20px;background:{c};border:1px solid #666;margin:2px'></span>" for c in scene_info['palette']])
                st.markdown(f"**调色板**：{palette_html}", unsafe_allow_html=True)

        st.markdown("---")

        # === 优先级 4: 一键演示预设 & 调试模式 ===
        col1, col2 = st.columns(2)
        with col1:
            st.button("🎬 一键演示模式", key="btn_demo_preset", on_click=_apply_demo_preset)
        with col2:
            debug_mode = st.checkbox("🛠️ 调试", value=False, key="chk_debug_mode_top")

        st.markdown("---")
        
        # === 优先级 5: 管理员：全量缓存预热 ===
        with st.expander("🔥 管理员：批量预热", expanded=False):
            st.caption("⚙️ 一键预热所有场景（5城市 × 4模式 = 20个）")
            st.caption("🕒 预计时间：10-15分钟（后台运行）")
            
            if st.button("🚀 开始全量预热", key="btn_batch_preheat"):
                # 获取当前的 GEE 用户路径
                current_path = _get_gee_user_path()
                effective_path = _resolve_effective_gee_user_path(
                    current_path, 
                    st.session_state.get("asset_path_override", "")
                )
                
                with st.spinner("🔄 批量提交中..."):
                    success, total = _batch_export_all(effective_path)
                
                if success > 0:
                    st.toast(f"✅ 已提交 {success}/{total} 个任务！", icon="🎉")
                    st.success(f"✅ 成功提交 {success}/{total} 个预热任务")
                    st.info("📍 请在“🛫️ 缓存任务状态”面板查看进度")
                    if hasattr(st, "rerun"):
                        st.rerun()
                else:
                    st.warning("⚠️ 未提交任何任务（可能全部已缓存或路径不支持）")

        st.markdown("---")

        # 移除这里的显式初始化和可能的重复设置，完全交给 st.session_state.get 和 widget 的 key 机制
        # 如果 key not in session_state, widget 会使用 value 参数（如果提供了）
        # 这里为了确保第一次加载有默认值，我们使用 setdefault
        
        st.session_state.setdefault("ui_compare_mode", "分屏对比")
        st.session_state.setdefault("ui_ai_opacity", 0.95)
        st.session_state.setdefault("ai_force_full", False)
        st.session_state.setdefault("th_change", 0.08)
        st.session_state.setdefault("th_intensity", 0.18)
        st.session_state.setdefault("th_eco", -0.15)

        compare_mode = st.radio("显示方式", ["叠加图层", "分屏对比"], horizontal=True, key="ui_compare_mode")
        st.slider("AI 图层透明度", min_value=0.35, max_value=1.0, step=0.05, key="ui_ai_opacity")
        st.checkbox("AI 可见性增强（取消掩膜）", key="ai_force_full")

        # 场景阈值
        st.slider("变化雷达阈值", min_value=0.02, max_value=0.25, step=0.01, key="th_change")
        st.slider("建设强度阈值", min_value=0.05, max_value=0.50, step=0.01, key="th_intensity")
        st.slider("生态韧性阈值", min_value=-0.30, max_value=0.10, step=0.01, key="th_eco")

        # 修复：默认值不再读取环境变量，而是使用硬编码的 Cloud Path，引导用户使用正确路径
        # 只有在明确需要 Local Path 时才让用户自己去改环境变量
        default_override = str(st.session_state.get("asset_path_override", DEFAULT_GEE_USER_PATH))

        asset_path_override = st.text_input(
            "GEE Asset 路径（可选）",
            value=default_override,
            placeholder="users/<username>/aef_demo 或 projects/<id>/assets/...",
            help="输入 projects/ 或 users/ 开头的路径以启用云端缓存。",
            autocomplete="on",
        ).strip()
        st.session_state["asset_path_override"] = asset_path_override

    # debug_mode 已在高级参数中定义
    debug_mode = st.session_state.get("chk_debug_mode_top", False)
    return mode, loc_name, loc_data, float(lat), float(lon), int(zoom), compare_mode, asset_path_override, debug_mode


def _render_debug_panel(image, vis_params, region):
    """
    渲染调试面板：静态缩略图 + 像素统计
    """
    st.markdown("---")
    st.subheader("🛠️ 调试诊断面板")

    col1, col2 = st.columns(2)

    with col1:
        st.caption("📷 静态缩略图 (Direct GEE Request)")
        try:
            # 准备缩略图参数，移除不被 getThumbURL 支持的参数
            thumb_vis = {k: v for k, v in vis_params.items() if k in ['min', 'max', 'palette', 'gamma', 'opacity']}
            thumb_params = {
                'region': region,
                'dimensions': 512,
                'format': 'png'
            }
            thumb_params.update(thumb_vis)
            
            url = image.getThumbURL(thumb_params)
            st.image(url, caption="GEE 静态渲染结果", width="stretch")
            st.success("静态图生成成功：说明 GEE 计算正常，可能是前端地图组件遮挡。")
        except Exception as e:
            st.error(f"静态图生成失败：{e}")
            st.warning("说明数据本身有问题，请检查 Asset 权限或计算逻辑。")

    with col2:
        st.caption("📊 区域像素统计 (Region Statistics)")
        try:
            # 计算区域统计
            stats = image.reduceRegion(
                reducer=ee.Reducer.mean().combine(
                    reducer2=ee.Reducer.minMax(),
                    sharedInputs=True
                ),
                geometry=region,
                scale=100,  # 使用较大 scale 加速统计
                bestEffort=True,
                maxPixels=1e9
            ).getInfo()

            st.json(stats)
            
            # 简单的智能诊断
            vals = list(stats.values())
            if not vals or all(v is None for v in vals):
                st.error("统计结果为空：该区域无有效数据 (Masked/NoData)。")
            else:
                img_min = min([v for v in vals if v is not None])
                img_max = max([v for v in vals if v is not None])
                st.info(f"数据范围: [{img_min:.4f}, {img_max:.4f}]")
                
                vis_min = vis_params.get('min', 0)
                vis_max = vis_params.get('max', 1)
                
                if img_max < vis_min or img_min > vis_max:
                    st.warning(f"⚠️ 可视化范围 [{vis_min}, {vis_max}] 与数据范围不匹配，可能导致图层全黑或全白。")
                else:
                    st.success("数据范围在可视化范围内。")

        except Exception as e:
            st.error(f"统计计算失败：{e}")


def _resolve_effective_gee_user_path(base_path: str, override_path: str) -> str:
    override = (override_path or "").strip().rstrip("/")
    # 修复：允许 users/ 和 projects/ 开头的路径作为覆盖
    if override.startswith("users/") or override.startswith("projects/"):
        return override
    # 如果 override 是空或者不合法，回退到 base_path
    return (base_path or "").strip().rstrip("/")


def get_layer_logic(mode: str, region):
    """返回场景计算结果、可视化参数与缓存后缀。"""
    emb_col = ee.ImageCollection(EMBEDDING_COLLECTION)
    mode_key = _match_mode_key(mode)
    cfg = MODE_CONFIG[mode_key]

    def _get_flattened_image(col, date_start, date_end, bounds):
        """辅助函数：获取、排序、展平图像"""
        # 增加对空集合的检查
        filtered = col.filterBounds(bounds).filterDate(date_start, date_end)
        
        # 如果集合为空，尝试回退到更早的时间 (2022-2025)
        # 注意：size().getInfo() 是客户端调用，会阻塞，但为了保证数据不为空是值得的。
        try:
            count = filtered.limit(1).size().getInfo()
        except:
            count = 0
            
        if int(count) == 0:
            filtered = col.filterBounds(bounds).filterDate("2019-01-01", "2025-12-31")
            
        # 使用 mosaic() 拼接，确保覆盖区域
        # 并按照 system:time_start 倒序排序，让最新的 tile 在上层
        # mosaic 本身不保证顺序，通常是 based on image collection order.
        # sort('system:time_start', False) may help if we use reduce(ee.Reducer.first()) instead.
        # Mosaic operates on the whole collection. To get latest pixels, we should sort by time.
        # But for Annual embedding, usually non-overlapping tiles for one year.
        
        raw_img = filtered.sort("system:time_start", False).mosaic()
        
        # 关键修正：处理多波段图像
        # 错误提示 "Found 64 bands" 表明该数据集已经是多波段。
        # 因此，我们需要直接使用这些波段，而不是 arrayFlatten。
        # 为了兼容后续代码，我们强制重命名波段为 "b0" 到 "b63"（GEE 要求以字母开头）。
        
        # 使用 ee.Algorithms.If 来避免 bandNames() 对空图像报错
        # 但既然我们前面已经尽力保证 filtered 不为空...
        
        bands = raw_img.bandNames().slice(0, 64)
        target = ee.List([f"b{i}" for i in range(64)])
        return raw_img.select(bands, target)

    if mode_key == "地表 DNA":
        # 扩大时间范围至 2023-2025，确保能取到数据 (以防 2024 还没发布)
        # 优先用 2024 (cfg中定义)，如果空则可能是 filter 问题。
        # 如果 2024 确实没数据，用户会看到空。
        # 这里为了稳健，我们硬编码扩大搜索范围到 2023-01-01 至 2024-12-31
        
        img = _get_flattened_image(emb_col, "2023-01-01", "2025-01-01", region)
        
        # 选择前3个波段 (使用 b0, b1, b2)
        img = img.select(["b0", "b1", "b2"])
        vis = cfg["vis"]
        suffix = cfg["suffix"]

    elif mode_key == "变化雷达":
        # 2019
        img19 = _get_flattened_image(emb_col, cfg["date_start_old"], cfg["date_end_old"], region)
        # 2024 (扩大范围到 2023-2025 以防缺数)
        img24 = _get_flattened_image(emb_col, "2023-01-01", "2025-01-01", region)
        
        # 欧氏距离：sqrt(sum((a-b)^2))
        diff = img19.subtract(img24)
        dist = diff.pow(2).reduce(ee.Reducer.sum()).sqrt()
        
        th = float(st.session_state.get("th_change", float(cfg["threshold"])))
        mask = dist.gt(th)
        
        if not bool(st.session_state.get("ai_force_full", False)):
            dist = dist.updateMask(mask)
            
        img = dist
        vis = dict(cfg["vis"])
        vis["min"] = th
        suffix = cfg["suffix"]

    elif mode_key == "建设强度":
        # 扩大范围
        img_all = _get_flattened_image(emb_col, "2023-01-01", "2025-01-01", region)
        # select "b0" (修复：原来是 "0")
        val = img_all.select(["b0"])
        # 归一化
        norm = val.unitScale(float(cfg["scale_min"]), float(cfg["scale_max"])).clamp(0, 1)
        
        th = float(st.session_state.get("th_intensity", float(cfg["threshold"])))
        if not bool(st.session_state.get("ai_force_full", False)):
            norm = norm.updateMask(norm.gt(th))
            
        img = norm
        vis = dict(cfg["vis"])
        vis["min"] = th
        suffix = cfg["suffix"]

    else:
        # 生态韧性
        img_all = _get_flattened_image(emb_col, "2023-01-01", "2025-01-01", region)
        # select "b2" & invert (修复：原来是 "2")
        val = img_all.select(["b2"]).multiply(-1)
        
        th = float(st.session_state.get("th_eco", float(cfg["threshold"])))
        if not bool(st.session_state.get("ai_force_full", False)):
            val = val.updateMask(val.gt(th))
            
        img = val
        vis = dict(cfg["vis"])
        vis["min"] = th
        suffix = cfg["suffix"]

    # 修复：圆形裁剪问题
    # 策略更新：不再对 AI 图层进行裁剪，使其像 S2 光学影像一样铺满可视区域或瓦片。
    # 这样用户拖动地图时也能看到周边数据的加载（只要有数据覆盖）。
    return img, vis, suffix


def smart_load(mode: str, region, loc_code: str, gee_user_path: str):
    """智能加载：先查缓存 Asset，未命中再实时计算。"""
    computed_img, vis_params, suffix = get_layer_logic(mode, region)
    
    # 移除末尾斜杠并拼接 Asset ID
    asset_id = f"{gee_user_path.rstrip('/')}/{loc_code}_{suffix}"

    status_html = ""
    final_layer = None
    is_cached = False
    route_reason = ""

    if gee_user_path.startswith("/"):
        final_layer = computed_img
        status_html = "<span class='status-badge status-live'>⚡ 实时计算 (Local Path)</span>"
        return final_layer, vis_params, status_html, False, asset_id, computed_img, suffix, "asset_disabled_local_path"

    try:
        ee.data.getAsset(asset_id)
        final_layer = ee.Image(asset_id)
        status_html = "<span class='status-badge status-cached'>🚀 极速缓存 (Asset)</span>"
        is_cached = True
        route_reason = "asset_hit"
    except Exception as exc:
        err_type = _classify_ee_error(exc)
        final_layer = computed_img
        if err_type == "not_found":
            status_html = "<span class='status-badge status-live'>⚡ 实时计算 (Cloud)</span>"
            route_reason = "asset_miss"
        else:
            status_html = "<span class='status-badge status-warn'>⚠️ 实时计算 (Asset检查异常)</span>"
            route_reason = f"asset_check_{err_type}"
        is_cached = False

    return final_layer, vis_params, status_html, is_cached, asset_id, computed_img, suffix, route_reason


def trigger_export(image, description: str, asset_id: str, region):
    """触发 GEE 后台导出任务。"""
    task = ee.batch.Export.image.toAsset(
        image=image,
        description=description,
        assetId=asset_id,
        region=region,
        scale=10,
        maxPixels=1e9,
    )
    task.start()
    return task.id


def _batch_export_all(gee_user_path: str) -> tuple[int, int]:
    """
    批量预热所有场景（ 5城市 × 4模式 = 20个）。
    返回: (success_count, total_count)
    """
    if gee_user_path.startswith("/"):
        return 0, 0  # 本地路径模式不支持
    
    # 所有城市配置
    all_locations = {
        "beijing": {"coords": [39.9042, 116.7000], "name": "北京·通州"},
        "xiongan": {"coords": [39.0500, 115.9800], "name": "河北·雄安"},
        "hangzhou": {"coords": [30.2450, 120.1400], "name": "杭州·西湖"},
        "shenzhen": {"coords": [22.5000, 113.9500], "name": "深圳·湾区"},
        "nyc": {"coords": [40.7580, -73.9855], "name": "美国·纽约"},
    }
    
    success_count = 0
    total_count = 0
    
    for loc_code, loc_data in all_locations.items():
        lat, lon = loc_data["coords"]
        viewport = ee.Geometry.Point([lon, lat]).buffer(DEFAULT_BUFFER_METERS)
        
        for mode_key, mode_cfg in MODE_CONFIG.items():
            total_count += 1
            suffix = mode_cfg["suffix"]
            
            try:
                # 检查是否已存在
                asset_id = f"{gee_user_path.rstrip('/')}/{loc_code}_{suffix}"
                try:
                    ee.data.getAsset(asset_id)
                    # 已存在，跳过
                    continue
                except:
                    pass  # 不存在，继续导出
                
                # 计算图层
                raw_img, _, _ = get_layer_logic(mode_key, viewport)
                
                # 提交导出任务
                description = f"Cache_{loc_code}_{suffix}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
                task_id = trigger_export(raw_img, description, asset_id, viewport)
                
                # 记录任务
                _record_cache_task(task_id, description, asset_id, loc_code, mode_key)
                success_count += 1
                
            except Exception as exc:
                # 单个任务失败不影响其他
                st.warning(f"预热 {loc_data['name']} - {mode_key} 失败: {exc}")
                continue
    
    return success_count, total_count


def _record_cache_task(task_id: str, description: str, asset_id: str, loc_code: str, mode: str) -> None:
    _ensure_runtime_state()
    st.session_state["cache_tasks"].insert(
        0,
        {
            "task_id": task_id,
            "description": description,
            "asset_id": asset_id,
            "loc_code": loc_code,
            "mode": mode,
            "created_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        },
    )
    st.session_state["cache_tasks"] = st.session_state["cache_tasks"][:20]


def _list_live_cache_tasks(limit: int = 12) -> list[dict]:
    if ee is None:
        return []

    try:
        live = []
        for task in ee.batch.Task.list():
            status = task.status()
            desc = str(status.get("description", ""))
            if not desc.startswith("Cache_"):
                continue
            live.append(
                {
                    "task_id": str(status.get("id", "")) or getattr(task, "id", ""),
                    "description": desc,
                    "state": str(status.get("state", "UNKNOWN")),
                    "error_message": str(status.get("error_message", "")),
                }
            )
            if len(live) >= limit:
                break
        return live
    except Exception:
        return []


def _render_cache_task_panel(current_loc_code: str, current_mode: str, current_suffix: str) -> None:
    _ensure_runtime_state()
    with st.sidebar.expander("🛰️ 缓存任务状态", expanded=False):
        if st.button("刷新任务", key="btn_refresh_tasks"):
            try:
                st.rerun()
            except Exception:
                pass

        only_current = st.checkbox("仅看当前场景", value=True, key="task_filter_current")
        live_tasks = _list_live_cache_tasks(limit=12)
        local_tasks = st.session_state.get("cache_tasks", [])

        if only_current:
            token = f"Cache_{current_loc_code}_{current_suffix}"
            live_tasks = [x for x in live_tasks if token in str(x.get("description", ""))]
            local_tasks = [
                x
                for x in local_tasks
                if str(x.get("loc_code", "")) == current_loc_code and _match_mode_key(str(x.get("mode", ""))) == current_mode
            ]

        if not live_tasks and not local_tasks:
            st.caption("暂无缓存任务记录")
            return

        if live_tasks:
            st.caption("Earth Engine 实时任务")
            for item in live_tasks:
                st.write(f"• {item['state']} | {item['description']}")
                if item.get("task_id"):
                    st.caption(f"ID: {item['task_id']}")
                if item.get("error_message"):
                    st.caption(f"错误：{item['error_message']}")

        if local_tasks:
            st.caption("本次会话已提交")
            for item in local_tasks[:5]:
                st.write(f"• SUBMITTED | {item['description']}")
                st.caption(f"{item['created_at']} | {item['asset_id']}")


def _build_s2_layer(region):
    candidates = [
        ("COPERNICUS/S2_SR_HARMONIZED", 20),
        ("COPERNICUS/S2_SR_HARMONIZED", 80),
        ("COPERNICUS/S2_HARMONIZED", 80),
        (S2_COLLECTION, None),
    ]
    for dataset_id, cloud_th in candidates:
        col = ee.ImageCollection(dataset_id).filterBounds(region).filterDate("2024-01-01", "2024-12-31")
        if cloud_th is not None:
            col = col.filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", cloud_th))
        try:
            if int(col.size().getInfo()) > 0:
                return col.median().visualize(min=0, max=3000, bands=["B4", "B3", "B2"])
        except Exception:
            # 网络波动时继续尝试下一个候选
            continue

    # 最后回退，避免空返回
    return (
        ee.ImageCollection(S2_COLLECTION)
        .filterBounds(region)
        .filterDate("2024-01-01", "2024-12-31")
        .median()
        .visualize(min=0, max=3000, bands=["B4", "B3", "B2"])
    )


def _build_scene_info(mode: str) -> dict:
    """构建场景详细解释信息，包含颜色、算法、意义"""
    scene_info = {
        "地表 DNA": {
            "title": "🧬 地表 DNA 解析 (GeoDNA)",
            "desc": "基于自监督学习提取的全球地表语义特征。将 64 维语义向量的前 3 个主成分映射为 RGB 通道，相似地物呈现相似颜色，用于无监督地物分类与语义理解。",
            "algorithm": "**算法原理**：PCA 降维 + RGB 映射\n- 输入：64维语义向量 (Google Satellite Embedding)\n- 处理：提取前3个主成分 [Dim 0, Dim 1, Dim 2]\n- 输出：RGB = (R: Dim0, G: Dim1, B: Dim2)",
            "color_meaning": "**颜色含义**：\n- 🔴 红色区域：高人造强度（城市、道路）\n- 🟢 绿色区域：高植被活力（森林、农田）\n- 🔵 蓝色区域：水体、湿地\n- 🟡 黄色区域：混合地物（城郊、裸地）",
            "usage": "**应用价值**：快速识别地物类型，发现异常地块，辅助国土资源分类与管理。",
            "formula": "RGB = PCA(Embedding)[0:3]",
            "palette": ["#000000", "#FF0000", "#00FF00", "#0000FF"],
        },
        "变化雷达": {
            "title": "⚠️ 时空风险雷达 (Change Radar)",
            "desc": "计算 2019-2024 年地表语义向量的高维欧氏距离，识别本质变化区域（建设、拆除、植被消长等），排除季节性或光照噪声干扰。",
            "algorithm": "**算法原理**：高维语义距离度量\n- 基准态：2019 年 64 维向量 V₁\n- 当前态：2024 年 64 维向量 V₂\n- 距离：D = √(Σ(V₁ᵢ - V₂ᵢ)²)\n- 阈值过滤：仅显示 D > 0.06 的区域",
            "color_meaning": "**颜色含义**（热力图）：\n- ⚫ 黑色：无变化或微小波动 (D < 0.06)\n- 🔴 红色：中等变化 (0.06 < D < 0.2)\n- 🟡 黄色：显著变化 (0.2 < D < 0.35)\n- ⚪ 白色：剧烈变化 (D > 0.35)",
            "usage": "**应用价值**：敏捷识别违建、非法占地、生态破坏等高风险区域，实现精准执法。",
            "formula": "Distance = √(Σ(V₂₀₁₉ - V₂₀₂₄)²)",
            "palette": ["#000000", "#FF0000", "#FFFF00", "#FFFFFF"],
        },
        "建设强度": {
            "title": "🏗️ 建设强度场 (Urban Intensity)",
            "desc": "提取 Embedding 第 0 维度（对人造不透水面高度敏感），定量评估区域开发强度与城市化水平，用于宏观管控与城市扩张监测。",
            "algorithm": "**算法原理**：敏感维度提取 + 归一化\n- 特征：Embedding[0]（与建筑密度正相关）\n- 归一化：I = (V - Vₘᵢₙ) / (Vₘₐₓ - Vₘᵢₙ)\n- 范围：0（自然）→ 1（高度城市化）\n- 阈值：仅显示 I > 0.15 的区域",
            "color_meaning": "**颜色含义**（紫-青-白渐变）：\n- ⚫ 黑色：自然地表 (I < 0.15)\n- 🟣 紫色：低强度开发 (0.15 < I < 0.35)\n- 🔵 青色：中等强度 (0.35 < I < 0.5)\n- ⚪ 白色：高强度核心区 (I > 0.65)",
            "usage": "**应用价值**：监控城市蔓延，评估开发强度，辅助三线（生态/永久基本农田/城市边界）管控。",
            "formula": "Intensity = Normalize(Embedding[0])",
            "palette": ["#000000", "#BC13FE", "#00F5FF", "#FFFFFF"],
        },
        "生态韧性": {
            "title": "🌿 生态韧性底线 (Eco-Resilience)",
            "desc": "利用 Embedding 第 2 维度（与植被活力负相关），反演区域生态韧性与绿色基底质量，辅助生态红线监管。",
            "algorithm": "**算法原理**：反向维度映射\n- 特征：-Embedding[2]（植被越茂盛值越高）\n- 反演：R = -V₂ （取反使高值代表高韧性）\n- 阈值：仅显示 R > -0.15 的区域\n- 范围：-0.3（退化）→ 0.1（健康）",
            "color_meaning": "**颜色含义**（黑-绿渐变）：\n- ⚫ 黑色：生态脆弱区 (R < -0.15)\n- 🌲 深绿：低韧性 (-0.15 < R < -0.05)\n- 🌿 中绿：中等韧性 (-0.05 < R < 0.05)\n- 🟢 亮绿：高韧性生态屏障 (R > 0.05)",
            "usage": "**应用价值**：识别生态脆弱区，评估生态修复效果，守护生态红线与绿色基底。",
            "formula": "Resilience = -1 × Embedding[2]",
            "palette": ["#000000", "#004400", "#00FF00", "#CCFF00"],
        },
    }

    mode_key = _match_mode_key(mode)
    return scene_info.get(mode_key, scene_info["地表 DNA"])


def _add_ee_layer(
    m: folium.Map, image, vis_params: dict, name: str, opacity: float = 1.0
) -> None:
    """Add an Earth Engine image layer to a folium map."""
    if ee is None:
        raise RuntimeError("earthengine-api is not available")

    # getMapId returns a dict containing a TileFetcher with a url_format.
    map_id_dict = image.getMapId(vis_params)
    tile_url = map_id_dict["tile_fetcher"].url_format

    folium.raster_layers.TileLayer(
        tiles=tile_url,
        attr="Google Earth Engine",
        name=name,
        overlay=True,
        control=True,
        opacity=float(opacity),
    ).add_to(m)


def _create_map(lat: float, lon: float, zoom: int, s2_layer, layer_img, layer_vis, compare_mode: str):
    ai_opacity = float(st.session_state.get("ui_ai_opacity", 0.85))
    
    # 将 ee.Image 转换为可视化后的 RGB 图像 (Visualized Image)
    # 这样 geemap.split_map 可以直接使用它
    try:
        if isinstance(layer_img, ee.Image):
            # 注意：visualize 返回的是 RGB uint8 Image
            ai_rgb = layer_img.visualize(**layer_vis)
        else:
            ai_rgb = layer_img
    except Exception:
        ai_rgb = layer_img

    if geemap is not None:
        try:
            m = geemap.Map(center=[lat, lon], zoom=zoom, height="1200px", basemap="CartoDB.DarkMatter")
            
            # 使用 split_map 进行分屏对比
            if compare_mode == "分屏对比":
                m.split_map(
                    left_layer=s2_layer, 
                    right_layer=ai_rgb 
                )
                # left_label="2024 Optical", right_label="AI Layer" (param names differ by version)
                # 显式添加图例标签
                # m.add_legend(title="AI Layer", builtin_legend='NLCD') # 可选
            else:
                # 叠加模式
                m.add_layer(s2_layer, {'name': '2024 真实地表'}, "2024 真实地表 (光学)")
                m.add_layer(ai_rgb, {'name': 'AI Layer', 'opacity': ai_opacity}, "AI 图层")
            
            m.add_layer_control()
            return m
        except Exception as exc:
            # st.error(f"Geemap error: {exc}") # Debug
            pass 

    # Fallback to pure folium
    # 强制使用暗黑底图，确保 AI 图层可见
    m = folium.Map(
        location=[lat, lon],
        zoom_start=zoom,
        tiles="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
        attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        control_scale=True,
    )
    # 添加图层：使用已可视化的 ai_rgb
    _add_ee_layer(m, s2_layer, {}, "2024 真实地表 (光学)", opacity=0.8)
    _add_ee_layer(m, ai_rgb, {}, "AI 图层", opacity=ai_opacity)
    folium.LayerControl(collapsed=False).add_to(m)
    return m


def _render_map(m) -> None:
    if m is None:
        return
    
    # 使用稳定的时间戳进行刷新控制
    # 时间戳只在 main() 中状态变化时更新，避免无意义的重复刷新
    _ensure_runtime_state()
    if 'last_update_ts' not in st.session_state:
        st.session_state['last_update_ts'] = 0.0
    
    last_update = st.session_state.get('last_update_ts', 0.0)

    # 优先使用 geemap 的 Streamlit 集成
    if hasattr(m, "to_streamlit"):
        try:
            # geemap 的 to_streamlit 通常不支持 key 参数
            # 依赖 Streamlit 的自动重渲染机制
            m.to_streamlit(height=1200)
        except TypeError:
            m.to_streamlit(height=1200)
        return

    # 回退：使用 streamlit-folium
    try:
        from streamlit_folium import st_folium
        # 使用稳定的时间戳作为 key，只在状态变化时刷新
        map_key = f"folium_map_{last_update}"
        st_folium(m, height=1200, width=None, key=map_key)
    except Exception as exc:
        st.error(f"地图渲染失败：{exc}")


def main() -> None:
    _set_theme()

    current_path = _get_gee_user_path()
    if "your_username_here" in current_path:
        st.error("🚨 严重配置错误：未设置 GEE 用户路径")
        st.info("请修改 app.py 第 26 行的 `GEE_USER_PATH`，或设置环境变量 `GEE_USER_PATH`。")
        st.markdown("去 **Google Earth Engine Code Editor** 左上角 Assets 栏，复制你的根目录（例如 `users/zhangsan`）。")
        st.code('GEE_USER_PATH="users/你的用户名/aef_demo"')
        st.warning("系统已暂停运行，直到配置修正。")
        st.stop()

    _ensure_runtime_state()

    gee_ok, gee_msg = _init_gee()
    if not gee_ok:
        st.warning(gee_msg)
        st.stop()

    mode, loc_name, loc_data, lat, lon, zoom, compare_mode, asset_path_override, debug_mode = _sidebar_controls()
    
    # 检测场景或位置是否发生变化，以更新时间戳，触发地图刷新
    # 包含所有影响地图显示的关键参数
    ai_opacity = float(st.session_state.get("ui_ai_opacity", 0.85))
    state_key_str = f"{mode}_{loc_name}_{compare_mode}_{zoom}_{ai_opacity}"
    if st.session_state.get('last_state_str') != state_key_str:
        st.session_state['last_state_str'] = state_key_str
        st.session_state['last_update_ts'] = perf_counter()

    gee_user_path = _resolve_effective_gee_user_path(current_path, asset_path_override)

    path_ok, path_msg = _validate_gee_user_path(gee_user_path)
    if not path_ok:
        st.sidebar.error(f"⚠️ {path_msg}")
    elif current_path.startswith("/") and (gee_user_path.startswith("users/") or gee_user_path.startswith("projects/")):
        st.sidebar.success("✅ 已使用侧栏 GEE Asset 路径，缓存功能已启用。")

    mode_key = _match_mode_key(mode)
    # 场景解释已整合到侧边栏，不再单独渲染

    viewport = ee.Geometry.Point([lon, lat]).buffer(DEFAULT_BUFFER_METERS)

    load_start = perf_counter()

    # 使用 Spinner 提示用户正在加载
    with st.spinner(f"🧮 AI 计算中... {mode_key}"):
        try:
            (
                layer_img,
                layer_vis,
                status_msg,
                is_cached,
                asset_path,
                raw_img,
                suffix,
                route_reason,
            ) = smart_load(mode, viewport, loc_data["code"], gee_user_path)
        except Exception as exc:
            st.error(f"AI 图层计算失败：{exc}")
            _render_layer_health_panel(
                mode,
                compare_mode,
                s2_ok=False,
                ai_ok=False,
                map_ok=False,
                detail="AI 计算阶段失败，请检查 Earth Engine 授权与数据集访问。",
            )
            st.stop()
    ai_ok = layer_img is not None
    load_ms = (perf_counter() - load_start) * 1000.0
    _record_load_metric(is_cached=is_cached, load_ms=load_ms, route_reason=route_reason)
    
    # Toast 反馈：缓存命中
    if is_cached and hasattr(st, "toast"):
        st.toast(f"⚡ 极速加载 ({load_ms:.0f}ms)", icon="🚀")

    if route_reason in {"asset_check_permission", "asset_check_transient", "asset_check_unknown"}:
        st.sidebar.warning("缓存检查异常，已自动回退实时计算。请检查权限或网络。")
    if route_reason == "asset_disabled_local_path":
        st.sidebar.info("当前为本地路径模式：仅实时计算。")
        st.sidebar.caption("提示：`/mnt/...` 是服务器本地目录，不是 GEE 云端 Asset。")
        st.sidebar.caption("如需缓存，请填写 `users/<username>/aef_demo`。")

    s2_ok = True
    map_ok = True
    health_detail = ""

    try:
        s2_layer = _build_s2_layer(viewport)
    except Exception as exc:
        s2_ok = False
        s2_layer = None
        health_detail = f"光学底图加载失败：{exc}"

    # HUD 信息已整合到侧边栏，不再单独渲染
    _render_preflight_panel(gee_user_path, asset_path)
    _render_metrics_panel()
    _render_cache_task_panel(loc_data["code"], mode_key, suffix)

    if s2_ok and ai_ok:
        with st.spinner("🗺️ 地图渲染中..."):
            try:
                m = _create_map(lat, lon, zoom, s2_layer, layer_img, layer_vis, compare_mode)
                _render_map(m)
            except Exception as exc:
                map_ok = False
                st.error(f"地图创建失败：{exc}")
    else:
        map_ok = False
        st.error("关键图层缺失，无法渲染地图。请查看侧栏“图层健康”面板。")

    _render_layer_health_panel(mode, compare_mode, s2_ok=s2_ok, ai_ok=ai_ok, map_ok=map_ok, detail=health_detail)

    if debug_mode:
        if ai_ok:
            try:
                _render_debug_panel(layer_img, layer_vis, viewport)
            except Exception as e:
                st.error(f"调试面板渲染失败：{e}")
        else:
            st.error("AI 图层初始化失败，无法渲染调试面板。请检查日志。")

    # 修复导出按钮逻辑：支持 projects/ 和 users/ 路径
    if (not is_cached) and (gee_user_path.startswith("users/") or gee_user_path.startswith("projects/")):
        with st.sidebar:
            st.write("---")
            st.write("**🚀 性能优化**")
            if st.button("📥 为下次演示缓存结果 (后台导出)"):
                safe_mode = suffix
                description = (
                    f"Cache_{loc_data['code']}_{safe_mode}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
                )
                try:
                    task_id = trigger_export(raw_img, description, asset_path, viewport)
                    _record_cache_task(task_id, description, asset_path, loc_data["code"], mode)
                    
                    if hasattr(st, "toast"):
                        st.toast(f"任务已提交! ID: {task_id}", icon="🚀")
                    
                    if hasattr(st, "rerun"):
                        st.rerun()
                except Exception as exc:
                    st.error(f"缓存任务提交失败：{exc}")
    elif (not is_cached) and gee_user_path.startswith("/"):
        with st.sidebar:
            st.write("---")
            st.caption("本地路径模式下不支持导出到 GEE Asset。")


if __name__ == "__main__":
    main()
