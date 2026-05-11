"""HEALTH detectors: HE-001, HE-002, HE-003 (DETECTORS_v0.1)."""

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

_MRN_LABELS = re.compile(r"\b(MRN|Medical Record|Patient ID|Chart No)\b", re.IGNORECASE)
_MRN_VALUE = re.compile(r"\b[A-Z0-9\-]{4,16}\b")


def _digit_count(s: str) -> int:
    return sum(1 for c in s if c.isdigit())


class MrnDetector:
    """HE-001 — medical record numbers."""

    rule_id: ClassVar[str] = "HE-001"
    category: ClassVar[Category] = "HEALTH"

    def detect(self, doc: Document, policy: Policy) -> list[Finding]:
        out: list[Finding] = []
        for page in doc.pages:
            for block in page.blocks:
                triggers = [
                    line
                    for line in block.lines
                    if _MRN_LABELS.search(" ".join(t.text for t in line.tokens))
                ]
                if not triggers:
                    continue
                for trigger in triggers:
                    for cand in block.lines:
                        same = cand is trigger
                        below = (
                            cand.bbox.y >= trigger.bbox.y2 and cand.bbox.y - trigger.bbox.y2 <= 96
                        )
                        if not (same or below):
                            continue
                        text, spans = line_text_and_offsets(cand)
                        label_match = _MRN_LABELS.search(text) if same else None
                        search_start = label_match.end() if label_match else 0
                        for match in _MRN_VALUE.finditer(text, search_start):
                            value = match.group(0)
                            if _digit_count(value) < 3:
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
                                    matched_text=value,
                                    page_index=page.index,
                                )
                            )
                            break
        return out


_ICD10_RE = re.compile(r"\b[A-TV-Z][0-9]{2}(?:\.[0-9A-TV-Z]{1,4})?\b")


class Icd10Detector:
    """HE-002 — ICD-10 diagnosis codes (OFF by default)."""

    rule_id: ClassVar[str] = "HE-002"
    category: ClassVar[Category] = "HEALTH"

    def detect(self, doc: Document, policy: Policy) -> list[Finding]:
        out: list[Finding] = []
        for page in doc.pages:
            for block in page.blocks:
                for line in block.lines:
                    text, spans = line_text_and_offsets(line)
                    for match in _ICD10_RE.finditer(text):
                        covered = tokens_covering(spans, *match.span())
                        if not covered:
                            continue
                        ocr_conf = confidence_from_tokens(covered)
                        out.append(
                            Finding(
                                rule_id=self.rule_id,
                                category=self.category,
                                bbox=union_bboxes(t.bbox for t in covered),
                                confidence=cap_confidence("medium", ocr_conf),
                                matched_text=match.group(0),
                                page_index=page.index,
                            )
                        )
        return out


_RX_LABEL = re.compile(r"\b(Rx|Prescription|Sig)\b", re.IGNORECASE)


class PrescriptionDetector:
    """HE-003 — prescription details (OFF by default)."""

    rule_id: ClassVar[str] = "HE-003"
    category: ClassVar[Category] = "HEALTH"

    def detect(self, doc: Document, policy: Policy) -> list[Finding]:
        out: list[Finding] = []
        for page in doc.pages:
            for block in page.blocks:
                for line in block.lines:
                    text, spans = line_text_and_offsets(line)
                    match = _RX_LABEL.search(text)
                    if not match:
                        continue
                    end_of_line = len(text)
                    covered = tokens_covering(spans, match.start(), end_of_line)
                    if not covered:
                        continue
                    ocr_conf = confidence_from_tokens(covered)
                    out.append(
                        Finding(
                            rule_id=self.rule_id,
                            category=self.category,
                            bbox=union_bboxes(t.bbox for t in covered),
                            confidence=cap_confidence("medium", ocr_conf),
                            matched_text=text[match.start() :],
                            page_index=page.index,
                        )
                    )
        return out
