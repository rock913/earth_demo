import os
from typing import Optional, Tuple

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


def _set_theme() -> None:
    st.set_page_config(
        layout="wide",
        page_title=APP_TITLE,
        initial_sidebar_state="expanded",
    )

    # 极简 App 体验：隐藏 Streamlit 默认菜单/页脚/页眉，并压缩默认 padding。
    st.markdown(
        """
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Reduce default paddings across Streamlit versions */
    .block-container { padding-top: 0.5rem; padding-bottom: 0.5rem; }

    /* Sidebar & dark background */
    .stApp { background: #0e1117; }
    section[data-testid="stSidebar"] { background-color: #262730; }
    h1, h2, h3, h4 { color: #ffffff; }

    /* 统一说明卡：黑底白字（精简风格） */
    .ae-note {
        background: #000000;
        color: #ffffff;
        border: 1px solid #ffffff;
        border-radius: 8px;
        padding: 10px 12px;
        margin: 8px 0 10px 0;
        line-height: 1.5;
        font-size: 0.95rem;
    }
    .ae-note b { color: #ffffff; }
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


def _sidebar_controls() -> tuple[str, float, float, int]:
    st.sidebar.title("🌍 空间智能驾驶舱")
    st.sidebar.markdown("---")

    mode = st.sidebar.radio(
        "治理场景选择",
        [
            "地表 DNA 语义视图 (认知统一)",
            "建设强度连续场 (宏观管控)",
            "时空变化风险雷达 (敏捷治理)",
            "生态韧性监测 (绿色底线)",
        ],
    )

    st.sidebar.markdown("---")

    locations = {
        "上海·陆家嘴 (超大城市)": {"lat": 31.2304, "lon": 121.4737, "zoom": 12},
        "杭州·西湖 (生态融合)": {"lat": 30.2500, "lon": 120.1400, "zoom": 13},
        "北京·通州 (城市副中心)": {"lat": 39.9000, "lon": 116.6500, "zoom": 12},
        "河北·雄安新区 (千年大计)": {"lat": 39.0300, "lon": 115.9500, "zoom": 11},
        "美国·纽约 (国际对标)": {"lat": 40.7300, "lon": -73.9900, "zoom": 12},
    }

    selected = st.sidebar.selectbox("快速导航", list(locations.keys()))
    loc = locations[selected]

    with st.sidebar.expander("微调坐标"):
        lat = st.number_input("纬度", value=float(loc["lat"]), format="%.4f")
        lon = st.number_input("经度", value=float(loc["lon"]), format="%.4f")
        zoom = int(st.slider("缩放", 4, 18, int(loc["zoom"])))

    return mode, float(lat), float(lon), zoom


def _pick_embedding_band_names(emb_image) -> tuple[str, str, str]:
    """Best-effort band name selection across dataset variants."""
    # Prefer numeric names if present (as in v3.0 docs), else A00-style.
    preferred = ("0", "1", "2")
    fallback = ("A00", "A01", "A02")
    try:
        names = emb_image.bandNames().getInfo()
        if isinstance(names, list) and len(names) >= 3:
            name_set = {str(n) for n in names}
            if all(p in name_set for p in preferred):
                return preferred
            if all(f in name_set for f in fallback):
                return fallback
            return str(names[0]), str(names[1]), str(names[2])
    except Exception:
        pass
    return fallback


def _render_mode_note(mode: str) -> None:
    if "地表 DNA" in mode:
        st.markdown(
            """
<div class="ae-note">
<b>图层说明｜地表 DNA 语义视图</b><br/>
含义：颜色相近代表地表功能相近（语义一致）。<br/>
解读：冷色常见于水体/湿地，绿色常见于植被/农田，紫蓝常见于城市建成区与工业区。<br/>
用途：跨区域统一认知底图，快速识别功能分区。
</div>
            """,
            unsafe_allow_html=True,
        )
    elif "建设强度" in mode:
        st.markdown(
            """
<div class="ae-note">
<b>图层说明｜建设强度连续场</b><br/>
含义：显示开发强度的连续梯度。<br/>
解读：白色最高、青紫中高、深蓝中低、黑色不显示（低于阈值）。<br/>
用途：识别高强度开发区与潜在低效用地。
</div>
            """,
            unsafe_allow_html=True,
        )
    elif "变化风险" in mode:
        st.markdown(
            """
<div class="ae-note">
<b>图层说明｜时空变化风险雷达</b><br/>
含义：2019-2024 语义差异强度（高维距离）。<br/>
解读：黄色为中等变化，红色为高风险变化；未显示区域表示变化不显著。<br/>
用途：主动发现耕地占用、工程扩张、生态扰动等风险点。
</div>
            """,
            unsafe_allow_html=True,
        )
    elif "生态韧性" in mode:
        st.markdown(
            """
<div class="ae-note">
<b>图层说明｜生态韧性监测</b><br/>
含义：反映生态活力与屏障完整性。<br/>
解读：深绿较高、浅绿中等、黑色较低。<br/>
用途：追踪生态修复效果与生态红线稳定性。
</div>
            """,
            unsafe_allow_html=True,
        )


def _add_sentinel2_layer(m, lat: float, lon: float) -> None:
    # v3.0: 使用 viewport buffer + median 合成，避免黑边/不重叠。
    # 增加多级回退，避免因单一数据集/云量阈值导致空图层。
    viewport = ee.Geometry.Point([lon, lat]).buffer(20000)

    candidates = [
        ("COPERNICUS/S2_SR_HARMONIZED", 20),
        ("COPERNICUS/S2_SR_HARMONIZED", 80),
        ("COPERNICUS/S2_HARMONIZED", 80),
        ("COPERNICUS/S2_HARMONIZED", None),
    ]

    chosen = None
    for dataset_id, cloud_threshold in candidates:
        col = (
            ee.ImageCollection(dataset_id)
            .filterBounds(viewport)
            .filterDate("2024-01-01", "2024-12-31")
        )
        if cloud_threshold is not None:
            col = col.filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", cloud_threshold))

        try:
            if int(col.size().getInfo()) > 0:
                chosen = col
                break
        except Exception:
            # 网络/权限受限时，直接采用当前候选继续尝试渲染。
            chosen = col
            break

    if chosen is None:
        st.warning("真实地表(光学)图层暂无可用影像。")
        return

    s2_mosaic = chosen.median()
    vis_s2 = {"min": 0, "max": 3000, "bands": ["B4", "B3", "B2"]}
    _add_ee_layer(m, s2_mosaic, vis_s2, "2024 真实地表 (光学)")


def _add_aef_layers(m, mode: str, lat: float, lon: float) -> None:
    # AEF Embedding 数据集
    emb_col = ee.ImageCollection("GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL")
    viewport = ee.Geometry.Point([lon, lat]).buffer(20000)

    semantic_opacity = st.sidebar.slider("语义/指数图层透明度", 0.0, 1.0, 0.85, 0.05)
    change_opacity = st.sidebar.slider("变化雷达透明度", 0.0, 1.0, 0.90, 0.05)

    if "地表 DNA" in mode:
        emb = emb_col.filterDate("2024-01-01", "2024-12-31").filterBounds(viewport).mosaic()
        b0, b1, b2 = _pick_embedding_band_names(emb)

        vis_params = {"bands": [b0, b1, b2], "min": -0.12, "max": 0.12, "gamma": 1.5}
        _add_ee_layer(m, emb, vis_params, "AI 语义底座", opacity=semantic_opacity)
        
        

    elif "建设强度" in mode:
        emb = emb_col.filterDate("2024-01-01", "2024-12-31").filterBounds(viewport).mosaic()
        b0, _, _ = _pick_embedding_band_names(emb)

        # v3.0 示例实现：将某一维特征 rescale 为 0..1 的连续场。
        built_up_index = emb.select(b0).unitScale(-0.12, 0.12).clamp(0, 1)

        vis_params = {
            "min": 0.4,
            "max": 0.7,
            "palette": ["000000", "blue", "purple", "cyan", "white"],
        }
        _add_ee_layer(
            m,
            built_up_index.updateMask(built_up_index.gt(0.4)),
            vis_params,
            "建设强度场",
            opacity=semantic_opacity,
        )
        
        

    elif "变化风险" in mode:
        emb19 = emb_col.filterDate("2019-01-01", "2019-12-31").filterBounds(viewport).mosaic()
        emb24 = emb_col.filterDate("2024-01-01", "2024-12-31").filterBounds(viewport).mosaic()

        diff = emb19.subtract(emb24).pow(2).reduce(ee.Reducer.sum()).sqrt()

        threshold = st.sidebar.slider("变化阈值（越小越敏感）", 0.05, 0.30, 0.18, 0.01)
        diff_masked = diff.updateMask(diff.gt(threshold))

        vis_change = {"min": threshold, "max": 0.4, "palette": ["yellow", "red"]}
        _add_ee_layer(m, diff_masked, vis_change, "变化热点 (2019-2024)", opacity=change_opacity)
        
        

    elif "生态韧性" in mode:
        emb = emb_col.filterDate("2024-01-01", "2024-12-31").filterBounds(viewport).mosaic()
        _, _, b2 = _pick_embedding_band_names(emb)

        eco_index = emb.select(b2).multiply(-1)
        vis_params = {"min": -0.1, "max": 0.1, "palette": ["black", "lightgreen", "darkgreen"]}
        _add_ee_layer(m, eco_index, vis_params, "生态本底", opacity=semantic_opacity)
        
        


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


def _create_map(mode: str, lat: float, lon: float, zoom: int):
    # Prefer a pure-folium implementation for robustness.
    # geemap.foliumap can break across dependency versions; folium tile layers are stable.
    m = folium.Map(location=[lat, lon], zoom_start=zoom, tiles=None, control_scale=True)

    # Dark basemap (CartoDB DarkMatter)
    folium.raster_layers.TileLayer(
        tiles="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
        attr="© OpenStreetMap contributors © CARTO",
        name="CartoDB.DarkMatter",
        overlay=False,
        control=True,
        max_zoom=20,
    ).add_to(m)

    # 永远先上真实影像做对照
    _add_sentinel2_layer(m, lat, lon)

    # AEF 图层（需要账号权限 + 数据集可见）
    try:
        _add_aef_layers(m, mode, lat, lon)
    except Exception as exc:
        st.warning(
            "AEF 图层加载失败（常见原因：未授权、数据集不可见、或网络受限）。\n\n"
            f"详细错误：{exc}"
        )

    folium.LayerControl(collapsed=False).add_to(m)

    return m


def _render_map(m) -> None:
    if m is None:
        return

    # 优先使用 geemap 的 Streamlit 集成
    if hasattr(m, "to_streamlit"):
        m.to_streamlit(height=800)
        return

    # 回退：使用 streamlit-folium
    try:
        from streamlit_folium import st_folium

        st_folium(m, height=800, width=None)
    except Exception as exc:
        st.error(f"地图渲染失败：{exc}")


def main() -> None:
    _set_theme()

    gee_ok, gee_msg = _init_gee()
    if not gee_ok:
        st.warning(gee_msg)
        st.stop()

    mode, lat, lon, zoom = _sidebar_controls()
    _render_mode_note(mode)

    # v3.0：沉浸式地图体验，默认不展示页面标题。
    m = _create_map(mode, lat, lon, zoom)
    _render_map(m)


if __name__ == "__main__":
    main()
