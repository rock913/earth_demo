#!/bin/bash
# AlphaEarth Cesium 环境配置脚本
# 交互式配置 .env 文件

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "╔════════════════════════════════════════════════╗"
echo "║   🔧 AlphaEarth Cesium 环境配置向导            ║"
echo "╚════════════════════════════════════════════════╝"
echo ""

# 检查是否已存在 .env
if [ -f ".env" ]; then
    echo "⚠️  检测到已存在的 .env 文件"
    read -p "是否要覆盖? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ 取消配置"
        exit 0
    fi
    echo ""
fi

echo "请按照提示输入配置信息（按 Enter 使用默认值）"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# GEE_USER_PATH
echo "【必需】GEE 用户路径"
echo "示例: users/zhangsan/aef_demo"
echo "说明: 用于存放缓存 Assets 的 GEE 目录"
read -p "GEE_USER_PATH: " gee_user_path
if [ -z "$gee_user_path" ]; then
    echo "❌ GEE_USER_PATH 不能为空"
    exit 1
fi
echo ""

# EE_SERVICE_ACCOUNT
echo "【可选】GEE 服务账号邮箱（生产环境推荐）"
echo "示例: my-service@my-project.iam.gserviceaccount.com"
read -p "EE_SERVICE_ACCOUNT (留空跳过): " ee_service_account
echo ""

# EE_PRIVATE_KEY_FILE
if [ ! -z "$ee_service_account" ]; then
    echo "【可选】GEE 服务账号 JSON 密钥文件路径"
    echo "示例: /etc/alphaearth/service-account-key.json"
    read -p "EE_PRIVATE_KEY_FILE: " ee_private_key_file
    echo ""
fi

# API_HOST
echo "【可选】后端 API 监听地址"
read -p "API_HOST (默认: 127.0.0.1): " api_host
api_host=${api_host:-127.0.0.1}
echo ""

# API_PORT
echo "【可选】后端 API 端口"
read -p "API_PORT (默认: 8503): " api_port
api_port=${api_port:-8503}
echo ""

# FRONTEND_PORT
echo "【可选】前端端口"
read -p "FRONTEND_PORT (默认: 8502): " frontend_port
frontend_port=${frontend_port:-8502}
echo ""

# VITE_CESIUM_TOKEN
echo "【可选】Cesium Ion Access Token"
echo "获取地址: https://ion.cesium.com/tokens"
read -p "VITE_CESIUM_TOKEN (留空跳过): " cesium_token
echo ""

# 生成 .env 文件
echo "📝 正在生成 .env 文件..."

cat > .env << EOF
# AlphaEarth Cesium 环境变量配置
# 生成时间: $(date '+%Y-%m-%d %H:%M:%S')

# ==================== GEE 配置 ====================
GEE_USER_PATH=$gee_user_path
EOF

if [ ! -z "$ee_service_account" ]; then
    cat >> .env << EOF

# GEE 服务账号（生产环境）
EE_SERVICE_ACCOUNT=$ee_service_account
EOF
fi

if [ ! -z "$ee_private_key_file" ]; then
    cat >> .env << EOF
EE_PRIVATE_KEY_FILE=$ee_private_key_file
EOF
fi

cat >> .env << EOF

# ==================== 服务器配置 ====================
API_HOST=$api_host
API_PORT=$api_port
FRONTEND_PORT=$frontend_port
EOF

if [ ! -z "$cesium_token" ]; then
    cat >> .env << EOF

# ==================== Cesium 配置 ====================
VITE_CESIUM_TOKEN=$cesium_token
EOF
fi

cat >> .env << EOF

# ==================== 开发配置 ====================
TESTING=0
LOG_LEVEL=INFO
EOF

echo "✅ .env 文件已生成"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "配置摘要:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "GEE 用户路径: $gee_user_path"
echo "后端地址: http://$api_host:$api_port"
echo "前端地址: http://127.0.0.1:$frontend_port"
if [ ! -z "$ee_service_account" ]; then
    echo "服务账号: $ee_service_account"
fi
if [ ! -z "$cesium_token" ]; then
    echo "Cesium Token: 已配置"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🚀 下一步:"
echo "   1. 确认配置: cat .env"
echo "   2. 启动服务: ./start.sh"
echo ""
