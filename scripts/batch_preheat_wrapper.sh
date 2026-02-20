#!/bin/bash
# 批量预热包装脚本 - 以 alphaearth 用户身份运行
# 用法:
#   sudo bash scripts/batch_preheat_wrapper.sh [--dry-run] [--force]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "🔐 以 alphaearth 用户身份运行批量预热脚本..."
echo "📂 项目根目录: $PROJECT_ROOT"
echo ""

# 将所有参数传递给 Python 脚本
sudo -u alphaearth -H bash -c "
    cd '$PROJECT_ROOT' && \
    source .venv/bin/activate && \
    python scripts/batch_preheat.py $@
"

echo ""
echo "✅ 脚本执行完毕"
