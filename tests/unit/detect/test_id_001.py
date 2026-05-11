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
