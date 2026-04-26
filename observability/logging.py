"""
Logging helpers for the refactored architecture.

This module centralises file + console logging so workers and UI can share
the same runtime conventions.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any


def _json_formatter(record: logging.LogRecord) -> str:
    payload: dict[str, Any] = {
        "ts": datetime.utcnow().isoformat() + "Z",
        "level": record.levelname,
        "logger": record.name,
        "message": record.getMessage(),
    }
    if hasattr(record, "run_id"):
        payload["run_id"] = record.run_id
    if hasattr(record, "entity_id"):
        payload["entity_id"] = record.entity_id
    if record.exc_info:
        payload["exception"] = logging.Formatter().formatException(record.exc_info)
    return json.dumps(payload, ensure_ascii=True)


class JsonLineFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return _json_formatter(record)


def configure_logging(
    level: str = "INFO",
    log_dir: str | None = None,
    service_name: str = "career-signal",
) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )

    resolved_log_dir = log_dir if log_dir is not None else os.getenv("LOG_DIR") or "data/logs"
    directory = Path(resolved_log_dir)
    directory.mkdir(parents=True, exist_ok=True)
    log_file = directory / f"{service_name}.jsonl"

    root = logging.getLogger()
    if any(isinstance(handler, logging.FileHandler) for handler in root.handlers):
        return

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
    file_handler.setFormatter(JsonLineFormatter())
    root.addHandler(file_handler)
