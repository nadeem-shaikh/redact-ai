"""CONTACT detector tests."""

from __future__ import annotations

from redact_ai.pipeline.detect.contact import (
    EmailDetector,
    PhoneDetector,
    PostalAddressDetector,
)
from redact_ai.policy.loader import load_default_policy
from tests.unit.detect._helpers import make_doc, make_doc_block


def test_email_high_confidence() -> None:
    doc = make_doc(["Reach me: name.surname+tag@example.com"])
    out = EmailDetector().detect(doc, load_default_policy())
    assert len(out) == 1
    assert out[0].confidence == "high"


def test_email_negative() -> None:
    doc = make_doc(["@example.com"])
    out = EmailDetector().detect(doc, load_default_policy())
    assert out == []


def test_phone_high_with_country_code() -> None:
    doc = make_doc(["+1 555 123 4567"])
    out = PhoneDetector().detect(doc, load_default_policy())
    assert len(out) == 1
    assert out[0].confidence == "high"


def test_phone_medium_without_country_code() -> None:
    doc = make_doc(["555-123-4567"])
    out = PhoneDetector().detect(doc, load_default_policy())
    assert len(out) == 1
    assert out[0].confidence == "medium"


def test_phone_skips_version_strings() -> None:
    doc = make_doc(["version 1.2.3.4 555 123 4567"])
    out = PhoneDetector().detect(doc, load_default_policy())
    assert out == []


def test_postal_address_two_line_high() -> None:
    doc = make_doc_block(["221 Baker Street", "Springfield, IL 62704"])
    out = PostalAddressDetector().detect(doc, load_default_policy())
    assert any(f.confidence == "high" for f in out)


def test_postal_address_label_only_medium() -> None:
    doc = make_doc_block(["Address", "221 Baker Street"])
    out = PostalAddressDetector().detect(doc, load_default_policy())
    assert any(f.confidence == "medium" for f in out)


def test_postal_address_no_match() -> None:
    doc = make_doc(["random line of text"])
    out = PostalAddressDetector().detect(doc, load_default_policy())
    assert out == []
