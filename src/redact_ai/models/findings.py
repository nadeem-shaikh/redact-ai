"""Internal Finding records (BUILD_SPEC §7, REDACTION_RULES §5)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from redact_ai.models.document import BBox

Category = Literal[
    "IDENTITY", "CONTACT", "FINANCIAL", "HEALTH", "CREDENTIALS", "LOCATION", "CUSTOM"
]
Confidence = Literal["low", "medium", "high"]

_CONFIDENCE_ORDER: dict[Confidence, int] = {"low": 0, "medium": 1, "high": 2}


def confidence_min(a: Confidence, b: Confidence) -> Confidence:
    """Return the lower of two confidence levels."""
    return a if _CONFIDENCE_ORDER[a] <= _CONFIDENCE_ORDER[b] else b


def confidence_max(a: Confidence, b: Confidence) -> Confidence:
    return a if _CONFIDENCE_ORDER[a] >= _CONFIDENCE_ORDER[b] else b


def confidence_ge(a: Confidence, b: Confidence) -> bool:
    return _CONFIDENCE_ORDER[a] >= _CONFIDENCE_ORDER[b]


class Finding(BaseModel):
    """A single detected sensitive entity (pre-merge, pre-projection)."""

    model_config = {"frozen": True}

    rule_id: str
    category: Category
    bbox: BBox
    confidence: Confidence
    matched_text: str = Field(default="")
    page_index: int = Field(default=0, ge=0)
    merged_from: tuple[str, ...] = ()
