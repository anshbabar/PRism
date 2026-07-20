"""Structured (JSON) logging with secret redaction.

Uses only the standard library so the backend stays dependency-light. Every log
record is emitted as a single JSON line, which is friendly to log aggregators and
trivially greppable in local dev.

Secret redaction is defense-in-depth: even if a token slips into a log message,
common secret shapes (GitHub PATs, Anthropic keys, bearer tokens) are masked
before the line is written.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime

# Patterns for common secret shapes. Redaction is best-effort, not a substitute
# for not logging secrets in the first place.
_SECRET_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),  # GitHub tokens
    re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}"),  # Anthropic keys
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._-]{20,}"),  # bearer tokens
]
_REDACTED = "[REDACTED]"

# Standard LogRecord attributes we don't want to duplicate into the JSON "extra".
_RESERVED = set(logging.makeLogRecord({}).__dict__) | {"message", "asctime", "taskName"}


def _redact(text: str) -> str:
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub(_REDACTED, text)
    return text


class JsonFormatter(logging.Formatter):
    """Format log records as single-line JSON with redaction."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": _redact(record.getMessage()),
        }

        # Merge any structured extras passed via logger.info(..., extra={...}).
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                payload[key] = _redact(value) if isinstance(value, str) else value

        if record.exc_info:
            payload["exception"] = _redact(self.formatException(record.exc_info))

        return json.dumps(payload, default=str)


def configure_logging(level: str = "info") -> None:
    """Configure the root logger to emit JSON to stdout.

    Idempotent: replaces any existing handlers so repeated calls (e.g. app
    reloads, test setup) don't stack duplicate output.
    """
    root = logging.getLogger()
    root.handlers.clear()

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    root.setLevel(level.upper())


def get_logger(name: str) -> logging.Logger:
    """Return a module-scoped logger."""
    return logging.getLogger(name)
