"""CREDENTIALS detectors: CR-001, CR-002, CR-003 (DETECTORS_v0.1)."""

from __future__ import annotations

import re
from collections import Counter
from math import log2
from typing import ClassVar

from redact_ai.models.document import Document
from redact_ai.models.findings import Category, Confidence, Finding
from redact_ai.pipeline.detect.base import (
    cap_confidence,
    confidence_from_tokens,
    line_text_and_offsets,
    tokens_covering,
    union_bboxes,
)
from redact_ai.policy.schema import Policy


def shannon_bits_per_char(s: str) -> float:
    if not s:
        return 0.0
    counts = Counter(s)
    n = len(s)
    return -sum((c / n) * log2(c / n) for c in counts.values())


_TOKEN_CANDIDATE_RE = re.compile(r"\b[A-Za-z0-9_\-]{20,}\b")
_HEX_RE = re.compile(r"^[0-9a-fA-F]+$")
_VERSION_LIKE_RE = re.compile(r"^[0-9]+(?:\.[0-9]+)+$")
_CONTEXT_RE = re.compile(
    r"\b(token|secret|key|bearer|authorization)\b", re.IGNORECASE
)


class HighEntropyTokenDetector:
    """CR-001 — generic high-entropy tokens."""

    rule_id: ClassVar[str] = "CR-001"
    category: ClassVar[Category] = "CREDENTIALS"

    def detect(self, doc: Document, policy: Policy) -> list[Finding]:
        out: list[Finding] = []
        for page in doc.pages:
            for block in page.blocks:
                for line in block.lines:
                    text, spans = line_text_and_offsets(line)
                    context_hit = _CONTEXT_RE.search(text) is not None
                    for match in _TOKEN_CANDIDATE_RE.finditer(text):
                        value = match.group(0)
                        if _HEX_RE.match(value) and len(value) < 32:
                            continue
                        if _VERSION_LIKE_RE.match(value):
                            continue
                        entropy = shannon_bits_per_char(value)
                        if entropy < 3.5:
                            continue
                        covered = tokens_covering(spans, *match.span())
                        if not covered:
                            continue
                        ocr_conf = confidence_from_tokens(covered)
                        detector_conf: Confidence = (
                            "high" if entropy >= 4.0 or context_hit else "medium"
                        )
                        out.append(
                            Finding(
                                rule_id=self.rule_id,
                                category=self.category,
                                bbox=union_bboxes(t.bbox for t in covered),
                                confidence=cap_confidence(detector_conf, ocr_conf),
                                matched_text=value,
                                page_index=page.index,
                            )
                        )
        return out


_SSH_BEGIN_RE = re.compile(r"-----BEGIN (?:OPENSSH|RSA|DSA|EC|PGP) PRIVATE KEY-----")
_SSH_END_RE = re.compile(r"-----END (?:OPENSSH|RSA|DSA|EC|PGP) PRIVATE KEY-----")


class SshPrivateKeyDetector:
    """CR-002 — SSH private key block markers."""

    rule_id: ClassVar[str] = "CR-002"
    category: ClassVar[Category] = "CREDENTIALS"

    def detect(self, doc: Document, policy: Policy) -> list[Finding]:
        out: list[Finding] = []
        for page in doc.pages:
            flat_lines = [
                line for block in page.blocks for line in block.lines
            ]
            i = 0
            while i < len(flat_lines):
                line = flat_lines[i]
                text = " ".join(t.text for t in line.tokens)
                if not _SSH_BEGIN_RE.search(text):
                    i += 1
                    continue
                end_index = len(flat_lines) - 1
                for j in range(i, len(flat_lines)):
                    txt = " ".join(t.text for t in flat_lines[j].tokens)
                    if _SSH_END_RE.search(txt):
                        end_index = j
                        break
                target_lines = flat_lines[i : end_index + 1]
                tokens = [t for tl in target_lines for t in tl.tokens]
                if tokens:
                    ocr_conf = confidence_from_tokens(tokens)
                    out.append(
                        Finding(
                            rule_id=self.rule_id,
                            category=self.category,
                            bbox=union_bboxes(t.bbox for t in tokens),
                            confidence=cap_confidence("high", ocr_conf),
                            matched_text="<ssh-private-key-block>",
                            page_index=page.index,
                        )
                    )
                i = end_index + 1
        return out


_CLOUD_KEY_RE = re.compile(
    r"\bAKIA[0-9A-Z]{16}\b"
    r"|\bASIA[0-9A-Z]{16}\b"
    r"|\bAIza[0-9A-Za-z\-_]{35}\b"
    r"|\bsk-[A-Za-z0-9]{20,}\b"
    r"|\bsk_live_[A-Za-z0-9]{16,}\b"
    r"|\bghp_[A-Za-z0-9]{36}\b"
)


class CloudKeyDetector:
    """CR-003 — common cloud key prefixes."""

    rule_id: ClassVar[str] = "CR-003"
    category: ClassVar[Category] = "CREDENTIALS"

    def detect(self, doc: Document, policy: Policy) -> list[Finding]:
        out: list[Finding] = []
        for page in doc.pages:
            for block in page.blocks:
                for line in block.lines:
                    text, spans = line_text_and_offsets(line)
                    for match in _CLOUD_KEY_RE.finditer(text):
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
