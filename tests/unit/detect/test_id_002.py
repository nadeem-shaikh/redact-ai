"""ID-002 date-of-birth tests."""

from __future__ import annotations

from redact_ai.pipeline.detect.identity import DateOfBirthDetector
from redact_ai.policy.loader import load_default_policy
from tests.unit.detect._helpers import make_doc, make_doc_block


def test_dob_match_medium_without_label() -> None:
    doc = make_doc(["12/04/1992"])
    out = DateOfBirthDetector().detect(doc, load_default_policy())
    assert len(out) == 1
    assert out[0].confidence == "medium"


def test_dob_with_label_high() -> None:
    doc = make_doc_block(["DOB", "12/04/1992"])
    out = DateOfBirthDetector().detect(doc, load_default_policy())
    assert any(f.confidence == "high" for f in out)


def test_invalid_date_rejected() -> None:
    doc = make_doc(["31/02/1992"])
    out = DateOfBirthDetector().detect(doc, load_default_policy())
    assert out == []
