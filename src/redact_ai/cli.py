"""CLI stub (BUILD_SPEC §18).

``redact-ai`` with no arguments starts the local web UI. ``--help`` and
``--version`` are handled here. The full subcommand surface ships in
v0.2 per the roadmap.
"""

from __future__ import annotations

import sys

from redact_ai.version import __version__

_USAGE = """redact-ai — privacy-first preprocessing for LLM uploads

Usage:
  redact-ai                Start the local web UI on a loopback port and open
                           it in your default browser.
  redact-ai --help         Show this message.
  redact-ai --version      Print the version and exit.

CLI subcommands ship in v0.2; for now the web UI is the v0.1 surface.
"""


def dispatch(args: list[str]) -> int:
    if not args or args[0] in {"-h", "--help", "help"}:
        sys.stdout.write(_USAGE)
        return 0
    if args[0] in {"--version", "-V", "version"}:
        sys.stdout.write(f"redact-ai {__version__}\n")
        return 0
    sys.stderr.write(
        f"unknown command: {args[0]!r}. Run 'redact-ai --help' or open the web UI.\n"
    )
    return 2
