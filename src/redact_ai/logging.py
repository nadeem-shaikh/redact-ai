"""Structured JSON logging (BUILD_SPEC §14.5).

Logs are emitted as one JSON object per line to ``stderr``. A redaction
filter drops any field named ``text``, ``bytes``, ``matched_text``, or
``b64`` so that user content cannot leak via the log stream
(NFR-8.2, SECURITY §3).
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

_SENSITIVE_FIELDS: frozenset[str] = frozenset({"text", "bytes", "matched_text", "b64"})


class RedactionFilter(logging.Filter):
    """Strip any sensitive-named field from log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        fields = getattr(record, "fields", None)
        if isinstance(fields, dict):
            record.fields = _strip(fields)
        return True


def _strip(fields: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in fields.items():
        if key in _SENSITIVE_FIELDS:
            continue
        if isinstance(value, dict):
            out[key] = _strip(value)
        else:
            out[key] = value
    return out


class JsonFormatter(logging.Formatter):
    """Render log records as one JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.now(tz=timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname.lower(),
            "event": record.getMessage(),
        }
        for attr in ("request_id", "stage", "duration_ms"):
            value = getattr(record, attr, None)
            if value is not None:
                payload[attr] = value
        fields = getattr(record, "fields", None)
        if isinstance(fields, dict):
            payload["fields"] = fields
        if record.exc_info:
            payload["error"] = self.formatException(record.exc_info)
        return json.dumps(payload, separators=(",", ":"), sort_keys=True)


_configured = False


def configure(level: int = logging.INFO) -> None:
    """Idempotently install the JSON formatter + redaction filter on stderr."""
    global _configured
    if _configured:
        return
    root = logging.getLogger("redact_ai")
    root.setLevel(level)
    root.handlers.clear()
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(RedactionFilter())
    root.addHandler(handler)
    root.propagate = False
    _configured = True


def get_logger(name: str) -> logging.Logger:
    configure()
    return logging.getLogger(f"redact_ai.{name}")
