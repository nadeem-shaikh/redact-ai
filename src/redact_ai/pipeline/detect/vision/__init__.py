"""Vision detectors operate on the original image, not OCR output (ADR-012)."""

from __future__ import annotations

from typing import ClassVar, Protocol

from PIL import Image

from redact_ai.models.findings import Category, Finding
from redact_ai.policy.schema import Policy


class VisionDetector(Protocol):
    """Common protocol for detectors that consume pixels, not OCR tokens."""

    rule_id: ClassVar[str]
    category: ClassVar[Category]

    def detect(self, image: Image.Image, policy: Policy) -> list[Finding]: ...
