"""OCR adapter contract (BUILD_SPEC §7, OCR_PIPELINE_v0.1 §4)."""

from __future__ import annotations

from typing import Protocol

from redact_ai.models.document import Document
from redact_ai.pipeline.ingest import IngestedImage


class OCRAdapter(Protocol):
    """Engine-agnostic interface for OCR backends.

    Implementations MUST return a :class:`~redact_ai.models.document.Document`
    whose bbox coordinates are in the *post-preprocessing* pixel space
    (the ``ingested.normalised`` image), with stable IDs derived from
    position.
    """

    def engine_id(self) -> str:  # e.g. "tesseract-5.3.4"
        ...

    def recognise(self, ingested: IngestedImage) -> Document:
        ...
