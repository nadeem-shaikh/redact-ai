"""OCR adapters (BUILD_SPEC §7, ADR-008)."""

from redact_ai.pipeline.ocr.base import OCRAdapter
from redact_ai.pipeline.ocr.tesseract import TesseractAdapter

__all__ = ["OCRAdapter", "TesseractAdapter"]
