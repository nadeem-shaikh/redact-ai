"""ID-003 / ID-004 / ID-005 detector tests."""

from __future__ import annotations

from redact_ai.pipeline.detect.identity import (
    DriverLicenceDetector,
    GovernmentIdDetector,
    PassportDetector,
)
from redact_ai.policy.loader import load_default_policy
from tests.unit.detect._helpers import make_doc, make_doc_block


def test_government_id_label_anchored() -> None:
    doc = make_doc(["SSN: 123-45-6789"])
    out = GovernmentIdDetector().detect(doc, load_default_policy())
    assert len(out) == 1
    assert out[0].confidence == "high"


def test_government_id_no_label_no_match() -> None:
    doc = make_doc(["123-45-6789"])
    out = GovernmentIdDetector().detect(doc, load_default_policy())
    assert out == []


def test_passport_below_label() -> None:
    doc = make_doc_block(["Passport No.", "A12345678"])
    out = PassportDetector().detect(doc, load_default_policy())
    assert any(f.confidence == "high" for f in out)


def test_passport_wrong_shape() -> None:
    doc = make_doc(["Passport: 12345"])
    out = PassportDetector().detect(doc, load_default_policy())
    assert out == []


def test_driver_licence() -> None:
    doc = make_doc(["DL: D1234567"])
    out = DriverLicenceDetector().detect(doc, load_default_policy())
    assert len(out) == 1
    assert out[0].confidence == "medium"


def test_driver_licence_no_letter_or_digit_rejected() -> None:
    doc = make_doc(["DL: ABCDEFGH"])
    out = DriverLicenceDetector().detect(doc, load_default_policy())
    assert out == []
