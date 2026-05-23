"""Structured JSON logging for production observability.

Addresses MIMO Category 13 gap: "no structured logging in production."
Drop-in replacement for `logging.getLogger(__name__)` that emits JSON lines
to stderr alongside the standard text formatter so existing log consumers
aren't broken.

Usage:
    from tools.structured_logger import get_logger
    log = get_logger(__name__)
    log.info("pick resolved", extra={"pick_id": "abc", "pnl_pct": 1.23})

The extra dict fields are lifted into the JSON payload as top-level keys.
JSON lines go to stderr (or STRUCTURED_LOG_FILE env path).
Text logging continues to the root handler as usual.

Kill-switch: STRUCTURED_LOGGING_ENABLED=0 (default: 1)
"""
from __future__ import annotations

import json
import logging
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_ENABLED = os.environ.get("STRUCTURED_LOGGING_ENABLED", "1").strip() not in ("0", "false", "no")
_LOG_FILE = os.environ.get("STRUCTURED_LOG_FILE", "")

_SERVICE = os.environ.get("SERVICE_NAME", "antigravity-trading")
_ENV = os.environ.get("DEPLOY_ENV", "production")


class _JsonFormatter(logging.Formatter):
    """Formats log records as newline-delimited JSON."""

    _SKIP_KEYS = frozenset({
        "name", "msg", "args", "levelname", "levelno", "pathname",
        "filename", "module", "exc_info", "exc_text", "stack_info",
        "lineno", "funcName", "created", "msecs", "relativeCreated",
        "thread", "threadName", "processName", "process", "message",
        "taskName",
    })

    def format(self, record: logging.LogRecord) -> str:
        record.message = record.getMessage()
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.message,
            "service": _SERVICE,
            "env": _ENV,
            "file": f"{record.filename}:{record.lineno}",
        }
        # Lift user-supplied extra fields
        for k, v in record.__dict__.items():
            if k not in self._SKIP_KEYS:
                try:
                    json.dumps(v)  # ensure JSON-serializable
                    payload[k] = v
                except (TypeError, ValueError):
                    payload[k] = str(v)

        if record.exc_info:
            payload["exception"] = traceback.format_exception(*record.exc_info)

        return json.dumps(payload, ensure_ascii=False)


def _build_json_handler() -> logging.Handler:
    if _LOG_FILE:
        path = Path(_LOG_FILE)
        path.parent.mkdir(parents=True, exist_ok=True)
        handler: logging.Handler = logging.FileHandler(path, encoding="utf-8")
    else:
        handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(_JsonFormatter())
    return handler


_json_handler: logging.Handler | None = None


def _get_json_handler() -> logging.Handler:
    global _json_handler
    if _json_handler is None:
        _json_handler = _build_json_handler()
    return _json_handler


def get_logger(name: str, level: int = logging.DEBUG) -> logging.Logger:
    """Return a logger that emits structured JSON lines in addition to text.

    The JSON handler is attached directly to the named logger (not the root)
    so it can be toggled per-module without affecting unrelated loggers.
    propagate=True is preserved so parent/root handlers still receive records.
    """
    logger = logging.getLogger(name)

    if _ENABLED:
        json_h = _get_json_handler()
        json_h.setLevel(level)
        # Don't add duplicate handlers on re-import
        if not any(isinstance(h, type(json_h)) for h in logger.handlers):
            logger.addHandler(json_h)

    return logger


def log_event(
    logger: logging.Logger,
    level: int,
    msg: str,
    **fields: Any,
) -> None:
    """Emit a structured log event with arbitrary key-value fields.

    Example:
        log_event(log, logging.INFO, "gate_reject",
                  pick_id="abc", gate="FOREX_HARD_DISABLE", asset_class="FOREX")
    """
    logger.log(level, msg, extra=fields)
