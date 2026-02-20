#!/bin/bash
# AlphaEarth Cesium 一键启动脚本
# 自动启动后端和前端服务

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "╔════════════════════════════════════════════════╗"
echo "║   🌍 AlphaEarth Cesium 启动器                  ║"
echo "║   OneEarth Command System                      ║"
echo "╚════════════════════════════════════════════════╝"
echo ""

# 加载 .env 文件
if [ -f ".env" ]; then
    echo "📋 加载环境变量 (.env)..."
    export $(cat .env | grep -v '^#' | grep -v '^$' | xargs)
    echo "✅ 环境变量已加载"
else
    echo "⚠️  未找到 .env 文件"
    echo "💡 建议: 复制 .env.example 为 .env 并配置"
    echo ""
fi

# 检查环境
echo "📋 环境检查..."

# 检查 Python（优先使用 workspace .venv / python3.11 / python）
PYTHON_BIN=""
if [ -x "$SCRIPT_DIR/.venv/bin/python" ]; then
    PYTHON_BIN="$SCRIPT_DIR/.venv/bin/python"
elif command -v python3.11 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3.11)"
elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python)"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
else
    echo "❌ Python 未安装，请先安装 Python 3.9+"
    exit 1
fi

PY_VER=$($PYTHON_BIN -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)
if [ "$PY_MAJOR" -lt 3 ] || [ "$PY_MINOR" -lt 9 ]; then
    echo "❌ Python 版本过低: $($PYTHON_BIN -V)（需要 Python 3.9+）"
    exit 1
fi
echo "✅ Python: $($PYTHON_BIN -V)"

# 检查 Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js 未安装，请先安装 Node.js 18+"
    exit 1
fi
echo "✅ Node.js: $(node --version)"

# 检查 GEE 配置
if [ -z "$GEE_USER_PATH" ]; then
    echo "⚠️  警告: GEE_USER_PATH 未设置，将使用默认值"
    echo "   建议设置: export GEE_USER_PATH=\"users/your_username/aef_demo\""
fi

echo ""
echo "🚀 启动服务..."
echo ""

# 创建日志目录
mkdir -p logs

# 启动后端
echo "📡 启动后端 (端口 8503)..."
./run_backend.sh > logs/backend.log 2>&1 &
BACKEND_PID=$!
echo "   PID: $BACKEND_PID"
echo "   日志: logs/backend.log"

# 等待后端启动
echo "   等待后端就绪..."
sleep 3

# 检查后端是否启动成功
if ! curl -s http://127.0.0.1:8503/health > /dev/null 2>&1; then
    echo "❌ 后端启动失败，请查看 logs/backend.log"
    kill $BACKEND_PID 2>/dev/null || true
    exit 1
fi
echo "✅ 后端就绪"

# 启动前端
echo ""
echo "🎨 启动前端 (端口 8502)..."
./run_frontend.sh > logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo "   PID: $FRONTEND_PID"
echo "   日志: logs/frontend.log"

# 等待前端启动
echo "   等待前端就绪..."
sleep 5

echo ""
echo "╔════════════════════════════════════════════════╗"
echo "║   ✅ 启动完成！                                 ║"
echo "╚════════════════════════════════════════════════╝"
echo ""
echo "🌐 访问地址:"
echo "   前端: http://127.0.0.1:8502"
echo "   后端: http://127.0.0.1:8503/docs"
echo ""
echo "📊 进程信息:"
echo "   后端 PID: $BACKEND_PID"
echo "   前端 PID: $FRONTEND_PID"
echo ""
echo "📝 日志文件:"
echo "   后端: logs/backend.log"
echo "   前端: logs/frontend.log"
echo ""
echo "⏹️  停止服务:"
echo "   kill $BACKEND_PID $FRONTEND_PID"
echo "   或按 Ctrl+C"
echo ""

# 保存 PID 到文件
echo "$BACKEND_PID" > logs/backend.pid
echo "$FRONTEND_PID" > logs/frontend.pid

# 等待用户中断
trap "echo ''; echo '🛑 正在停止服务...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true; echo '✅ 服务已停止'; exit 0" INT TERM

echo "按 Ctrl+C 停止服务..."
wait
