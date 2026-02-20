OneEarth 空间智能底座 · V5.0 旗舰指挥舱升级白皮书

文档版本： v5.0
核心目标： 从“技术验证原型 (PoC)”全面升级为“国家级空间治理指挥舱”
技术栈： Vue3 + CesiumJS (前端 WebGL) | FastAPI + httpx (后端高并发) | Google Earth Engine (云端算力)

一、 战略叙事重构：为什么要有这个版本？

过去我们在 Streamlit 上的演示更像是一个“研发人员的调参工具”。为了向部委级领导汇报，证明建设中国版 AlphaEarth（OneEarth）的必要性，我们在 V5.0 版本中实现了“叙事逻辑的降维打击”。

1. 剧情化交互（三幕剧）

系统不再一上来就怼着某条街道，而是设计了电影级的体验流：

第一幕 [行星待机]： 满屏星空与自转的地球。潜台词：“我们在管理一整个星球”。

第二幕 [目标锁定]： 点击任务后，镜头从 2000 万米太空极速俯冲至目标上空。潜台词：“指哪打哪的算力聚焦”。

第三幕 [情报展开]： AI 图层如扫描仪般覆盖 3D 城市，右侧滑出定量分析报表。潜台词：“感知-计算-决策的业务闭环”。

2. “悖论演示”战略 (The Paradoxical Demo)

此版本拥有极具震撼力的视觉效果和响应速度，但这正是一个**“战略阳谋”**：

“领导请看，这套全球无死角、实时计算的上帝视角非常强大。但是，它的底层数据和算力目前全部在 Google 的服务器上。 我们建设 OneEarth 项目，就是要把这个炫酷外壳下的‘心脏’，换成我们中国自主可控的计算底座。”

二、 核心技术架构升级与难点攻克

为了支撑上述宏大的叙事，我们在底层架构上进行了彻底的换血，攻克了三大技术痛点。

痛点 1：地图卡顿、白屏与黑块 (渲染性能瓶颈)

过去： 使用 Folium/Streamlit，服务端渲染，一次只能加载有限的图块，视角一动就卡死。

现在： 引入 CesiumJS (WebGL)。GPU 客户端硬件加速，不仅支持 60 帧丝滑缩放，还引入了 3D 真实地形和城市建筑白模。

后端重构 (FastAPI 异步代理)： Cesium 移动视角时会瞬间并发几十个瓦片请求。我们将后端的 urllib (同步阻塞) 彻底重写为 httpx (全异步非阻塞)。
伪代码对比：

# ❌ 旧版：同步阻塞，导致大量瓦片 Timeout，地图出现黑块
response = urllib.request.urlopen(url) 

# ✅ 新版：异步高并发池，瞬间吞吐上百个瓦片请求
async with httpx.AsyncClient() as client:
    response = await client.get(url)


痛点 2：AI 图层只有“一小块” (空间计算局限)

过去： 引擎只计算屏幕中心 20km 的圆形范围 (.clip(region))，缩小地图后边缘被直接切断。

现在： 解除人为的空间禁锢。利用 GEE 的 .mosaic() 算子，在云端动态拼接覆盖当前视锥体（Frustum）的所有数据。
核心逻辑：

# GEE Backend Service
def get_layer_logic(mode, region):
    # 1. 不再使用 .first()，改用 filterBounds().mosaic() 获取全域拼接特征
    filtered_col = emb_col.filterBounds(region).filterDate('2023-01-01', '2025-01-01')
    img = filtered_col.mosaic()

    # 2. 执行数学算子 (如提取维度0)
    img_result = img.select(['0']).normalize()

    # 3. 移除 .clip()，让前端 Cesium 按需无缝加载全球瓦片
    return img_result, vis_params


痛点 3：缺乏“业务闭环” (只有图没有数)

过去： 只有一张红绿相间的热力图，缺乏量化支撑。

现在： 前端引入了任务驱动模型 (Mission-Driven) 与 数据面板 (Dashboard)。

// 前端 Vue3 状态机与任务配置
const missions = [
  { 
    name: '河南周口 · 农作物健康体检', 
    apiMode: 'eco', // 对应后端计算逻辑
    mockStats: { area: '8,452', anomaly: '12.4' } // 定量数据支撑
  }
]


三、 三大核心演示专项 (Missions)

新系统包装了三个具备国家级意义的切口：

农业安全：河南周口 · 农作物健康体检

底层调用： AEF_Inverse(Dim_2)

业务叙事： 替代传统 NDVI 只能看叶绿素的局限，利用 AEF 64 维特征反演高标准农田的生长韧性，精准发现内涝、病虫害等深层结构胁迫。

生态红线：毛乌素沙地 · 三北防护林演变

底层调用： Distance(V_2019, V_2024)

业务叙事： 穿越 5 年的时空特征距离。自动过滤植被季节性发芽/落叶的干扰，锁定非法采砂、毁林开荒等“本质性地表退化”。

城市治理：粤港澳大湾区 · 无序扩张监测

底层调用： Normalize(Dim_0)

业务叙事： 提取 AEF 中对人造地表高度敏感的特征通道，生成全域开发强度场，直观呈现城市群的连片蔓延趋势。

四、 下一步演进路线图 (Roadmap to V6.0)

目前 V5.0 已具备极强的展示能力，后续我们将着手“填实”后端：

图表数据真实化 (Dynamic Zonal Statistics)：
将右侧面板的 mockStats 替换为 GEE 的 reduceRegion 实时统计，真正在云端算出异常面积的准确百分比。

LLM 智能报告生成 (Agentic Workflow)：
将后端的统计结果 JSON 喂给大语言模型（如 Qwen/DeepSeek/Gemini），实时生成《区域空间监测简报》（含原因推测与处置建议）。

国产引擎平替预研 (The "OneEarth" Goal)：
在阿里云 / 达摩院 AI 平台上复现 Satellite Embedding 的推理管线，真正切断对 GEE 的依赖。