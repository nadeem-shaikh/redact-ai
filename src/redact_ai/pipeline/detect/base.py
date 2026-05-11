"""Detector contract and shared helpers (DETECTORS_v0.1)."""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import ClassVar, Protocol

from redact_ai.models.document import BBox, Document, Line, Token
from redact_ai.models.findings import Category, Confidence, Finding, confidence_min
from redact_ai.policy.schema import DetectorRef, Policy


class Detector(Protocol):
    """Common protocol for every per-rule detector."""

    rule_id: ClassVar[str]
    category: ClassVar[Category]

    def detect(self, doc: Document, policy: Policy) -> list[Finding]: ...


def policy_override(policy: Policy, rule_id: str) -> DetectorRef | None:
    for det in policy.detectors:
        if det.id == rule_id:
            return det
    return None


def union_bboxes(boxes: Iterable[BBox]) -> BBox:
    bboxes = list(boxes)
    if not bboxes:
        raise ValueError("union_bboxes requires at least one bbox")
    out = bboxes[0]
    for b in bboxes[1:]:
        out = out.union(b)
    return out


def line_text_and_offsets(line: Line) -> tuple[str, list[tuple[int, int, Token]]]:
    """Return the joined line text and the (start, end, token) span list.

    The joined text uses single spaces, matching the rule in DETECTORS_v0.1
    ("regex is applied to the line text — tokens joined by single spaces").
    """
    pieces: list[str] = []
    spans: list[tuple[int, int, Token]] = []
    cursor = 0
    for idx, tok in enumerate(line.tokens):
        if idx:
            cursor += 1  # the joining space
            pieces.append(" ")
        start = cursor
        pieces.append(tok.text)
        cursor += len(tok.text)
        spans.append((start, cursor, tok))
    return "".join(pieces), spans


def tokens_covering(
    spans: list[tuple[int, int, Token]], char_start: int, char_end: int
) -> list[Token]:
    """Return every token whose character range overlaps ``[char_start, char_end)``."""
    out: list[Token] = []
    for s, e, tok in spans:
        if s < char_end and e > char_start:
            out.append(tok)
    return out


def confidence_from_tokens(tokens: Iterable[Token]) -> Confidence:
    """Map the minimum OCR confidence among ``tokens`` to a finding floor
    (BUILD_SPEC §12.1)."""
    confs = [t.confidence for t in tokens]
    if not confs:
        return "low"
    low = min(confs)
    if low >= 0.85:
        return "high"
    if low >= 0.60:
        return "medium"
    return "low"


def cap_confidence(detector_conf: Confidence, ocr_conf: Confidence) -> Confidence:
    """A finding's confidence is the min of the detector's own confidence
    and the OCR-derived floor (BUILD_SPEC §12.1)."""
    return confidence_min(detector_conf, ocr_conf)


WORD_RE = re.compile(r"\b[\w'.\-]+\b")


def bbox_distance(a: BBox, b: BBox) -> int:
    """Manhattan-ish gap between two non-overlapping bboxes; ``0`` if overlapping."""
    dx = max(a.x - b.x2, b.x - a.x2, 0)
    dy = max(a.y - b.y2, b.y - a.y2, 0)
    return dx + dy
