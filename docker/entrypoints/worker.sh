#!/bin/sh
set -e

mkdir -p /app/data /app/logs
uv run python -m storage.init_db

exec uv run python autopublish.py
