"""HEALTH detector tests (HE-001..HE-003)."""

from __future__ import annotations

from redact_ai.pipeline.detect.health import (
    Icd10Detector,
    MrnDetector,
    PrescriptionDetector,
)
from redact_ai.policy.loader import load_default_policy
from tests.unit.detect._helpers import make_doc


def test_mrn_match() -> None:
    doc = make_doc(["MRN: 0001234"])
    out = MrnDetector().detect(doc, load_default_policy())
    assert len(out) == 1
    assert out[0].confidence == "high"


def test_mrn_no_digits_skipped() -> None:
    doc = make_doc(["MRN: ABCDEFG"])
    out = MrnDetector().detect(doc, load_default_policy())
    assert out == []


def test_icd10_match() -> None:
    doc = make_doc(["Diagnosis E11.9"])
    out = Icd10Detector().detect(doc, load_default_policy())
    assert any(f.matched_text == "E11.9" for f in out)


def test_icd10_negative() -> None:
    doc = make_doc(["abc 12"])
    out = Icd10Detector().detect(doc, load_default_policy())
    assert out == []


def test_prescription_match() -> None:
    doc = make_doc(["Rx Metformin 500mg"])
    out = PrescriptionDetector().detect(doc, load_default_policy())
    assert len(out) == 1


def test_prescription_no_keyword() -> None:
    doc = make_doc(["random words"])
    out = PrescriptionDetector().detect(doc, load_default_policy())
    assert out == []
