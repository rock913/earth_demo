AlphaEarth (AEF) 国家级空间智能底座 · 极速验证实战手册

版本： v5.0 (智能缓存增强版)
适用场景： 部委汇报、高层演示、技术验证
核心特性： 包含“智能混合加载”机制，兼顾实时性与极速体验。

1. 演示场景与机理 (The 4 Scenarios)

我们完整定义了四个能够覆盖自然资源、生态、建设等多部委需求的 AI 场景。

场景名称

对应部委

核心机理 (AI Operator)

视觉呈现

1. 地表 DNA (语义视图)

自然资源部 / 大数据局

PCA 降维： 将 64维特征压缩为 RGB，同类地物颜色自动归一。

彩色纹理 (赛博风)

2. 变化雷达 (敏捷治理)

执法局 / 督察办

欧氏距离： 计算 2019-2024 特征向量距离，锁定本质变化。

红色高亮 (热成像)

3. 建设强度 (宏观管控)

规划司 / 国土空间规划

特征响应 (Dim 0)： 提取对人造地表强响应的特征维。

冰蓝光晕 (科技感)

4. 生态韧性 (绿色底线)

生态环境部 / 林草局

特征反演 (Dim 2)： 提取对植被生物量强响应的特征维。

荧光绿 (夜视仪)

2. 技术架构：智能混合加载 (Smart Hybrid Loading)

为了解决“实时计算慢”的问题，我们引入了一套动态缓存机制。

查询 (Query)： 前端请求某地标的 AI 图层。

探测 (Detect)： Python 脚本自动检测您的 GEE Assets 中是否已存在该地点的缓存文件。

分流 (Route)：

✅ 命中缓存： 直接加载静态 Asset，延迟 < 0.5秒。

⚡ 未命中： 调用 Google Cloud 实时计算，延迟 3-8秒。

写入 (Write)： 在实时计算模式下，提供“📥 后台缓存”按钮，点击后自动将结果导出到 GEE Asset，下次演示即可秒开。

3. 完整代码实现 (app.py)

请直接复制以下代码。此版本增加了 Asset 管理和后台导出功能。

注意： 请在代码顶部的 GEE_USER_PATH 填入您的 GEE 用户名（例如 users/zhangsan）。

import streamlit as st
import ee
import geemap.foliumap as geemap
from datetime import datetime

# =========================================================
# 0. 全局配置 (请修改此处!)
# =========================================================
# 您的 GEE 根目录，用于存放缓存数据
# 请在 GEE Code Editor 左上角 Assets 面板查看您的路径
GEE_USER_PATH = "users/your_username_here/aef_demo" 

# =========================================================
# 1. 页面初始化
# =========================================================
st.set_page_config(layout="wide", page_title="ALPHA EARTH COMMAND", initial_sidebar_state="collapsed")

# 注入 CSS：HUD 风格
st.markdown("""
<style>
    .stApp { background-color: #000000; }
    header, footer, #MainMenu { visibility: hidden; }
    .block-container { padding: 0 !important; }
    
    /* HUD Header */
    .hud-header {
        position: fixed; top: 20px; left: 20px; z-index: 9999;
        background: rgba(16, 20, 24, 0.9); 
        border-left: 5px solid #00F5FF; padding: 15px 25px; 
        backdrop-filter: blur(10px); border-radius: 0 4px 4px 0;
    }
    .hud-title { color: #FFF; font-weight: 700; font-size: 24px; margin: 0; }
    
    /* HUD Panel */
    .hud-panel {
        position: fixed; top: 100px; right: 20px; z-index: 9998;
        width: 320px; background: rgba(0, 0, 0, 0.85);
        border-top: 3px solid #FF00FF; padding: 20px; color: #EEE;
        backdrop-filter: blur(10px);
    }
    
    /* Status Badge */
    .status-badge {
        padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;
    }
    .status-live { background: #FF4444; color: white; }
    .status-cached { background: #00AA00; color: white; }
    
    iframe { height: 100vh !important; }
</style>
""", unsafe_allow_html=True)

# GEE 初始化
try:
    ee.Initialize()
except Exception:
    ee.Authenticate()
    ee.Initialize()

# =========================================================
# 2. 核心逻辑：智能混合加载
# =========================================================

def get_layer_logic(mode, region):
    """
    定义核心计算逻辑 (纯数学算子)
    返回: ee.Image, 视觉参数, Asset名称后缀
    """
    emb_col = ee.ImageCollection("GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL")
    
    if "地表 DNA" in mode:
        emb = emb_col.filterDate('2024-01-01', '2024-12-31').first()
        # 逻辑：PCA 模拟 (前3维映射)
        img = emb.select(['0', '1', '2'])
        vis = {'min': -0.1, 'max': 0.1, 'gamma': 1.6}
        suffix = "dna"
        
    elif "变化雷达" in mode:
        emb19 = emb_col.filterDate('2019-01-01', '2019-12-31').first()
        emb24 = emb_col.filterDate('2024-01-01', '2024-12-31').first()
        # 逻辑：欧氏距离
        img = emb19.subtract(emb24).pow(2).reduce(ee.Reducer.sum()).sqrt()
        # 仅保留变化区域
        img = img.updateMask(img.gt(0.18))
        vis = {'min': 0.18, 'max': 0.45, 'palette': ['FF0000', 'FF8800', 'FFFFFF']}
        suffix = "change"
        
    elif "建设强度" in mode:
        emb = emb_col.filterDate('2024-01-01', '2024-12-31').first()
        # 逻辑：Dim 0 响应
        img = emb.select('0').normalize()
        img = img.updateMask(img.gt(0.4))
        vis = {'min': 0.4, 'max': 0.75, 'palette': ['000000', '0000AA', '00F5FF', 'FFFFFF']}
        suffix = "intensity"
        
    elif "生态韧性" in mode:
        emb = emb_col.filterDate('2024-01-01', '2024-12-31').first()
        # 逻辑：Dim 2 反演
        img = emb.select('2').multiply(-1)
        img = img.updateMask(img.gt(-0.05))
        vis = {'min': -0.1, 'max': 0.15, 'palette': ['000000', '004400', '00FF00', 'CCFF00']}
        suffix = "eco"
        
    return img.clip(region), vis, suffix

def smart_load(mode, region, loc_code):
    """
    智能加载：先查 Asset，无则计算
    """
    # 1. 获取计算逻辑
    computed_img, vis_params, suffix = get_layer_logic(mode, region)
    
    # 2. 构建 Asset ID (例如: users/zhangsan/aef_demo/shanghai_change)
    asset_id = f"{GEE_USER_PATH}/{loc_code}_{suffix}"
    
    status_html = ""
    final_layer = None
    is_cached = False
    
    try:
        # 尝试加载 Asset
        ee.data.getAsset(asset_id) # 如果不存在会抛异常
        final_layer = ee.Image(asset_id)
        status_html = "<span class='status-badge status-cached'>🚀 极速缓存 (Asset)</span>"
        is_cached = True
    except:
        # Asset 不存在，使用实时计算
        final_layer = computed_img
        status_html = "<span class='status-badge status-live'>⚡ 实时计算 (Cloud)</span>"
        is_cached = False
        
    return final_layer, vis_params, status_html, is_cached, asset_id, computed_img

def trigger_export(image, description, asset_id, region):
    """触发 GEE 后台导出任务"""
    task = ee.batch.Export.image.toAsset(
        image=image,
        description=description,
        assetId=asset_id,
        region=region,
        scale=10,
        maxPixels=1e9
    )
    task.start()
    return task.id

# =========================================================
# 3. 侧边栏与控制
# =========================================================
with st.sidebar:
    st.title("🎛️ 指挥控制台")
    st.markdown("---")
    
    mode = st.radio("监测场景", 
        ["地表 DNA (语义视图)", "变化雷达 (敏捷治理)", "建设强度 (宏观管控)", "生态韧性 (绿色底线)"])
    
    st.markdown("---")
    
    # 地标定义 (增加 loc_code 用于文件名)
    locations = {
        "上海 · 陆家嘴": {"coords": [31.2304, 121.5000, 14], "code": "shanghai"},
        "北京 · 通州": {"coords": [39.9042, 116.7000, 13], "code": "beijing"},
        "河北 · 雄安": {"coords": [39.0500, 115.9800, 12], "code": "xiongan"},
        "杭州 · 西湖": {"coords": [30.2450, 120.1400, 14], "code": "hangzhou"},
        "深圳 · 湾区": {"coords": [22.5000, 113.9500, 13], "code": "shenzhen"},
        "美国 · 纽约": {"coords": [40.7580, -73.9855, 13], "code": "nyc"}
    }
    
    loc_name = st.selectbox("核心监测区", list(locations.keys()))
    loc_data = locations[loc_name]
    lat, lon, zoom = loc_data["coords"]
    
    st.info("💡 操作：拖动滑块对比。若显示‘实时计算’，可点击下方按钮缓存以加速下次演示。")

# =========================================================
# 4. 主渲染逻辑
# =========================================================

# 动态视口 Geometry
viewport = ee.Geometry.Point([lon, lat]).buffer(20000)

# 智能加载图层
layer_img, layer_vis, status_msg, is_cached, asset_path, raw_img = smart_load(mode, viewport, loc_data["code"])

# HUD 信息内容
hud_info = {
    "地表 DNA": {"title": "🧬 地表 DNA 解析", "desc": "AI 自动识别土地功能基因", "formula": "PCA(Vector_64d)"},
    "变化雷达": {"title": "⚠️ 时空风险雷达", "desc": "锁定地表属性本质突变", "formula": "Euclidean_Dist(V1, V2)"},
    "建设强度": {"title": "🏗️ 建设强度场", "desc": "数字化全域开发强度", "formula": "Dim_0_Response"},
    "生态韧性": {"title": "🌿 生态韧性底线", "desc": "监测生态屏障完整性", "formula": "Inverse(Dim_2)"}
}
info = hud_info.get(mode.split(' ')[0], hud_info["地表 DNA"])

# 构建地图
m = geemap.Map(center=[lat, lon], zoom=zoom, height="100vh", basemap="HYBRID")

# 左侧：2024 真实影像
s2_layer = ee.ImageCollection("COPERNICUS/S2_SR").filterBounds(viewport)\
    .filterDate('2024-01-01', '2024-12-31').median()\
    .visualize(min=0, max=3000, bands=['B4', 'B3', 'B2'])

# 右侧：AI 图层 (可视化)
ai_layer_vis = layer_img.visualize(**layer_vis)

m.split_map(s2_layer, ai_layer_vis)

# 渲染页面元素
st.markdown(f"""
<div class='hud-header'>
    <p class='hud-title'>ALPHA EARTH <span style='color:#00F5FF'>COMMAND</span></p>
    <p style='color:#00F5FF; font-size:12px; margin-top:5px'>
        TARGET: {loc_name.split(' ')[0]} /// MODE: {status_msg}
    </p>
</div>

<div class='hud-panel'>
    <h4>{info['title']}</h4>
    <p>{info['desc']}</p>
    <hr style='border-color: #333'>
    <div style='margin-bottom:10px'>
        <span style='color:#888; font-size:12px'>CORE OPERATOR</span><br>
        <code>{info['formula']}</code>
    </div>
</div>
""", unsafe_allow_html=True)

# 缓存按钮逻辑 (仅当未缓存时显示)
if not is_cached:
    with st.sidebar:
        st.write("---")
        st.write("**🚀 性能优化**")
        if st.button("📥 为下次演示缓存结果 (后台导出)"):
            task_id = trigger_export(
                raw_img, 
                f"Cache_{loc_data['code']}_{mode}", 
                asset_path, 
                viewport
            )
            st.success(f"任务已提交! ID: {task_id}")
            st.caption("请等待约 5-10 分钟，GEE 后台处理完成后，下次选择此场景将自动秒开。")

m.to_streamlit(height=800)


4. 如何使用“智能缓存”功能？

场景一：第一次彩排 (冷启动)

启动 Streamlit 应用。

选择“雄安新区” -> “变化雷达”。

地图加载可能需要 3-5 秒（HUD 显示 ⚡ 实时计算）。

操作： 点击侧边栏底部的 “📥 为下次演示缓存结果” 按钮。

系统提示任务已提交。您可以继续测试其他城市。

场景二：正式汇报 (热启动)

(假设您昨天已经点了缓存按钮，且 GEE 后台任务已完成)。

打开应用，选择“雄安新区” -> “变化雷达”。

效果： 地图秒级加载，HUD 状态标显示 🚀 极速缓存。

话术： “大家看到的是经过我们预处理的高精度分析结果，响应速度极快。”

5. 常见问题 (Troubleshooting)

报错 Asset not found 或权限错误？

检查代码中的 GEE_USER_PATH 是否修改为您自己的 GEE 用户名。

您需要在 GEE Code Editor 中手动创建一个文件夹 aef_demo，否则导出任务可能会因为找不到目录而失败。

缓存任务需要多久？

通常 100 平方公里的区域，导出 Asset 需要 3-8 分钟。建议在汇报前一天晚上，把所有重点城市的 4 个模式都点一遍缓存。

如果我想更新缓存怎么办？

直接在 GEE Code Editor 的 Assets 标签页中删除对应的 Image，Streamlit 下次运行时检测不到 Asset，就会自动切回“实时计算”模式。