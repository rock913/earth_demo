#!/bin/bash
# AlphaEarth Cesium Frontend 启动脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 Starting AlphaEarth Cesium Frontend..."

# 加载 .env 文件（如果存在）
if [ -f ".env" ]; then
    echo "📋 Loading environment from .env..."
    export $(cat .env | grep -v '^#' | grep -v '^$' | xargs)
fi

# 进入前端目录
cd frontend

# 检查 node_modules
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# 启动前端
echo "✅ Frontend starting on http://127.0.0.1:${FRONTEND_PORT:-8502}"
npm run dev -- --port ${FRONTEND_PORT:-8502}
