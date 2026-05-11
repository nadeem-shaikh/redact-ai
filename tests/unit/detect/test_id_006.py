"""ID-006 PersonNameNerDetector tests."""

from __future__ import annotations

import pytest

from redact_ai.errors import RedactError
from redact_ai.pipeline.detect.identity import PersonNameNerDetector, _name_variants
from redact_ai.policy.loader import load_default_policy
from tests.unit.detect._helpers import make_doc

spacy = pytest.importorskip("spacy")


def _require_en_core_web_md() -> None:
    """Skip individual tests when the model is absent.

    Scoped per-test so ``test_missing_model_raises_policy_error`` can
    still run when the model is intentionally unavailable — that test
    is the model-absent fail-closed coverage.
    """
    try:
        spacy.load(
            "en_core_web_md",
            disable=["parser", "lemmatizer", "tagger", "attribute_ruler"],
        )
    except OSError:
        pytest.skip(
            "en_core_web_md not available; run `python -m spacy download en_core_web_md`",
        )


def test_non_western_name_detected() -> None:
    """The case that motivated ADR-011: ID-001 dictionary misses 'Nadeem Shaikh'."""
    _require_en_core_web_md()
    doc = make_doc(["Nadeem Shaikh"])
    out = PersonNameNerDetector().detect(doc, load_default_policy())
    assert len(out) >= 1
    matched = " ".join(f.matched_text for f in out)
    assert "Nadeem" in matched and "Shaikh" in matched


def test_two_token_name_is_high_confidence() -> None:
    _require_en_core_web_md()
    doc = make_doc(["Maria Garcia visited yesterday"])
    out = PersonNameNerDetector().detect(doc, load_default_policy())
    person_findings = [f for f in out if "Maria" in f.matched_text or "Garcia" in f.matched_text]
    assert person_findings, "expected at least one PERSON finding"
    assert any(f.confidence == "high" for f in person_findings)


def test_no_person_no_finding() -> None:
    _require_en_core_web_md()
    doc = make_doc(["The quick brown fox jumps over the lazy dog"])
    out = PersonNameNerDetector().detect(doc, load_default_policy())
    assert out == []


def test_name_variants_includes_github_username_form() -> None:
    """The motivating screenshot had `nadeem-shaikh` appear in repo paths."""
    variants = _name_variants("Nadeem Shaikh")
    assert "nadeem-shaikh" in variants
    assert "nadeem_shaikh" in variants
    assert "nadeem.shaikh" in variants
    assert "nadeemshaikh" in variants
    # First-initial + last forms should also be there.
    assert "nshaikh" in variants
    # Standalone first/last name forms (e.g. `nadeem/redact-ai`).
    assert "nadeem" in variants
    assert "shaikh" in variants


def test_name_variants_skip_too_short() -> None:
    """Variants shorter than `_MIN_VARIANT_LEN` are excluded as too generic."""
    variants = _name_variants("A B")
    assert variants == set(), variants


def test_variant_match_catches_repo_paths() -> None:
    """`nadeem-shaikh/redact-ai`, `nadeem/redact-ai`, and `shaikh/redact-ai`
    should all be redacted once `Nadeem Shaikh` is detected."""
    _require_en_core_web_md()
    doc = make_doc(
        [
            "Nadeem Shaikh",
            "nadeem-shaikh/scripts",
            "nadeem-shaikh/redact-ai",
            "nadeem/redact-ai",
            "shaikh/redact-ai",
            "Across-Finance/pools",
        ]
    )
    out = PersonNameNerDetector().detect(doc, load_default_policy())
    matched_lower = {f.matched_text.lower() for f in out}
    # Primary NER hit on the full name.
    assert any("nadeem" in m and "shaikh" in m for m in matched_lower), matched_lower
    # Combined slug form.
    assert "nadeem-shaikh" in matched_lower, matched_lower
    # Standalone first / last name forms.
    assert "nadeem" in matched_lower, matched_lower
    assert "shaikh" in matched_lower, matched_lower
    # Untouched: an unrelated org name.
    assert not any("across-finance" in m for m in matched_lower), matched_lower


def test_variant_match_skipped_when_no_person_detected() -> None:
    """Without a detected PERSON, variant scanning emits nothing (no anchor)."""
    _require_en_core_web_md()
    doc = make_doc(["random-slug-string/some-repo", "another-org/another-repo"])
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
