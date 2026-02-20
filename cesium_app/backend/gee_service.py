"""
GEE Service Layer for Cesium App
提供 Google Earth Engine 的核心计算和缓存管理功能
"""
import ee
import os
from typing import Dict, Tuple, Any


def compute_zonal_stats(
    image: Any,
    region: Any,
    *,
    scale: int = 30,
    max_pixels: int = int(1e9),
    masked_as_anomaly: bool = True,
) -> Dict[str, Any]:
    """Compute simple zonal statistics for a layer.

    This is intended to power V5 HUD metrics (replace mockStats) with real cloud
    results via Earth Engine `reduceRegion`.

    Returns numbers in km^2 and percent.
    """

    # Total area of the analysis geometry (pixel-based so it matches mask behavior)
    pixel_area = ee.Image.pixelArea().rename(["area"])
    total_area_m2 = pixel_area.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=region,
        scale=scale,
        maxPixels=max_pixels,
    ).get("area")

    anomaly_area_m2 = None
    if masked_as_anomaly:
        # Treat masked-in pixels as anomaly; our mode logic typically sets mask for "interesting" areas.
        anomaly_area_m2 = pixel_area.updateMask(image.mask()).reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=region,
            scale=scale,
            maxPixels=max_pixels,
        ).get("area")

    # Convert to client-side numbers
    total_m2 = ee.Number(total_area_m2).getInfo() if total_area_m2 is not None else 0.0
    total_km2 = float(total_m2) / 1e6 if total_m2 else 0.0

    anomaly_km2 = None
    anomaly_pct = None
    if anomaly_area_m2 is not None and total_m2:
        a_m2 = float(ee.Number(anomaly_area_m2).getInfo())
        anomaly_km2 = a_m2 / 1e6
        anomaly_pct = (a_m2 / float(total_m2)) * 100.0

    return {
        "total_area_km2": total_km2,
        "anomaly_area_km2": anomaly_km2,
        "anomaly_pct": anomaly_pct,
        "scale_m": scale,
    }


def get_layer_logic(mode: str, region: Any) -> Tuple[Any, Dict, str]:
    """
    定义核心计算逻辑 (纯数学算子)
    
    Args:
        mode: AI 场景模式 (如 "地表 DNA (语义视图)")
        region: ee.Geometry 对象，表示监测区域
    
    Returns:
        (ee.Image, 视觉参数, Asset名称后缀)
    """
    emb_col = ee.ImageCollection("GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL")

    # Core fix: Earth Engine stores imagery in large tiles; using .first() may return just
    # the first intersecting source tile, rendering as a single square. Use
    # filterBounds(region).mosaic() to stitch all intersecting pieces into one image.
    filtered_col = emb_col.filterBounds(region).filterDate('2023-01-01', '2025-01-01')

    if "地表 DNA" in mode:
        img = filtered_col.mosaic().select(['A00', 'A01', 'A02'])
        vis = {'min': -0.1, 'max': 0.1, 'gamma': 1.6}
        suffix = "dna"

    elif "变化雷达" in mode:
        emb19 = emb_col.filterBounds(region).filterDate('2019-01-01', '2019-12-31').mosaic()
        emb24 = filtered_col.mosaic()
        img = emb19.subtract(emb24).pow(2).reduce(ee.Reducer.sum()).sqrt()
        img = img.updateMask(img.gt(0.18))
        vis = {'min': 0.18, 'max': 0.45, 'palette': ['FF0000', 'FF8800', 'FFFFFF']}
        suffix = "change"

    elif "建设强度" in mode:
        img = filtered_col.mosaic().select(['A00']).rename(['intensity']).unitScale(0, 1)
        img = img.updateMask(img.gt(0.4))
        # NOTE: Avoid specifying 'bands' here. Cached assets may not preserve the renamed band name,
        # and Earth Engine will throw "Image.visualize: No band named ..." when vis_params bands mismatch.
        # For single-band images, leaving 'bands' unset is robust.
        vis = {'min': 0.4, 'max': 0.75, 'palette': ['000000', '0000AA', '00F5FF', 'FFFFFF']}
        suffix = "intensity"

    elif "生态韧性" in mode:
        img = filtered_col.mosaic().select(['A02']).rename(['eco']).multiply(-1)
        img = img.updateMask(img.gt(-0.05))
        # See note above about avoiding fragile 'bands' in vis_params.
        vis = {'min': -0.1, 'max': 0.15, 'palette': ['000000', '004400', '00FF00', 'CCFF00']}
        suffix = "eco"
    else:
        raise ValueError(f"Unknown mode: {mode}")
    
    # 🔧 修复：不裁剪图像到region，保持全球范围
    # 原因：clip()后的小范围图像在某些zoom level下可能没有瓦片
    # Cesium会根据视口自动加载需要的瓦片范围
    # 注意：filterBounds仍然用于选择正确的时间/空间数据
    return img, vis, suffix


def generate_asset_id(loc_code: str, suffix: str, gee_user_path: str) -> str:
    """
    生成 Asset ID
    
    Args:
        loc_code: 地点代码 (如 "shanghai")
        suffix: 场景后缀 (如 "change")
        gee_user_path: GEE 用户路径 (如 "users/xxx/aef_demo")
    
    Returns:
        完整的 Asset ID
    """
    return f"{gee_user_path}/{loc_code}_{suffix}"


def smart_load(
    mode: str, 
    region: Any, 
    loc_code: str,
    gee_user_path: str
) -> Tuple[Any, Dict, str, bool, str, Any]:
    """
    智能加载：先查 Asset，无则计算
    
    Args:
        mode: AI 场景模式
        region: 监测区域
        loc_code: 地点代码
        gee_user_path: GEE 用户路径
    
    Returns:
        (图层, 视觉参数, 状态HTML, 是否缓存命中, Asset ID, 原始计算图层)
    """
    # 1. 获取计算逻辑
    computed_img, vis_params, suffix = get_layer_logic(mode, region)
    
    # 2. 构建 Asset ID
    asset_id = generate_asset_id(loc_code, suffix, gee_user_path)
    
    status_html = ""
    final_layer = None
    is_cached = False
    
    try:
        # 尝试加载 Asset
        ee.data.getAsset(asset_id)  # 如果不存在会抛异常
        final_layer = ee.Image(asset_id)
        status_html = "<span class='status-badge status-cached'>🚀 极速缓存 (Asset)</span>"
        is_cached = True
    except Exception:
        # Asset 不存在，使用实时计算
        final_layer = computed_img
        status_html = "<span class='status-badge status-live'>⚡ 实时计算 (Cloud)</span>"
        is_cached = False
        
    return final_layer, vis_params, status_html, is_cached, asset_id, computed_img


def get_tile_url(image: Any, vis_params: Dict) -> str:
    """
    获取 GEE 图层的 Tile URL
    
    Args:
        image: ee.Image 对象
        vis_params: 可视化参数
    
    Returns:
        XYZ Tile URL (包含 {z}/{x}/{y} 占位符)
    """
    # 🔧 修复：GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL数据已经是Web友好的
    # 无需重投影，直接生成MapID即可获得有效的瓦片
    # 原始投影(EPSG:32645 UTC45N)已被GEE正确处理
    map_id = image.getMapId(vis_params)
    tile_url = map_id['tile_fetcher'].url_format
    return tile_url


def trigger_export_task(
    image: Any,
    description: str,
    asset_id: str,
    region: Any,
    scale: int = 10,
    max_pixels: int = int(1e9)
) -> str:
    """
    触发 GEE 后台导出任务
    
    Args:
        image: 要导出的 ee.Image
        description: 任务描述
        asset_id: 目标 Asset ID
        region: 导出区域
        scale: 分辨率 (米)
        max_pixels: 最大像素数
    
    Returns:
        任务 ID
    """
    task = ee.batch.Export.image.toAsset(
        image=image,
        description=description,
        assetId=asset_id,
        region=region,
        scale=scale,
        maxPixels=max_pixels
    )
    task.start()
    return task.id


def init_earth_engine():
    """
    初始化 Earth Engine
    优先使用服务账号，回退到交互式认证
    """
    try:
        # 尝试服务账号认证
        service_account = os.getenv('EE_SERVICE_ACCOUNT')
        key_file = os.getenv('EE_PRIVATE_KEY_FILE')
        
        if service_account and key_file:
            credentials = ee.ServiceAccountCredentials(service_account, key_file)
            ee.Initialize(credentials)
            print(f"✅ GEE initialized with service account: {service_account}")
        else:
            # 交互式认证
            ee.Initialize()
            print("✅ GEE initialized with user credentials")
    except Exception as e:
        print(f"❌ GEE initialization failed: {e}")
        raise

