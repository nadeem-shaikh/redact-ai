"""``python -m redact_ai`` and the ``redact-ai`` console script entry point.

In v0.1 this is the only user-facing surface: it starts the local web
UI on a loopback port and opens the browser. The CLI subcommand surface
ships in v0.2 (see ROADMAP).
"""

from __future__ import annotations

import sys

from redact_ai.cli import dispatch
from redact_ai.server import serve


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args:
        return dispatch(args)
    serve()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
