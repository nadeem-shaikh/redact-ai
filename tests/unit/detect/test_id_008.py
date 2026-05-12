"""ID-008 PaymentRecipientNameDetector tests."""

from __future__ import annotations

from redact_ai.pipeline.detect.identity import PaymentRecipientNameDetector
from redact_ai.policy.loader import load_default_policy
from tests.unit.detect._helpers import make_doc_block


def test_paid_to_all_caps_non_western_name() -> None:
    doc = make_doc_block(["Paid to", "ANJALI VENKATESHA NAIDU"])
    out = PaymentRecipientNameDetector().detect(doc, load_default_policy())
    assert len(out) == 1
    assert out[0].rule_id == "ID-008"
    assert "ANJALI" in out[0].matched_text
    assert "NAIDU" in out[0].matched_text
    assert out[0].confidence == "high"


def test_payee_title_case_name() -> None:
    doc = make_doc_block(["Payee: John Smith"])
    out = PaymentRecipientNameDetector().detect(doc, load_default_policy())
    assert len(out) == 1
    assert out[0].matched_text == "John Smith"


def test_beneficiary_on_separate_line() -> None:
    doc = make_doc_block(["Beneficiary", "Maria Garcia"])
    out = PaymentRecipientNameDetector().detect(doc, load_default_policy())
    assert len(out) == 1
    assert out[0].matched_text == "Maria Garcia"


def test_no_label_no_finding() -> None:
    doc = make_doc_block(["ANJALI VENKATESHA NAIDU"])
    out = PaymentRecipientNameDetector().detect(doc, load_default_policy())
    assert out == []


def test_single_capitalized_token_below_label_skipped() -> None:
    doc = make_doc_block(["Paid to", "Total"])
    out = PaymentRecipientNameDetector().detect(doc, load_default_policy())
    assert out == []


def test_label_with_lowercase_word_after_label_does_not_match() -> None:
    doc = make_doc_block(["Paid to vendor today"])
    out = PaymentRecipientNameDetector().detect(doc, load_default_policy())
    assert out == []
