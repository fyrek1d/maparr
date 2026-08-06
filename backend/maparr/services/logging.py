"""Structured logging for the application."""

from __future__ import annotations

import json
import logging
import sys
import time

from ..config import get_settings


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created)) + f".{int(record.msecs):03d}Z",
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        for key in ("event", "map_id", "user", "provider", "status", "duration_ms"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        return json.dumps(payload)


def setup_logging() -> None:
    settings = get_settings()
    root = logging.getLogger()
    root.setLevel(settings.log_level.upper())
    handler = logging.StreamHandler(sys.stdout)
    if settings.json_logs:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)-7s %(name)s: %(message)s", "%H:%M:%S"
        ))
    root.handlers = [handler]
    # Keep uvicorn access logs but silence its internal noise at debug level.
    logging.getLogger("uvicorn.error").handlers = []
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


log = logging.getLogger("maparr")


class EventAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        extra = kwargs.get("extra", {})
        if "event" in extra:
            kwargs["extra"] = extra
        return msg, kwargs


def get_logger(name: str = "maparr") -> logging.Logger:
    return logging.getLogger(name)
