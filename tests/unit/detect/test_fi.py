"""FINANCIAL detector tests (FI-001..FI-004)."""

from __future__ import annotations

from redact_ai.pipeline.detect.financial import (
    BankAccountDetector,
    CvvExpiryDetector,
    IbanDetector,
    MaskedAccountDetector,
    PanDetector,
    iban_ok,
    luhn_ok,
)
from redact_ai.policy.loader import load_default_policy
from tests.unit.detect._helpers import make_doc, make_doc_block


def test_pan_luhn_passes() -> None:
    doc = make_doc(["4111 1111 1111 1111"])
    out = PanDetector().detect(doc, load_default_policy())
    assert len(out) == 1
    assert out[0].confidence == "high"


def test_pan_luhn_fails_filtered() -> None:
    doc = make_doc(["1234567890123456"])
    out = PanDetector().detect(doc, load_default_policy())
    assert out == []


def test_luhn_helper() -> None:
    assert luhn_ok("4111111111111111")
    assert not luhn_ok("1234567890123456")
    assert not luhn_ok("123")


def test_iban_high_confidence() -> None:
    doc = make_doc(["IBAN: GB29 NWBK 6016 1331 9268 19"])
    out = IbanDetector().detect(doc, load_default_policy())
    assert len(out) == 1
    assert out[0].confidence == "high"


def test_iban_bad_checksum_filtered() -> None:
    doc = make_doc(["IBAN: GB00 NWBK 6016 1331 9268 19"])
    out = IbanDetector().detect(doc, load_default_policy())
    assert out == []


def test_iban_helper() -> None:
    assert iban_ok("GB29 NWBK 6016 1331 9268 19")
    assert not iban_ok("GB00 NWBK 6016 1331 9268 19")


def test_bank_account_label_anchored_medium() -> None:
    doc = make_doc(["Account: 9876543210"])
    out = BankAccountDetector().detect(doc, load_default_policy())
    assert len(out) == 1
    assert out[0].confidence == "medium"


def test_bank_account_skipped_if_luhn() -> None:
    doc = make_doc(["Account: 4111 1111 1111 1111"])
    out = BankAccountDetector().detect(doc, load_default_policy())
    assert out == []


def test_cvv_expiry_anchored_to_pan() -> None:
    doc = make_doc_block(["4111 1111 1111 1111", "Exp 09/27 CVV 123"])
    out = CvvExpiryDetector().detect(doc, load_default_policy())
    assert any(f.matched_text == "09/27" for f in out)
    assert any(f.matched_text == "123" for f in out)


def test_cvv_expiry_no_pan_no_match() -> None:
    doc = make_doc(["Exp 09/27 CVV 123"])
    out = CvvExpiryDetector().detect(doc, load_default_policy())
    assert out == []


def test_masked_account_asterisks() -> None:
    doc = make_doc(["******1234"])
    out = MaskedAccountDetector().detect(doc, load_default_policy())
    assert len(out) == 1
    assert out[0].rule_id == "FI-005"
    assert "1234" in out[0].matched_text
    assert out[0].confidence == "high"


def test_masked_account_uppercase_x() -> None:
    doc = make_doc(["XXXX1234"])
    out = MaskedAccountDetector().detect(doc, load_default_policy())
    assert len(out) == 1
    assert "1234" in out[0].matched_text


def test_masked_account_bullets() -> None:
    doc = make_doc(["••••5678"])
    out = MaskedAccountDetector().detect(doc, load_default_policy())
    assert len(out) == 1
    assert "5678" in out[0].matched_text


def test_masked_account_plain_digits_not_matched() -> None:
    doc = make_doc(["12345678"])
    out = MaskedAccountDetector().detect(doc, load_default_policy())
    assert out == []


def test_masked_account_short_mask_run_not_matched() -> None:
    # Single mask char is not enough — must be a run.
    doc = make_doc(["*1234"])
    out = MaskedAccountDetector().detect(doc, load_default_policy())
    assert out == []
