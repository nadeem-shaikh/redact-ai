"""CLI stub tests (BUILD_SPEC §18)."""

from __future__ import annotations

import pytest

from redact_ai.cli import dispatch


def test_help_prints_usage(capsys: pytest.CaptureFixture[str]) -> None:
    rc = dispatch(["--help"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "redact-ai" in out
    assert "web UI" in out


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    rc = dispatch(["--version"])
    assert rc == 0
    assert "redact-ai" in capsys.readouterr().out


def test_unknown_command(capsys: pytest.CaptureFixture[str]) -> None:
    rc = dispatch(["nope"])
    assert rc == 2
    assert "unknown" in capsys.readouterr().err


def test_dispatch_empty_args_shows_help(capsys: pytest.CaptureFixture[str]) -> None:
    rc = dispatch([])
    assert rc == 0
    assert "Usage" in capsys.readouterr().out
