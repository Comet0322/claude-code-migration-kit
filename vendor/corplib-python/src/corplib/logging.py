"""Minimal real implementation of corplib.logging for migration-kit testing.

Writes one JSON object per line to stdout. Not a description of the real
company log-collector wire format, just enough to be genuinely importable
and runnable.
"""
from __future__ import annotations

import json
import logging
import sys
import time
from typing import Any


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        payload.update(getattr(record, "extra_fields", {}) or {})
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload)


class _ExtraAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        extra = kwargs.pop("extra", None) or {}
        kwargs["extra"] = {"extra_fields": extra}
        return msg, kwargs


def get_logger(name: str) -> logging.LoggerAdapter:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(_JsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return _ExtraAdapter(logger, {})


class RequestLoggingMiddleware:
    """Minimal ASGI middleware for python-corplib-fastapi's template."""

    def __init__(self, app):
        self.app = app
        self._logger = get_logger("corplib.request")

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        self._logger.info("request", extra={"path": scope.get("path")})
        await self.app(scope, receive, send)
