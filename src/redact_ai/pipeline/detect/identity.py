"""IDENTITY detectors: ID-001 through ID-006 (DETECTORS_v0.1)."""

from __future__ import annotations

import re
from functools import lru_cache
from importlib.resources import files
from typing import Any, ClassVar

from redact_ai.errors import policy_error
from redact_ai.models.document import Block, Document, Line, Token
from redact_ai.models.findings import Category, Confidence, Finding
from redact_ai.pipeline.detect.base import (
    cap_confidence,
    confidence_from_tokens,
    line_text_and_offsets,
    tokens_covering,
    union_bboxes,
)
from redact_ai.policy.schema import Policy


@lru_cache(maxsize=4)
def _wordset(filename: str) -> frozenset[str]:
    text = files("redact_ai.resources").joinpath(filename).read_text(encoding="utf-8")
    return frozenset(
        line.strip().lower()
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )


_TITLE_RE = re.compile(r"^[A-Z][a-zA-Z'\-]+$")
_MIDDLE_RE = re.compile(r"^[A-Z](?:\.|)$")


class FullNameDetector:
    """ID-001 — dictionary-driven full personal names."""

    rule_id: ClassVar[str] = "ID-001"
    category: ClassVar[Category] = "IDENTITY"

    def detect(self, doc: Document, policy: Policy) -> list[Finding]:
        given = _wordset("names_given_en_us.txt")
        family = _wordset("names_family_en_us.txt")
        stop = _wordset("stopwords_caps_en.txt")
        out: list[Finding] = []
        for page in doc.pages:
            for block in page.blocks:
                for line in block.lines:
                    tokens = line.tokens
                    n = len(tokens)
                    i = 0
                    while i < n:
                        consumed = self._try_match(tokens, i, given, family, stop, page.index, out)
                        i += consumed if consumed else 1
        return out

    def _try_match(
        self,
        tokens: tuple[Token, ...],
        i: int,
        given: frozenset[str],
        family: frozenset[str],
        stop: frozenset[str],
        page_index: int,
        out: list[Finding],
    ) -> int:
        first = tokens[i]
        if not _TITLE_RE.match(first.text):
            return 0
        if first.text.lower() in stop:
            return 0
        # Try First M. Last (three tokens with middle initial).
        if i + 2 < len(tokens):
            middle = tokens[i + 1]
            last = tokens[i + 2]
            if (
                _MIDDLE_RE.match(middle.text)
                and _TITLE_RE.match(last.text)
                and last.text.lower() not in stop
            ):
                fhit = first.text.lower() in given
                lhit = last.text.lower() in family
                if fhit or lhit:
                    self._emit([first, middle, last], fhit and lhit, page_index, out)
                    return 3
        # Try First Last (two tokens).
        if i + 1 < len(tokens):
            last = tokens[i + 1]
            if _TITLE_RE.match(last.text) and last.text.lower() not in stop:
                fhit = first.text.lower() in given
                lhit = last.text.lower() in family
                if fhit and lhit:
                    self._emit([first, last], True, page_index, out)
                    return 2
                if fhit or lhit:
                    self._emit([first, last], False, page_index, out)
                    return 2
        return 0

    def _emit(
        self,
        tokens: list[Token],
        both_hit: bool,
        page_index: int,
        out: list[Finding],
    ) -> None:
        ocr_conf = confidence_from_tokens(tokens)
        detector_conf: Confidence = "high" if both_hit and ocr_conf == "high" else "medium"
        out.append(
            Finding(
                rule_id=self.rule_id,
                category=self.category,
                bbox=union_bboxes(t.bbox for t in tokens),
                confidence=cap_confidence(detector_conf, ocr_conf),
                matched_text=" ".join(t.text for t in tokens),
                page_index=page_index,
            )
        )


_DOB_REGEXES = [
    re.compile(r"\b(?:0?[1-9]|[12]\d|3[01])[\/\-.\s](?:0?[1-9]|1[0-2])[\/\-.\s](?:19|20)\d{2}\b"),
    re.compile(r"\b(?:19|20)\d{2}[\/\-.\s](?:0?[1-9]|1[0-2])[\/\-.\s](?:0?[1-9]|[12]\d|3[01])\b"),
]
_DOB_CONTEXT = re.compile(r"\b(?:DOB|Date of Birth|D\.O\.B\.|Born)\b", re.IGNORECASE)


class DateOfBirthDetector:
    """ID-002 — DOB with optional ``DOB`` proximity boost."""

    rule_id: ClassVar[str] = "ID-002"
    category: ClassVar[Category] = "IDENTITY"

    def detect(self, doc: Document, policy: Policy) -> list[Finding]:
        out: list[Finding] = []
        for page in doc.pages:
            for block in page.blocks:
                for line in block.lines:
                    text, spans = line_text_and_offsets(line)
                    for regex in _DOB_REGEXES:
                        for match in regex.finditer(text):
                            if not _valid_date(match.group(0)):
                                continue
                            covered = tokens_covering(spans, *match.span())
                            if not covered:
                                continue
                            ocr_conf = confidence_from_tokens(covered)
                            detector_conf: Confidence = "medium"
                            if _has_dob_context(block, line):
                                detector_conf = "high"
                            out.append(
                                Finding(
                                    rule_id=self.rule_id,
                                    category=self.category,
                                    bbox=union_bboxes(t.bbox for t in covered),
                                    confidence=cap_confidence(detector_conf, ocr_conf),
                                    matched_text=match.group(0),
                                    page_index=page.index,
                                )
                            )
        return out


def _valid_date(raw: str) -> bool:
    import datetime as dt

    parts = re.split(r"[\/\-.\s]", raw)
    if len(parts) != 3:
        return False
    try:
        a, b, c = (int(p) for p in parts)
    except ValueError:
        return False
    candidates: list[tuple[int, int, int]] = []
    if 1900 <= a <= 2100:
        candidates.append((a, b, c))
    if 1900 <= c <= 2100:
        candidates.append((c, b, a))
        candidates.append((c, a, b))
    for year, month, day in candidates:
        try:
            dt.date(year, month, day)
            return True
        except ValueError:
            continue
    return False


def _has_dob_context(block: Block, target_line: Line) -> bool:
    for line in block.lines:
        if line is target_line:
            text = " ".join(t.text for t in line.tokens)
            if _DOB_CONTEXT.search(text):
                return True
            continue
        if line.bbox.y2 <= target_line.bbox.y and target_line.bbox.y - line.bbox.y2 <= 32:
            text = " ".join(t.text for t in line.tokens)
            if _DOB_CONTEXT.search(text):
                return True
    return False


_ID_LABELS = re.compile(
    r"\b(SSN|Social Security|National ID|NIN|Aadhaar|PAN|Tax ID|TIN|EIN)\b",
    re.IGNORECASE,
)
_ID_VALUE_RE = re.compile(r"[\d][\d\s\-]{5,19}")


def _digit_count(s: str) -> int:
    return sum(1 for c in s if c.isdigit())


class _LabelTriggeredDetector:
    """Shared helper for label-anchored ID rules (ID-003, ID-004, ID-005, FI-003, HE-001)."""

    label_re: re.Pattern[str]
    value_re: re.Pattern[str]
    horizontal_px: int = 64
    min_digits: int = 0
    detector_confidence: Confidence = "high"

    def _scan(self, doc: Document) -> list[Finding]:
        out: list[Finding] = []
        for page in doc.pages:
            for block in page.blocks:
                trigger_lines = [
                    line
                    for line in block.lines
                    if self.label_re.search(" ".join(t.text for t in line.tokens))
                ]
                if not trigger_lines:
                    continue
                for trigger in trigger_lines:
                    self._scan_block(block, trigger, page.index, out)
        return out

    def _scan_block(
        self,
        block: Block,
        trigger: Line,
        page_index: int,
        out: list[Finding],
    ) -> None:
        for cand in block.lines:
            same_line = cand is trigger
            below = (
                cand.bbox.y >= trigger.bbox.y2
                and cand.bbox.y - trigger.bbox.y2 <= self.horizontal_px
            )
            if not (same_line or below):
                continue
            text, spans = line_text_and_offsets(cand)
            label_match = self.label_re.search(text) if same_line else None
            search_start = label_match.end() if label_match else 0
            for match in self.value_re.finditer(text, search_start):
                value = match.group(0)
                if _digit_count(value) < self.min_digits:
                    continue
                if same_line:
                    covered_tokens = tokens_covering(spans, *match.span())
                    if covered_tokens:
                        leftmost = min(t.bbox.x for t in covered_tokens)
                        if leftmost - trigger.bbox.x2 > self.horizontal_px and label_match is None:
                            continue
                else:
                    covered_tokens = tokens_covering(spans, *match.span())
                if not covered_tokens:
                    continue
                ocr_conf = confidence_from_tokens(covered_tokens)
                out.append(
                    Finding(
                        rule_id=self.rule_id,  # type: ignore[attr-defined]
                        category=self.category,  # type: ignore[attr-defined]
                        bbox=union_bboxes(t.bbox for t in covered_tokens),
                        confidence=cap_confidence(self.detector_confidence, ocr_conf),
                        matched_text=value,
                        page_index=page_index,
                    )
                )
                return  # first match per (trigger, candidate-line) per spec


class GovernmentIdDetector(_LabelTriggeredDetector):
    """ID-003 — generic government IDs anchored to a trigger label."""

    rule_id: ClassVar[str] = "ID-003"
    category: ClassVar[Category] = "IDENTITY"
    label_re = _ID_LABELS
    value_re = _ID_VALUE_RE
    horizontal_px = 64
    min_digits = 6
    detector_confidence: Confidence = "high"

    def detect(self, doc: Document, policy: Policy) -> list[Finding]:
        return self._scan(doc)


_PASSPORT_LABELS = re.compile(r"\bPassport(?:\s*(?:No|Number))?\b", re.IGNORECASE)
_PASSPORT_VALUE = re.compile(r"\b(?:[A-Z][0-9]{8}|[A-Z]{2}[0-9]{7})\b")


class PassportDetector(_LabelTriggeredDetector):
    """ID-004 — label-triggered passport numbers."""

    rule_id: ClassVar[str] = "ID-004"
    category: ClassVar[Category] = "IDENTITY"
    label_re = _PASSPORT_LABELS
    value_re = _PASSPORT_VALUE
    horizontal_px = 64
    min_digits = 0
    detector_confidence: Confidence = "high"

    def detect(self, doc: Document, policy: Policy) -> list[Finding]:
        return self._scan(doc)


_DL_LABELS = re.compile(r"\b(DL|DLN|Driver|License|Licence)\b", re.IGNORECASE)
_DL_VALUE = re.compile(r"\b[A-Z0-9]{6,14}\b")


class DriverLicenceDetector:
    """ID-005 — label-triggered driver's licence numbers."""

    rule_id: ClassVar[str] = "ID-005"
    category: ClassVar[Category] = "IDENTITY"

    def detect(self, doc: Document, policy: Policy) -> list[Finding]:
        out: list[Finding] = []
        for page in doc.pages:
            for block in page.blocks:
                trigger_lines = [
                    line
                    for line in block.lines
                    if _DL_LABELS.search(" ".join(t.text for t in line.tokens))
                ]
                if not trigger_lines:
                    continue
                for trigger in trigger_lines:
                    for cand in block.lines:
                        same_line = cand is trigger
                        below = (
                            cand.bbox.y >= trigger.bbox.y2 and cand.bbox.y - trigger.bbox.y2 <= 64
                        )
                        if not (same_line or below):
                            continue
                        text, spans = line_text_and_offsets(cand)
                        label_match = _DL_LABELS.search(text) if same_line else None
                        search_start = label_match.end() if label_match else 0
                        for match in _DL_VALUE.finditer(text, search_start):
                            value = match.group(0)
                            if not (
                                any(c.isalpha() for c in value) and any(c.isdigit() for c in value)
                            ):
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
                                    confidence=cap_confidence("medium", ocr_conf),
                                    matched_text=value,
                                    page_index=page.index,
                                )
                            )
                            break
        return out


_DEFAULT_NER_MODEL = "en_core_web_md"
_NER_MODEL_INSTALL_HINT = (
    "Run `python -m spacy download en_core_web_md` once after install. "
    "See ADR-011 in docs/DECISIONS.md."
)


@lru_cache(maxsize=2)
def _load_spacy_ner(model_name: str) -> Any:
    try:
        import spacy
    except ImportError as exc:  # pragma: no cover - spacy is a required dep
        raise RuntimeError(
            "spaCy is required for ID-006 PersonNameNerDetector but is not installed."
        ) from exc
    try:
        nlp = spacy.load(
            model_name,
            disable=["parser", "lemmatizer", "tagger", "attribute_ruler"],
        )
    except OSError as exc:
        raise RuntimeError(
            f"spaCy model '{model_name}' is not available. {_NER_MODEL_INSTALL_HINT}"
        ) from exc
    return nlp


class PersonNameNerDetector:
    """ID-006 — statistical NER for personal names (PERSON entities).

    Complements ID-001 by catching names absent from the bundled
    given/family dictionaries (non-Western names, novel spellings).
    Runs entirely on-device via spaCy (ADR-002, ADR-011).
    """

    rule_id: ClassVar[str] = "ID-006"
    category: ClassVar[Category] = "IDENTITY"

    def detect(self, doc: Document, policy: Policy) -> list[Finding]:
        model_name = _DEFAULT_NER_MODEL
        for det in policy.detectors:
            if det.id == self.rule_id:
                model_override = det.overrides.get("model")
                if model_override is not None:
                    if not isinstance(model_override, str) or not model_override:
                        raise policy_error(policy.id, "ID-006.model must be a non-empty string")
                    model_name = model_override
                break
        try:
            nlp = _load_spacy_ner(model_name)
        except RuntimeError as exc:
            raise policy_error(policy.id, str(exc)) from exc
        out: list[Finding] = []
        for page in doc.pages:
            for block in page.blocks:
                for line in block.lines:
                    text, spans = line_text_and_offsets(line)
                    if not text.strip():
                        continue
                    parsed = nlp(text)
                    for ent in parsed.ents:
                        if ent.label_ != "PERSON":
                            continue
                        covered = tokens_covering(spans, ent.start_char, ent.end_char)
                        if not covered:
                            continue
                        ocr_conf = confidence_from_tokens(covered)
                        detector_conf: Confidence = "high" if len(covered) >= 2 else "medium"
                        out.append(
                            Finding(
                                rule_id=self.rule_id,
                                category=self.category,
                                bbox=union_bboxes(t.bbox for t in covered),
                                confidence=cap_confidence(detector_conf, ocr_conf),
                                matched_text=ent.text,
                                page_index=page.index,
                            )
                        )
        return out
