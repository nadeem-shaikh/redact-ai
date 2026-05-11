"""Logging filter ensures we never log raw user content (BUILD_SPEC §14.5)."""

from __future__ import annotations

import json
import logging

from redact_ai.logging import JsonFormatter, RedactionFilter, configure, get_logger


def test_redaction_filter_drops_sensitive_fields() -> None:
    record = logging.LogRecord("x", logging.INFO, "p", 0, "msg", None, None)
    record.fields = {"text": "leak", "ok": "kept", "matched_text": "leak"}
    RedactionFilter().filter(record)
    assert record.fields == {"ok": "kept"}


def test_redaction_filter_handles_nested_dict() -> None:
    record = logging.LogRecord("x", logging.INFO, "p", 0, "msg", None, None)
    record.fields = {"meta": {"text": "leak", "ok": 1}}
    RedactionFilter().filter(record)
    assert record.fields == {"meta": {"ok": 1}}


def test_json_formatter_emits_one_line_json() -> None:
    record = logging.LogRecord("x", logging.INFO, "p", 0, "hello", None, None)
    record.request_id = "abc"
    record.stage = "ingest"
    record.fields = {"ok": True}
    out = JsonFormatter().format(record)
    payload = json.loads(out)
    assert payload["event"] == "hello"
    assert payload["request_id"] == "abc"
    assert payload["stage"] == "ingest"
    assert payload["fields"] == {"ok": True}


def test_configure_is_idempotent() -> None:
    configure()
    configure()
    log = get_logger("test")
    assert log.name == "redact_ai.test"
