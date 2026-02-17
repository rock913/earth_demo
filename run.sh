#!/usr/bin/env bash
set -euo pipefail

PORT="${PORT:-8501}"
HOST="${HOST:-0.0.0.0}"

if [[ -x "./.venv/bin/python" ]]; then
  exec ./.venv/bin/python -m streamlit run app.py \
    --server.address "$HOST" \
    --server.port "$PORT"
else
  exec streamlit run app.py \
    --server.address "$HOST" \
    --server.port "$PORT"
fi
