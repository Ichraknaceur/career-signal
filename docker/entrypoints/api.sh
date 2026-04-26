#!/bin/sh
set -e

mkdir -p /app/data /app/logs
uv run python -m storage.init_db

exec uv run uvicorn app.api.main:app \
  --host 0.0.0.0 \
  --port 8000
