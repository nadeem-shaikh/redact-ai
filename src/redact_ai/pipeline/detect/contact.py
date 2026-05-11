"""CONTACT detectors: CO-001, CO-002, CO-003 (DETECTORS_v0.1)."""

from __future__ import annotations

import re
from functools import lru_cache
from importlib.resources import files
from typing import ClassVar

from redact_ai.models.document import Document, Line
from redact_ai.models.findings import Category, Confidence, Finding
from redact_ai.pipeline.detect.base import (
    cap_confidence,
    confidence_from_tokens,
    line_text_and_offsets,
    tokens_covering,
    union_bboxes,
)
from redact_ai.policy.schema import Policy

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,24}\b")


class EmailDetector:
    """CO-001 — email addresses."""

    rule_id: ClassVar[str] = "CO-001"
    category: ClassVar[Category] = "CONTACT"

    def detect(self, doc: Document, policy: Policy) -> list[Finding]:
        out: list[Finding] = []
        for page in doc.pages:
            for block in page.blocks:
                for line in block.lines:
                    text, spans = line_text_and_offsets(line)
                    for match in _EMAIL_RE.finditer(text):
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


_PHONE_RE = re.compile(
    r"(?<![\d/])(?:(\+?\d{1,3})[\s\-.]?)?(?:\(?\d{3}\)?[\s\-.]?)\d{3}[\s\-.]?\d{4}(?!\d)"
)
_PHONE_NEGATIVE = re.compile(r"\b(version|v\.?\d|port|pid)\b", re.IGNORECASE)


class PhoneDetector:
    """CO-002 — international phone numbers."""

    rule_id: ClassVar[str] = "CO-002"
    category: ClassVar[Category] = "CONTACT"

    def detect(self, doc: Document, policy: Policy) -> list[Finding]:
        out: list[Finding] = []
        for page in doc.pages:
            for block in page.blocks:
                for line in block.lines:
                    text, spans = line_text_and_offsets(line)
                    if _PHONE_NEGATIVE.search(text):
                        continue
                    for match in _PHONE_RE.finditer(text):
                        raw = match.group(0)
                        digits = re.sub(r"\D", "", raw)
                        if not 10 <= len(digits) <= 15:
                            continue
                        covered = tokens_covering(spans, *match.span())
                        if not covered:
                            continue
                        ocr_conf = confidence_from_tokens(covered)
                        has_country = match.group(1) is not None and match.group(1).startswith("+")
                        detector_conf: Confidence = "high" if has_country else "medium"
                        out.append(
                            Finding(
                                rule_id=self.rule_id,
                                category=self.category,
                                bbox=union_bboxes(t.bbox for t in covered),
                                confidence=cap_confidence(detector_conf, ocr_conf),
                                matched_text=raw,
                                page_index=page.index,
                            )
                        )
        return out


_STREET_RE = re.compile(
    r"^\d{1,5}[A-Za-z]?\s+[A-Z][\w'.\-]+(\s+[A-Z][\w'.\-]+){0,3}"
    r"\s+(St|Street|Ave|Avenue|Rd|Road|Blvd|Boulevard|Ln|Lane|Dr|Drive|Way|Ct|Court|Pl|Place|Sq|Square)\b",
    re.IGNORECASE,
)
_CITY_STATE_ZIP_RE = re.compile(r"^[A-Z][\w'.\- ]+,?\s+[A-Z]{2}\s+\d{5}(?:-\d{4})?\b")
_ADDRESS_LABELS = re.compile(r"\b(Address|Addr|Mailing)\b", re.IGNORECASE)


@lru_cache(maxsize=1)
def _country_set() -> frozenset[str]:
    text = files("redact_ai.resources").joinpath("countries_en.txt").read_text(encoding="utf-8")
    return frozenset(
        line.strip().lower()
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )


class PostalAddressDetector:
    """CO-003 — multi-line postal addresses."""

    rule_id: ClassVar[str] = "CO-003"
    category: ClassVar[Category] = "CONTACT"

    def detect(self, doc: Document, policy: Policy) -> list[Finding]:
        countries = _country_set()
        out: list[Finding] = []
        for page in doc.pages:
            for block in page.blocks:
                lines = list(block.lines)
                for i, line in enumerate(lines):
                    line_text = " ".join(t.text for t in line.tokens)
                    label_above = i > 0 and _ADDRESS_LABELS.search(
                        " ".join(t.text for t in lines[i - 1].tokens)
                    )
                    is_street = _STREET_RE.search(line_text) is not None
                    if not is_street and not label_above:
                        continue
                    second = lines[i + 1] if i + 1 < len(lines) else None
                    second_text = " ".join(t.text for t in second.tokens) if second else ""
                    both = bool(second) and (
                        _CITY_STATE_ZIP_RE.search(second_text) is not None
                        or second_text.strip().rstrip(",.").lower() in countries
                    )
                    if both and second is not None:
                        confidence: Confidence = "high"
                        span_lines: list[Line] = [line, second]
                    elif label_above and is_street:
                        confidence = "medium"
                        span_lines = [line]
                    else:
                        continue
                    tokens = [t for sl in span_lines for t in sl.tokens]
                    ocr_conf = confidence_from_tokens(tokens)
                    out.append(
                        Finding(
                            rule_id=self.rule_id,
                            category=self.category,
                            bbox=union_bboxes(t.bbox for t in tokens),
                            confidence=cap_confidence(confidence, ocr_conf),
                            matched_text=line_text + (" | " + second_text if both else ""),
                            page_index=page.index,
                        )
                    )
        return out
