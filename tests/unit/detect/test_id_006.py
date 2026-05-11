"""ID-006 PersonNameNerDetector tests."""

from __future__ import annotations

import pytest

from redact_ai.errors import RedactError
from redact_ai.pipeline.detect.identity import PersonNameNerDetector
from redact_ai.policy.loader import load_default_policy
from tests.unit.detect._helpers import make_doc

spacy = pytest.importorskip("spacy")

try:
    spacy.load("en_core_web_md", disable=["lemmatizer", "tagger", "attribute_ruler"])
except OSError:
    pytest.skip(
        "en_core_web_md not available; run `python -m spacy download en_core_web_md`",
        allow_module_level=True,
    )


def test_non_western_name_detected() -> None:
    """The case that motivated ADR-011: ID-001 dictionary misses 'Nadeem Shaikh'."""
    doc = make_doc(["Nadeem Shaikh"])
    out = PersonNameNerDetector().detect(doc, load_default_policy())
    assert len(out) >= 1
    matched = " ".join(f.matched_text for f in out)
    assert "Nadeem" in matched and "Shaikh" in matched


def test_two_token_name_is_high_confidence() -> None:
    doc = make_doc(["Maria Garcia visited yesterday"])
    out = PersonNameNerDetector().detect(doc, load_default_policy())
    person_findings = [f for f in out if "Maria" in f.matched_text or "Garcia" in f.matched_text]
    assert person_findings, "expected at least one PERSON finding"
    assert any(f.confidence == "high" for f in person_findings)


def test_no_person_no_finding() -> None:
    doc = make_doc(["The quick brown fox jumps over the lazy dog"])
    out = PersonNameNerDetector().detect(doc, load_default_policy())
    assert out == []


def test_missing_model_raises_policy_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """If the configured model isn't available, fail closed with a clear error (ADR-005)."""
    doc = make_doc(["Nadeem Shaikh"])
    policy = load_default_policy()
    overridden = policy.model_copy(
        update={
            "detectors": tuple(
                det.model_copy(update={"overrides": {"model": "not_a_real_model_xyzzy"}})
                if det.id == "ID-006"
                else det
                for det in policy.detectors
            )
        }
    )
    with pytest.raises(RedactError):
        PersonNameNerDetector().detect(doc, overridden)
