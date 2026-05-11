"""CUSTOM detector: CU-001 (user-defined regex via policy overrides)."""

from __future__ import annotations

import re
from typing import ClassVar

from redact_ai.errors import policy_error
from redact_ai.models.document import Document
from redact_ai.models.findings import Category, Confidence, Finding
from redact_ai.pipeline.detect.base import (
    cap_confidence,
    confidence_from_tokens,
    line_text_and_offsets,
    policy_override,
    tokens_covering,
    union_bboxes,
)
from redact_ai.policy.schema import Policy


_ALLOWED_CONFIDENCES: frozenset[str] = frozenset({"low", "medium", "high"})
_ALLOWED_CATEGORIES: frozenset[str] = frozenset(
    {"IDENTITY", "CONTACT", "FINANCIAL", "HEALTH", "CREDENTIALS", "LOCATION", "CUSTOM"}
)


class CustomRegexDetector:
    """CU-001 — user-defined regex / dictionary detector."""

    rule_id: ClassVar[str] = "CU-001"
    category: ClassVar[Category] = "CUSTOM"

    def detect(self, doc: Document, policy: Policy) -> list[Finding]:
        ref = policy_override(policy, self.rule_id)
        if ref is None:
            return []
        overrides = ref.overrides
        kind = overrides.get("kind", "regex")
        if kind not in {"regex", "dictionary"}:
            raise policy_error(policy.id, f"CU-001.kind must be 'regex' or 'dictionary' (got {kind!r})")
        category = overrides.get("category", "CUSTOM")
        if category not in _ALLOWED_CATEGORIES:
            raise policy_error(policy.id, f"CU-001.category must be one of {_ALLOWED_CATEGORIES}")
        confidence: Confidence = overrides.get("confidence", "medium")
        if confidence not in _ALLOWED_CONFIDENCES:
            raise policy_error(policy.id, f"CU-001.confidence must be one of {_ALLOWED_CONFIDENCES}")
        if kind == "regex":
            pattern = overrides.get("pattern")
            if not isinstance(pattern, str) or not pattern:
                raise policy_error(policy.id, "CU-001.pattern is required for kind=regex")
            try:
                regex = re.compile(pattern)
            except re.error as exc:
                raise policy_error(policy.id, f"CU-001.pattern is invalid regex: {exc}") from exc
        else:
            words = overrides.get("words")
            if not isinstance(words, list) or not all(isinstance(w, str) for w in words):
                raise policy_error(policy.id, "CU-001.words must be a list of strings")
            regex = re.compile(r"\b(?:" + "|".join(re.escape(w) for w in words) + r")\b")
        out: list[Finding] = []
        for page in doc.pages:
            for block in page.blocks:
                for line in block.lines:
                    text, spans = line_text_and_offsets(line)
                    for match in regex.finditer(text):
                        covered = tokens_covering(spans, *match.span())
                        if not covered:
                            continue
                        ocr_conf = confidence_from_tokens(covered)
                        out.append(
                            Finding(
                                rule_id=self.rule_id,
                                category=category,  # type: ignore[arg-type]
                                bbox=union_bboxes(t.bbox for t in covered),
                                confidence=cap_confidence(confidence, ocr_conf),
                                matched_text=match.group(0),
                                page_index=page.index,
                            )
                        )
        return out
