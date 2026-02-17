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


APP_TITLE = "AlphaEarth 国家级空间智能底座 POC"


def _set_theme() -> None:
    st.set_page_config(layout="wide", page_title="AlphaEarth 空间智能驾驶舱")
    st.markdown(
        """
<style>
    /* Streamlit theme tweaks (dark dashboard style) */
    .stApp { background: #0e1117; }
    h1, h2, h3, h4 { color: #ffffff; }
    section[data-testid="stSidebar"] { background-color: #262730; }
</style>
        """,
        unsafe_allow_html=True,
    )


def _init_gee() -> Tuple[bool, Optional[str]]:
    if ee is None:
        return False, f"earthengine-api import 失败：{_ee_import_error}"

    # Option A: Use a service account (recommended for server deployments)
    # Set env vars on ECS:
    # - EE_SERVICE_ACCOUNT (e.g. xxx@yyy.iam.gserviceaccount.com)
    # - EE_PRIVATE_KEY_FILE (path to JSON key)
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
            "提示：如果你看到 ‘Credentials already exist’ 但页面仍提示未认证，\n"
            "通常是授权时的用户/`HOME`/`XDG_CONFIG_HOME` 与 systemd 服务运行环境不一致，\n"
            "导致服务进程找不到 `~/.config/earthengine/credentials`。\n\n"
            "服务账号的创建与 JSON key 获取步骤见 README 的“服务账号（可选）”。\n\n"
            f"详细错误：{exc}"
        )


def _sidebar_controls() -> tuple[str, float, float, int]:
    st.sidebar.image(
        "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e5/NASA_logo.svg/512px-NASA_logo.svg.png",
        width=100,
    )
    st.sidebar.title("空间智能底座")
    st.sidebar.markdown("---")

    mode = st.sidebar.radio(
        "选择治理场景",
        [
            "场景一：地表 DNA 语义视图（认知统一）",
            "场景二：时空变化风险雷达（敏捷治理）",
        ],
    )

    st.sidebar.markdown("---")
    st.sidebar.subheader("视口控制")

    # 默认坐标：上海临港
    lat = st.sidebar.number_input("纬度", value=30.90, format="%.4f")
    lon = st.sidebar.number_input("经度", value=121.93, format="%.4f")
    zoom = int(st.sidebar.slider("缩放级别", 4, 16, 12))

    return mode, float(lat), float(lon), zoom


def _add_sentinel2_layer(m, lat: float, lon: float) -> None:
    s2 = (
        ee.ImageCollection("COPERNICUS/S2_SR")
        .filterBounds(ee.Geometry.Point([lon, lat]))
        .filterDate("2024-01-01", "2024-12-31")
        .sort("CLOUDY_PIXEL_PERCENTAGE")
        .first()
    )

    if s2 is None:
        st.warning("未获取到 Sentinel-2 影像（该点位/时间段可能无可用影像）。")
        return

    vis_s2 = {"min": 0, "max": 3000, "bands": ["B4", "B3", "B2"]}
    _add_ee_layer(m, s2, vis_s2, "2024 真实光学影像")


def _add_aef_layers(m, mode: str, lat: float, lon: float) -> None:
    # AEF Embedding 数据集
    dataset = ee.ImageCollection("GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL")
    point = ee.Geometry.Point([lon, lat])

    semantic_opacity = st.sidebar.slider("语义图层透明度", 0.0, 1.0, 0.85, 0.05)
    change_opacity = st.sidebar.slider("变化雷达透明度", 0.0, 1.0, 0.90, 0.05)

    if "地表 DNA" in mode or "场景一" in mode:
        # Important: the embedding dataset is tiled. Using `.first()` picks an arbitrary tile,
        # which often has no overlap with the current viewport.
        col2024 = dataset.filterDate("2024-01-01", "2024-12-31").filterBounds(point)
        try:
            if int(col2024.size().getInfo()) == 0:
                st.warning("当前位置附近未检索到 Earth DNA（Embedding）数据切片；请移动到其它区域重试。")
                return
        except Exception:
            # If we cannot query size (permissions/network), still attempt to render.
            pass

        emb2024 = col2024.mosaic()

        # 取前 3 个 band 映射到 RGB（band 名可能随数据集版本变化）
        # Default band names for this dataset are usually A00..A63
        bands = ["A00", "A01", "A02"]
        try:
            names = emb2024.bandNames().getInfo()
            if isinstance(names, list) and len(names) >= 3:
                bands = [str(names[0]), str(names[1]), str(names[2])]
        except Exception:
            # 如果无法 getInfo（网络/权限限制），回退到默认名称
            pass

        vis_params = {
            "bands": bands,
            "min": -0.15,
            "max": 0.15,
            "gamma": 1.4,
        }
        _add_ee_layer(m, emb2024, vis_params, "AI 语义底座（Earth DNA）", opacity=semantic_opacity)

        st.info(
            """
**核心价值：认知统一**

- 当前图层并非光学照片，而是 AI 对地表的语义理解。
- 颜色相似区域代表功能属性相似（如工业区/农田/城市）。
- 无需重复测绘，一套底座，全域感知。
            """.strip()
        )

    elif "变化风险" in mode or "场景二" in mode:
        col2019 = dataset.filterDate("2019-01-01", "2019-12-31").filterBounds(point)
        col2024 = dataset.filterDate("2024-01-01", "2024-12-31").filterBounds(point)
        try:
            if int(col2019.size().getInfo()) == 0 or int(col2024.size().getInfo()) == 0:
                st.warning("当前位置附近未检索到 2019/2024 的 Embedding 数据切片；请移动到其它区域重试。")
                return
        except Exception:
            pass

        emb2019 = col2019.mosaic()
        emb2024 = col2024.mosaic()

        # 欧氏距离（跨多 band）
        diff = emb2019.subtract(emb2024).pow(2).reduce(ee.Reducer.sum()).sqrt()

        threshold = st.sidebar.slider("变化阈值（越小越敏感）", 0.01, 0.30, 0.10, 0.01)
        diff_masked = diff.updateMask(diff.gt(threshold))

        vis_change = {
            "min": threshold,
            "max": 0.4,
            "palette": ["#ffff00", "#ffaa00", "#ff0000"],
        }
        _add_ee_layer(m, diff_masked, vis_change, "变化风险雷达", opacity=change_opacity)

        st.error(
            """
**核心价值：敏捷治理**

- 红色高亮区域代表地表属性发生了本质突变（如耕地变厂房、滩涂变码头）。
- 自动过滤光照/云层/季节性干扰，只突出“结构性变化”。
- 从“被动核查”升级为“全域风险主动发现”。
            """.strip()
        )


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
        m.to_streamlit(height=700)
        return

    # 回退：使用 streamlit-folium
    try:
        from streamlit_folium import st_folium

        st_folium(m, height=700, width=None)
    except Exception as exc:
        st.error(f"地图渲染失败：{exc}")


def main() -> None:
    _set_theme()

    st.title(APP_TITLE)

    gee_ok, gee_msg = _init_gee()
    if not gee_ok:
        st.warning(gee_msg)
        st.stop()

    mode, lat, lon, zoom = _sidebar_controls()

    col1, col2 = st.columns([3, 1])

    with col1:
        m = _create_map(mode, lat, lon, zoom)
        _render_map(m)

    with col2:
        st.markdown("### 实时计算指标")
        st.metric("数据源吞吐", "PB 级", delta="全球实时")
        st.metric("特征维度", "64 维", help="每个像素包含 64 个高维语义特征")
        st.metric("推理延迟", "< 300ms", delta="流式计算")

        st.markdown("---")
        st.markdown("### 架构说明")
        st.caption("本系统采用混合云（Hybrid Cloud）架构。")
        st.caption("后端矩阵运算在 Google Cloud / Earth Engine 完成。")
        st.caption("前端交互展现部署于阿里云 ECS。")
        st.caption("数据零下载：原始 PB 级数据无需落地。")


if __name__ == "__main__":
    main()
