"""ID-001 full-name detector tests."""

from __future__ import annotations

from redact_ai.pipeline.detect.identity import FullNameDetector
from redact_ai.policy.loader import load_default_policy
from tests.unit.detect._helpers import make_doc


def test_two_dictionary_hits_high_confidence() -> None:
    doc = make_doc(["Aanya Sharma"])
    out = FullNameDetector().detect(doc, load_default_policy())
    assert len(out) == 1
    assert out[0].rule_id == "ID-001"
    assert out[0].confidence == "high"


def test_three_token_middle_initial() -> None:
    doc = make_doc(["John A. Smith"])
    out = FullNameDetector().detect(doc, load_default_policy())
    assert len(out) == 1


def test_negative_filter_skips_stopword_caps() -> None:
    doc = make_doc(["New York"])
    out = FullNameDetector().detect(doc, load_default_policy())
    assert out == []


def test_trailing_comma_does_not_break_match() -> None:
    """Real OCR keeps punctuation glued to the word (``Bennett,`` is
    one token). The detector must still recognise the name body."""
    doc = make_doc(["Laura Bennett, MD"])
    out = FullNameDetector().detect(doc, load_default_policy())
    assert len(out) == 1
    assert "Laura" in out[0].matched_text and "Bennett" in out[0].matched_text


def test_honorific_prefix_is_skipped() -> None:
    """``Dr. Laura Bennett, MD`` should still resolve to the name even
    though Tesseract emits ``Dr.`` as the leading token."""
    doc = make_doc(["Dr. Laura Bennett, MD"])
    out = FullNameDetector().detect(doc, load_default_policy())
    assert len(out) == 1
    assert "Laura" in out[0].matched_text and "Bennett" in out[0].matched_text


def test_honorific_in_middle_of_line_also_skipped() -> None:
    """Layout: ``Reported by: Dr. Laura Bennett, MD``."""
    doc = make_doc(["Reported by: Dr. Laura Bennett, MD"])
    out = FullNameDetector().detect(doc, load_default_policy())
    assert any("Laura" in f.matched_text and "Bennett" in f.matched_text for f in out), [
        f.matched_text for f in out
    ]


def test_bare_honorific_does_not_emit() -> None:
    """A standalone ``Dr.`` with no following name is not a finding."""
    doc = make_doc(["Dr."])
    out = FullNameDetector().detect(doc, load_default_policy())
    assert out == []
