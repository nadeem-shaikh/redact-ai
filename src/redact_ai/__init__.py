"""redact-ai: privacy-first preprocessing for LLM uploads.

The public Python surface is intentionally small for v0.1: import the
:func:`redact` entry point, build a :class:`~redact_ai.policy.schema.Policy`,
and call it. The local web UI is the recommended user surface (ADR-007).
"""

from redact_ai.errors import RedactError
from redact_ai.pipeline import redact
from redact_ai.version import __version__

__all__ = ["RedactError", "__version__", "redact"]
