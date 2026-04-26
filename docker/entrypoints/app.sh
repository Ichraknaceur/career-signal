#!/bin/sh
set -e

mkdir -p /app/data /app/logs
uv run python -m storage.init_db

exec uv run streamlit run ui/app.py \
  --server.port=8501 \
  --server.address=0.0.0.0 \
  --server.headless=true \
  --browser.gatherUsageStats=false
