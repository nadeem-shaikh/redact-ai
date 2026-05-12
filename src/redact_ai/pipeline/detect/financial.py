"""FINANCIAL detectors: FI-001..FI-004 (DETECTORS_v0.1)."""

from __future__ import annotations

import re
from typing import ClassVar

from redact_ai.models.document import BBox, Document
from redact_ai.models.findings import Category, Finding
from redact_ai.pipeline.detect.base import (
    cap_confidence,
    confidence_from_tokens,
    line_text_and_offsets,
    tokens_covering,
    union_bboxes,
)
from redact_ai.policy.schema import Policy

_PAN_RE = re.compile(r"(?<!\d)(?:\d[ \-]?){13,19}(?!\d)")


def luhn_ok(s: str) -> bool:
    d = [int(c) for c in s if c.isdigit()]
    if not 13 <= len(d) <= 19:
        return False
    checksum = 0
    for i, n in enumerate(reversed(d)):
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        checksum += n
    return checksum % 10 == 0


class PanDetector:
    """FI-001 — card numbers, Luhn-validated."""

    rule_id: ClassVar[str] = "FI-001"
    category: ClassVar[Category] = "FINANCIAL"

    def detect(self, doc: Document, policy: Policy) -> list[Finding]:
        out: list[Finding] = []
        for page in doc.pages:
            for block in page.blocks:
                for line in block.lines:
                    text, spans = line_text_and_offsets(line)
                    for match in _PAN_RE.finditer(text):
                        raw = match.group(0)
                        if not luhn_ok(raw):
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
                                matched_text=raw,
                                page_index=page.index,
                            )
                        )
        return out


_IBAN_RE = re.compile(r"\b[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]){11,30}\b")


def iban_ok(raw: str) -> bool:
    s = re.sub(r"\s+", "", raw).upper()
    if not 15 <= len(s) <= 34:
        return False
    rearranged = s[4:] + s[:4]
    digits = "".join(str(ord(c) - 55) if c.isalpha() else c for c in rearranged)
    if not digits.isdigit():
        return False
    return int(digits) % 97 == 1


class IbanDetector:
    """FI-002 — IBAN with mod-97 validation."""

    rule_id: ClassVar[str] = "FI-002"
    category: ClassVar[Category] = "FINANCIAL"

    def detect(self, doc: Document, policy: Policy) -> list[Finding]:
        out: list[Finding] = []
        for page in doc.pages:
            for block in page.blocks:
                for line in block.lines:
                    text, spans = line_text_and_offsets(line)
                    for match in _IBAN_RE.finditer(text):
                        raw = match.group(0)
                        if not iban_ok(raw):
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
                                matched_text=raw,
                                page_index=page.index,
                            )
                        )
        return out


_ACCOUNT_LABELS = re.compile(r"\b(Account|A/C|Acct(?:\s*No\.?)?)\b", re.IGNORECASE)
_ACCOUNT_VALUE = re.compile(r"[\d][\d\s\-]{5,19}")


def _digit_count(s: str) -> int:
    return sum(1 for c in s if c.isdigit())


class BankAccountDetector:
    """FI-003 — generic bank account numbers (label-anchored)."""

    rule_id: ClassVar[str] = "FI-003"
    category: ClassVar[Category] = "FINANCIAL"

    def detect(self, doc: Document, policy: Policy) -> list[Finding]:
        out: list[Finding] = []
        for page in doc.pages:
            for block in page.blocks:
                trigger_lines = [
                    line
                    for line in block.lines
                    if _ACCOUNT_LABELS.search(" ".join(t.text for t in line.tokens))
                ]
                if not trigger_lines:
                    continue
                for trigger in trigger_lines:
                    for cand in block.lines:
                        same = cand is trigger
                        below = (
                            cand.bbox.y >= trigger.bbox.y2 and cand.bbox.y - trigger.bbox.y2 <= 96
                        )
                        if not (same or below):
                            continue
                        text, spans = line_text_and_offsets(cand)
                        label_match = _ACCOUNT_LABELS.search(text) if same else None
                        search_start = label_match.end() if label_match else 0
                        for match in _ACCOUNT_VALUE.finditer(text, search_start):
                            value = match.group(0)
                            if _digit_count(value) < 6:
                                continue
                            digits_only = re.sub(r"\D", "", value)
                            if luhn_ok(digits_only):
                                continue  # belongs to FI-001
                            if iban_ok(value):
                                continue  # belongs to FI-002
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
                                    matched_text=value,
                                    page_index=page.index,
                                )
                            )
                            break
        return out


_MASK_CHARS = "*X•·●"
_MASKED_NUMBER_RE = re.compile(
    r"(?:[\*X•·●](?:\s|[\-]){0,2}){2,}(?:\d(?:\s|[\-])?){2,}"
    r"|(?:\d(?:\s|[\-])?){2,}(?:[\*X•·●](?:\s|[\-]){0,2}){2,}(?:\d(?:\s|[\-])?){2,}"
)


class MaskedAccountDetector:
    """FI-005 — masked account / card numbers like ``******1234`` or ``XXXX5678``.

    A run of mask glyphs (``*``, ``X``, ``•``, ``·``, ``●``)
    adjacent to a short run of digits is an unambiguous reference to a
    sensitive identifier. No label trigger is required because the mask
    glyphs themselves are the signal.
    """

    rule_id: ClassVar[str] = "FI-005"
    category: ClassVar[Category] = "FINANCIAL"

    def detect(self, doc: Document, policy: Policy) -> list[Finding]:
        out: list[Finding] = []
        for page in doc.pages:
            for block in page.blocks:
                for line in block.lines:
                    text, spans = line_text_and_offsets(line)
                    for match in _MASKED_NUMBER_RE.finditer(text):
                        raw = match.group(0)
                        if _digit_count(raw) < 2:
                            continue
                        if not _has_mask_char(raw):
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
                                matched_text=raw,
                                page_index=page.index,
                            )
                        )
        return out


def _has_mask_char(s: str) -> bool:
    return any(c in _MASK_CHARS for c in s)


_EXPIRY_RE = re.compile(r"\b(0[1-9]|1[0-2])[\/\-](\d{2}|\d{4})\b")
_CVV_RE = re.compile(r"\b\d{3,4}\b")
_CVV_KEYWORD_RE = re.compile(r"\b(CVV|CVC|Sec(?:urity)?\s*Code)\b", re.IGNORECASE)


class CvvExpiryDetector:
    """FI-004 — CVV / expiry adjacent to a PAN."""

    rule_id: ClassVar[str] = "FI-004"
    category: ClassVar[Category] = "FINANCIAL"

    def detect(self, doc: Document, policy: Policy) -> list[Finding]:
        pans = PanDetector().detect(doc, policy)
        if not pans:
            return []
        out: list[Finding] = []
        for page in doc.pages:
            for block in page.blocks:
                pans_in_block = [
                    p
                    for p in pans
                    if (p.page_index == page.index and block.bbox.iou(p.bbox) > 0)
                    or _bbox_inside(p.bbox, block.bbox)
                ]
                if not pans_in_block:
                    continue
                for line in block.lines:
                    text, spans = line_text_and_offsets(line)
                    line_close = any(_bbox_close(line.bbox, p.bbox, 200) for p in pans_in_block)
                    if not line_close:
                        continue
                    for match in _EXPIRY_RE.finditer(text):
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
                    if _CVV_KEYWORD_RE.search(text):
                        for match in _CVV_RE.finditer(text):
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


def _bbox_inside(inner: BBox, outer: BBox) -> bool:
    return bool(
        inner.x >= outer.x and inner.y >= outer.y and inner.x2 <= outer.x2 and inner.y2 <= outer.y2
    )


def _bbox_close(a: BBox, b: BBox, px: int) -> bool:
    dx = max(a.x - b.x2, b.x - a.x2, 0)
    dy = max(a.y - b.y2, b.y - a.y2, 0)
    return dx + dy <= px
