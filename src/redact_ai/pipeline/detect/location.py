"""LOCATION detectors: LO-001 (DETECTORS_v0.1).

LO-002 (vehicle plates) is intentionally not implemented in v0.1 and
is absent from the registry per DETECTORS_v0.1 §Registry.
"""

from __future__ import annotations

import re
from typing import ClassVar

from redact_ai.models.document import Document
from redact_ai.models.findings import Category, Finding
from redact_ai.pipeline.detect.base import (
    cap_confidence,
    confidence_from_tokens,
    line_text_and_offsets,
    tokens_covering,
    union_bboxes,
)
from redact_ai.policy.schema import Policy

_GPS_RE = re.compile(
    r"(?<![\d.])(-?(?:[1-8]?\d(?:\.\d+)?|90(?:\.0+)?))\s*(°)?\s*([NS])?"
    r"\s*[, ]\s*"
    r"(-?(?:1[0-7]\d(?:\.\d+)?|180(?:\.0+)?|\d{1,2}(?:\.\d+)?))\s*(°)?\s*([EW])?(?![\d.])"
)
# At least one of the optional decoration groups must be present so we
# don't fire on bare number pairs (e.g. phone fragments "44 20"). The
# spec's confidence floor is HIGH, which is only defensible when the
# match looks unambiguously like a coordinate.
_GPS_DECORATION_GROUPS = (2, 3, 5, 6)


class GpsCoordsDetector:
    """LO-001 — GPS coordinates (decimal degrees)."""

    rule_id: ClassVar[str] = "LO-001"
    category: ClassVar[Category] = "LOCATION"

    def detect(self, doc: Document, policy: Policy) -> list[Finding]:
        out: list[Finding] = []
        for page in doc.pages:
            for block in page.blocks:
                for line in block.lines:
                    text, spans = line_text_and_offsets(line)
                    for match in _GPS_RE.finditer(text):
                        try:
                            lat = float(match.group(1))
                            lon = float(match.group(4))
                        except ValueError:
                            continue
                        if not (-90.0 <= lat <= 90.0):
                            continue
                        if not (-180.0 <= lon <= 180.0):
                            continue
                        if not any(match.group(g) for g in _GPS_DECORATION_GROUPS):
                            continue
                        covered = tokens_covering(spans, *match.span())
                        if not covered:
                            continue
                        ocr_conf = confidence_from_tokens(covered)
                        out.append(
                            Finding(
                                rule_id=self.rule_id,
                                category=self.category,
                                bbox=union_bboxes(t.bbox for t in covered),
                                confidence=cap_confidence("high", ocr_conf),
                                matched_text=match.group(0),
                                page_index=page.index,
                            )
                        )
        return out
