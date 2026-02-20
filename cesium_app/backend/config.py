"""
Configuration for Cesium Backend
"""
import os
from pathlib import Path
from pydantic import BaseModel
from dotenv import load_dotenv

# 加载 .env 文件（从 cesium_app 根目录）
# 使用绝对路径确保无论工作目录在哪都能正确找到
env_path = Path(__file__).resolve().parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
    print(f"✅ 已加载环境变量: {env_path}")
else:
    print(f"⚠️  未找到 .env 文件: {env_path}，使用默认配置")


class Settings(BaseModel):
    """Application settings"""
    
    # GEE Configuration
    gee_user_path: str = os.getenv("GEE_USER_PATH", "users/default/aef_demo")
    ee_service_account: str = os.getenv("EE_SERVICE_ACCOUNT", "")
    ee_private_key_file: str = os.getenv("EE_PRIVATE_KEY_FILE", "")
    
    # Server Configuration
    api_host: str = os.getenv("API_HOST", "127.0.0.1")
    api_port: int = int(os.getenv("API_PORT", "8503"))

    # LLM (OpenAI compatible)
    # DashScope compatible-mode example:
    #   LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
    #   LLM_API_KEY=...
    #   LLM_MODEL=qwen-plus
    llm_base_url: str = os.getenv(
        "LLM_BASE_URL",
        "https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_model: str = os.getenv("LLM_MODEL", "qwen-plus")
    llm_timeout_s: float = float(os.getenv("LLM_TIMEOUT_S", "12"))
    llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.2"))
    llm_max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "512"))

    # Map viewport buffer (meters)
    # Used for backend-side filterBounds region when generating AI layers.
    viewport_buffer_m: int = int(os.getenv("VIEWPORT_BUFFER_M", "150000"))
    
    # CORS Configuration
    cors_origins: list = ["http://localhost:8502", "http://127.0.0.1:8502"]
    
    # Location Database
    locations: dict = {
        "shanghai": {
            "coords": [31.2304, 121.5000, 14],
            "name": "上海 · 陆家嘴",
            "code": "shanghai"
        },
        "beijing": {
            "coords": [39.9042, 116.7000, 13],
            "name": "北京 · 通州",
            "code": "beijing"
        },
        "xiongan": {
            "coords": [39.0500, 115.9800, 12],
            "name": "河北 · 雄安",
            "code": "xiongan"
        },
        "hangzhou": {
            "coords": [30.2450, 120.1400, 14],
            "name": "杭州 · 西湖",
            "code": "hangzhou"
        },
        "shenzhen": {
            "coords": [22.5000, 113.9500, 13],
            "name": "深圳 · 湾区",
            "code": "shenzhen"
        },

        # V5 Missions (whitepaper) default targets
        "zhoukou": {
            "coords": [33.6250, 114.6500, 11],
            "name": "河南周口 · 农作物健康体检",
            "code": "zhoukou"
        },
        "maowusu": {
            "coords": [38.5000, 109.6000, 10],
            "name": "毛乌素沙地 · 三北防护林演变",
            "code": "maowusu"
        },
        "gba": {
            "coords": [22.7500, 113.7000, 10],
            "name": "粤港澳大湾区 · 无序扩张监测",
            "code": "gba"
        },
    }
    
    # AI Modes
    modes: dict = {
        "dna": "地表 DNA (语义视图)",
        "change": "变化雷达 (敏捷治理)",
        "intensity": "建设强度 (宏观管控)",
        "eco": "生态韧性 (绿色底线)",
    }

    # V5 mission registry (ordered)
    # NOTE: Keep this list order stable; front-end uses it as the default narrative sequence.
    missions: list = [
        {
            "id": "agri_zhoukou",
            "name": "农业安全",
            "title": "河南周口 · 农作物健康体检",
            "location": "zhoukou",
            "api_mode": "eco",
            "formula": "AEF_Inverse(Dim_2)",
            "narrative": "利用 AEF 特征反演农田生长韧性，识别内涝、病虫害等结构性胁迫。",
            "camera": {"lat": 33.6250, "lon": 114.6500, "height": 12000, "duration_s": 3.5},
        },
        {
            "id": "eco_maowusu",
            "name": "生态红线",
            "title": "毛乌素沙地 · 三北防护林演变",
            "location": "maowusu",
            "api_mode": "change",
            "formula": "Distance(V_2019, V_2024)",
            "narrative": "跨 5 年的时空特征距离，过滤季节性变化，锁定本质性地表退化。",
            "camera": {"lat": 38.5000, "lon": 109.6000, "height": 18000, "duration_s": 3.8},
        },
        {
            "id": "urban_gba",
            "name": "城市治理",
            "title": "粤港澳大湾区 · 无序扩张监测",
            "location": "gba",
            "api_mode": "intensity",
            "formula": "Normalize(Dim_0)",
            "narrative": "提取对人造地表敏感的通道，生成全域开发强度场，刻画连片蔓延趋势。",
            "camera": {"lat": 22.7500, "lon": 113.7000, "height": 20000, "duration_s": 3.5},
        },
    ]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
