# AlphaEarth Cesium 版本

> 基于 CesiumJS 的 3D 地球可视化版本，提供电影级视觉体验和行星级叙事能力

## 📚 文档导航

- **[快速参考卡片](QUICK_REFERENCE.md)** - 常用命令和配置速查
- **[.env 使用指南](ENV_GUIDE.md)** - 环境变量配置详解
- **[版本对比分析](COMPARISON.md)** - Streamlit vs Cesium 对比
- **[开发总结](DEVELOPMENT_SUMMARY.md)** - 技术实现与测试报告

## 🎯 项目概述

这是 AlphaEarth 的 Cesium 升级版本，相比 Streamlit 版本：

### ✨ 核心优势

| 维度 | Streamlit (原版) | Cesium (升级版) |
|------|-----------------|----------------|
| **视觉维度** | 2D 平面地图 | 3D 数字地球 + 地形 + 大气层 |
| **交互性能** | 服务端渲染，卡顿 | 客户端 WebGL，60fps 丝滑 |
| **时空表达** | 静态切片 | 支持时间轴动态播放 |
| **叙事价值** | 像看纸质地图 | 上帝视角，行星级底座 |

### 🏗️ 技术架构

```
Frontend (Port 8502)          Backend API (Port 8503)         Google Earth Engine
┌─────────────────┐          ┌─────────────────┐            ┌──────────────┐
│ Vue3 + CesiumJS │◄────────►│  FastAPI        │◄──────────►│  AEF Dataset │
│ - 3D 渲染       │  REST    │  - GEE 计算     │   ee API   │  - Embeddings│
│ - HUD 界面      │  JSON    │  - 缓存管理     │            │  - Sentinel-2│
│ - 交互控制      │          │  - Tile URL生成 │            └──────────────┘
└─────────────────┘          └─────────────────┘
```

## 📁 项目结构

```
cesium_app/
├── backend/                 # Python FastAPI 后端
│   ├── main.py             # API 主入口
│   ├── gee_service.py      # GEE 计算逻辑
│   ├── config.py           # 配置管理
│   └── requirements.txt    # Python 依赖
├── frontend/               # Vue3 + Cesium 前端
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── main.js
│       ├── App.vue         # 主应用
│       ├── components/
│       │   ├── CesiumViewer.vue   # 3D 地球渲染
│       │   └── HudPanel.vue       # HUD 控制面板
│       └── services/
│           └── api.js      # 后端 API 调用
├── tests/                  # 测试套件
│   ├── conftest.py
│   ├── test_gee_service.py      # GEE 服务单元测试
│   ├── test_backend_api.py      # API 端点测试
│   └── test_integration.py      # 集成测试
├── run_backend.sh          # 后端启动脚本
├── run_frontend.sh         # 前端启动脚本
└── README.md              # 本文档
```

## 🚀 快速开始

### 环境要求

- **后端**: Python 3.9+
- **前端**: Node.js 18+ / npm 9+
- **GEE 账号**: 已授权的 Google Earth Engine 账户

### 0. 配置环境变量（首次使用）

**推荐方式：使用 .env 文件**

```bash
cd cesium_app

# 方式 A: 交互式配置（最简单）
./setup_env.sh

# 方式 B: 手动配置
cp .env.example .env
vim .env  # 编辑配置文件
```

最少需要配置：
```bash
GEE_USER_PATH=users/your_username/aef_demo
```

### 1. 后端启动

```bash
cd cesium_app

# 方式一：使用启动脚本（推荐）
./run_backend.sh

# 方式二：手动启动
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m uvicorn main:app --host 127.0.0.1 --port 8503 --reload
```

后端将运行在 `http://127.0.0.1:8503`

### 2. 前端启动

**在新终端中**：

```bash
cd cesium_app

# 方式一：使用启动脚本（推荐）
./run_frontend.sh

# 方式二：手动启动
cd frontend
npm install
npm run dev
```

前端将运行在 `http://127.0.0.1:8502`

### 3. 访问应用

打开浏览器访问：`http://127.0.0.1:8502`

## ⚙️ 配置说明

### 方式一：使用 .env 文件（推荐）

项目支持通过 `.env` 文件管理所有环境变量，无需每次手动 export。

#### 快速配置（交互式）

```bash
cd cesium_app
./setup_env.sh
# 按照提示输入配置信息
```

#### 手动配置

```bash
# 1. 复制示例配置文件
cp .env.example .env

# 2. 编辑 .env 文件
vim .env  # 或使用其他编辑器
```

`.env` 文件示例：

```bash
# GEE 配置（必需）
GEE_USER_PATH=users/your_username/aef_demo

# GEE 服务账号（可选，生产环境推荐）
# EE_SERVICE_ACCOUNT=xxx@yyy.iam.gserviceaccount.com
# EE_PRIVATE_KEY_FILE=/path/to/service-account-key.json

# 服务器配置
API_HOST=127.0.0.1
API_PORT=8503
FRONTEND_PORT=8502

# Cesium Token（可选）
# VITE_CESIUM_TOKEN=your_cesium_token

# LLM（可选，用于 /api/report 生成简报；未配置则使用模板回退）
# DashScope OpenAI-compatible: https://dashscope.aliyuncs.com/compatible-mode/v1
# LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
# LLM_API_KEY=your_dashscope_api_key
# LLM_MODEL=qwen-plus
# LLM_TIMEOUT_S=12
# LLM_TEMPERATURE=0.2
# LLM_MAX_TOKENS=512
```

**优势**：
- ✅ 配置集中管理
- ✅ 自动加载，无需手动 export
- ✅ 支持版本控制（.env 已在 .gitignore 中）
- ✅ 团队协作友好（共享 .env.example）

### 方式二：手动设置环境变量

如果不使用 `.env` 文件，也可以手动设置：

```bash
# 必需配置
export GEE_USER_PATH="users/your_username/aef_demo"

# 可选配置
export EE_SERVICE_ACCOUNT="xxx@yyy.iam.gserviceaccount.com"
export EE_PRIVATE_KEY_FILE="/path/to/service-account-key.json"
export VITE_CESIUM_TOKEN="your_cesium_token"
```

### Cesium Token 获取

1. 访问 [Cesium Ion](https://ion.cesium.com/)
2. 注册并登录
3. 进入 Access Tokens 页面
4. 创建新 Token 或使用默认 Token

## 🧪 测试

项目采用 TDD (测试驱动开发) 策略，提供完整的测试套件：

```bash
cd /path/to/oneearth

# 运行所有测试
pytest cesium_app/tests/ -v

# 仅运行 GEE 服务测试
pytest cesium_app/tests/test_gee_service.py -v

# 仅运行 API 测试
pytest cesium_app/tests/test_backend_api.py -v

# 查看测试覆盖率
pytest cesium_app/tests/ --cov=cesium_app/backend --cov-report=html
```

测试统计：
- ✅ 11 个 GEE 服务单元测试
- ✅ 13 个 API 端点测试
- ✅ 覆盖率 > 80%

## 🎮 功能特性

### 1. 四大 AI 监测场景

| 场景 | 算法 | 视觉效果 |
|------|------|---------|
| 🧬 地表 DNA | PCA 降维 | 彩色纹理（赛博风） |
| ⚠️ 变化雷达 | 欧氏距离 | 红色高亮（热成像） |
| 🏗️ 建设强度 | 特征响应 (Dim 0) | 冰蓝光晕（科技感） |
| 🌿 生态韧性 | 特征反演 (Dim 2) | 荧光绿（夜视仪） |

### 2. 智能混合加载

- ✅ **缓存命中**: 直接从 GEE Asset 加载，< 0.5 秒
- ⚡ **实时计算**: 调用 Cloud 计算，3-8 秒
- 📥 **后台导出**: 一键缓存，下次秒开

### 3. 3D 地球特性

- 🌍 全球地形渲染
- 🌅 大气层光照效果
- 🚁 电影级相机运镜
- 🎯 精准位置飞行

### 4. HUD 界面

- 赛博朋克风格设计
- 实时缓存状态显示
- 加载性能统计
- 一键缓存导出

### 5. V5 任务驱动（Missions）+ 业务闭环

- 🎬 Missions 三幕剧：待机（行星视角）→ 目标锁定（俯冲飞行）→ 情报展开（HUD + 图层 + 报表）
- 📊 动态统计：后端 `reduceRegion` 实时计算指标（替换 mockStats）
- 📝 智能简报：生成《区域空间监测简报》（默认模板，后续可接 LLM）

## 📊 性能指标

| 指标 | Streamlit 版本 | Cesium 版本 |
|------|---------------|------------|
| 首屏加载 | 2-3 秒 | 1-2 秒 |
| 图层切换 | 3-8 秒（服务端渲染） | 0.5-3 秒（客户端渲染） |
| 地点切换 | 5-10 秒（重新渲染） | 3 秒（飞行动画） |
| 帧率 | 不适用（静态） | 60 fps |
| 缓存加载 | < 1 秒 | < 0.5 秒 |

## 🔧 常见问题

### Q1: 后端报错 "GEE not initialized"

**解决方案**：
```bash
# 确保已授权 GEE
earthengine authenticate --quiet --auth_mode=notebook

# 或使用服务账号
export EE_SERVICE_ACCOUNT="xxx@yyy.iam.gserviceaccount.com"
export EE_PRIVATE_KEY_FILE="/path/to/key.json"
```

### Q2: 前端报错 "Failed to fetch"

**检查清单**：
1. 后端是否启动？`curl http://127.0.0.1:8503/health`
2. CORS 配置是否正确？查看浏览器控制台
3. 防火墙是否阻止？

### Q3: Cesium 地球不显示

**可能原因**：
1. Cesium Token 未配置或已过期
2. 网络无法访问 Cesium Ion
3. WebGL 未启用（检查浏览器）

### Q4: 图层加载慢

**优化建议**：
1. 使用缓存机制（点击"为下次演示缓存结果"）
2. 减小监测区域范围
3. 使用服务账号避免交互式认证延迟

## 🚢 生产部署

### systemd 服务配置

创建 `/etc/systemd/system/alphaearth-cesium-backend.service`:

```ini
[Unit]
Description=AlphaEarth Cesium Backend
After=network.target

[Service]
Type=simple
User=alphaearth
WorkingDirectory=/opt/oneearth/cesium_app/backend
Environment="GEE_USER_PATH=users/your_username/aef_demo"
Environment="EE_SERVICE_ACCOUNT=xxx@yyy.iam.gserviceaccount.com"
Environment="EE_PRIVATE_KEY_FILE=/etc/alphaearth/service-account-key.json"
ExecStart=/opt/oneearth/cesium_app/backend/venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8503
Restart=always

[Install]
WantedBy=multi-user.target
```

### Nginx 反向代理

```nginx
server {
    listen 80;
    server_name your.domain.com;

    # 前端静态文件
    location / {
        root /opt/oneearth/cesium_app/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # 后端 API
    location /api/ {
        proxy_pass http://127.0.0.1:8503;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 📖 API 文档

后端提供 RESTful API，启动后访问：
- Swagger UI: `http://127.0.0.1:8503/docs`
- ReDoc: `http://127.0.0.1:8503/redoc`

### 核心端点

```
GET  /health               # 健康检查
GET  /api/locations        # 获取所有地点
GET  /api/modes           # 获取所有 AI 模式
GET  /api/missions        # 获取 V5 Missions（任务驱动演示主线）
GET  /api/layers          # 获取图层 Tile URL
GET  /api/sentinel2       # 获取 Sentinel-2 影像
POST /api/stats           # 动态统计（reduceRegion）
POST /api/report          # 生成《区域空间监测简报》（模板/LLM）
POST /api/cache/export    # 触发缓存导出
```

## 🤝 对比 Streamlit 版本

### 何时使用 Cesium 版本？

✅ **推荐场景**：
- 高层汇报、大屏展示
- 需要震撼视觉效果
- 强调"行星级底座"叙事
- 演示系统性能和技术实力

❌ **不推荐场景**：
- 快速原型验证
- 简单数据查看
- 低配置设备

### 何时使用 Streamlit 版本？

✅ **推荐场景**：
- 内部技术验证
- 快速迭代开发
- Python 生态集成
- 低复杂度需求

## 🎬 演示话术

### 开场（从太空俯冲）
> "您看到的是我们的 OneEarth 行星级空间智能底座。这不是一张地图，而是一个数字孪生的地球。现在，让我们从太空视角，飞入中国的雄安新区..."

### 切换场景（变化雷达）
> "通过 AI 算法，我们可以识别出 2019 到 2024 年间，地表属性发生本质突变的区域。红色区域代表变化强度，这些都是需要重点关注的执法对象。"

### 揭示依赖（战略反思）
> "但是，各位领导，您刚才看到的震撼画面，底层数据全部来自 Google 的 AlphaEarth。如果明天 Google 封锁 API，这个屏幕就会瞬间全黑。这就是为什么我们必须建设中国版的 AEF。"

## 📝 更新日志

### v1.0.0 (2026-02-19)
- ✅ 完整的前后端分离架构
- ✅ 4 种 AI 监测场景
- ✅ 智能混合加载机制
- ✅ 3D 地球 + 电影级运镜
- ✅ TDD 测试覆盖率 > 80%
- ✅ HUD 赛博朋克界面

## 📄 开源协议

本项目仅供内部演示使用，不对外开源。

## 🙏 致谢

- [CesiumJS](https://cesium.com/) - 开源 3D 地球引擎
- [Google Earth Engine](https://earthengine.google.com/) - 地理空间数据平台
- [Vue 3](https://vuejs.org/) - 渐进式 JavaScript 框架
- [FastAPI](https://fastapi.tiangolo.com/) - 高性能 Python Web 框架

---

**项目状态**: ✅ 生产就绪  
**维护者**: AlphaEarth Team  
**最后更新**: 2026-02-19
