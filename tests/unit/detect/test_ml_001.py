"""ML-001 GlinerPiiDetector tests.

The GLiNER model cannot be downloaded in CI/sandbox environments, so these
tests mock the model loader with a deterministic fake whose ``predict_entities``
locates configured substrings in the line text. This exercises the detector's
mapping, confidence, override-validation, and fail-closed logic without the
transformer runtime.
"""

from __future__ import annotations

import pytest

from redact_ai.errors import RedactError
from redact_ai.pipeline.detect import ner_gliner
from redact_ai.pipeline.detect.ner_gliner import GlinerPiiDetector
from redact_ai.policy.loader import load_default_policy
from redact_ai.policy.schema import Policy
from tests.unit.detect._helpers import make_doc


class FakeGliner:
    """Deterministic stand-in for a GLiNER model.

    ``spans`` is a list of ``(substring, label, score)``. On each line the fake
    returns an entity for every configured substring it finds, with correct
    character offsets so the token round-trip is real.
    """

    def __init__(self, spans: list[tuple[str, str, float]]) -> None:
        self._spans = spans

    def eval(self) -> None:  # pragma: no cover - trivial
        pass

    def predict_entities(
        self, text: str, labels: list[str], threshold: float = 0.5
    ) -> list[dict[str, object]]:
        out: list[dict[str, object]] = []
        for substring, label, score in self._spans:
            if score < threshold:
                continue
            idx = text.find(substring)
            if idx < 0:
                continue
            out.append(
                {
                    "start": idx,
                    "end": idx + len(substring),
                    "label": label,
                    "score": score,
                    "text": substring,
                }
            )
        return out


def _use_fake(monkeypatch: pytest.MonkeyPatch, spans: list[tuple[str, str, float]]) -> None:
    monkeypatch.setattr(ner_gliner, "_load_gliner", lambda model_name: FakeGliner(spans))


def _policy_with_ml_overrides(overrides: dict[str, object]) -> Policy:
    policy = load_default_policy()
    return policy.model_copy(
        update={
            "detectors": tuple(
                det.model_copy(update={"enabled": True, "overrides": overrides})
                if det.id == "ML-001"
                else det
                for det in policy.detectors
            )
        }
    )


def test_person_span_maps_to_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    _use_fake(monkeypatch, [("Nadeem Shaikh", "person", 0.9)])
    doc = make_doc(["Contact Nadeem Shaikh today"])
    out = GlinerPiiDetector().detect(doc, load_default_policy())
    assert len(out) == 1
    finding = out[0]
    assert finding.rule_id == "ML-001"
    assert finding.category == "IDENTITY"
    assert finding.matched_text == "Nadeem Shaikh"
    # bbox spans both name tokens, not the surrounding words.
    assert finding.bbox.w > 0 and finding.bbox.h > 0


def test_category_mapping_across_labels(monkeypatch: pytest.MonkeyPatch) -> None:
    _use_fake(
        monkeypatch,
        [
            ("jane@acme.com", "email address", 0.9),
            ("4111111111111111", "credit card number", 0.95),
        ],
    )
    doc = make_doc(["Email jane@acme.com card 4111111111111111"])
    out = GlinerPiiDetector().detect(doc, load_default_policy())
    cats = {f.matched_text: f.category for f in out}
    assert cats["jane@acme.com"] == "CONTACT"
    assert cats["4111111111111111"] == "FINANCIAL"


@pytest.mark.parametrize(
    ("score", "expected"),
    [(0.95, "high"), (0.7, "medium"), (0.55, "low")],
)
def test_score_maps_to_confidence(
    monkeypatch: pytest.MonkeyPatch, score: float, expected: str
) -> None:
    _use_fake(monkeypatch, [("Nadeem Shaikh", "person", score)])
    # High OCR confidence (default 0.95) so it does not cap the detector tier.
    doc = make_doc(["Nadeem Shaikh"])
    out = GlinerPiiDetector().detect(doc, load_default_policy())
    assert out and out[0].confidence == expected


def test_low_ocr_confidence_caps_finding(monkeypatch: pytest.MonkeyPatch) -> None:
    _use_fake(monkeypatch, [("Nadeem Shaikh", "person", 0.99)])
    doc = make_doc(["Nadeem Shaikh"], token_confidence=0.5)  # low OCR floor
    out = GlinerPiiDetector().detect(doc, load_default_policy())
    assert out and out[0].confidence == "low"


def test_no_entities_no_findings(monkeypatch: pytest.MonkeyPatch) -> None:
    _use_fake(monkeypatch, [])
    doc = make_doc(["Nothing sensitive here"])
    assert GlinerPiiDetector().detect(doc, load_default_policy()) == []


def test_unknown_label_is_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    _use_fake(monkeypatch, [("Acme Corp", "organization", 0.9)])
    doc = make_doc(["Acme Corp filed the report"])
    assert GlinerPiiDetector().detect(doc, load_default_policy()) == []


def test_missing_gliner_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(model_name: str) -> object:
        raise RuntimeError("GLiNER is required for ML-001 but is not installed.")

    monkeypatch.setattr(ner_gliner, "_load_gliner", _raise)
    doc = make_doc(["Nadeem Shaikh"])
    with pytest.raises(RedactError) as exc:
        GlinerPiiDetector().detect(doc, load_default_policy())
    assert exc.value.code == "E_POLICY"


def test_model_override_applied(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, str] = {}

    def _loader(model_name: str) -> object:
        seen["model"] = model_name
        return FakeGliner([("Nadeem Shaikh", "person", 0.9)])

    monkeypatch.setattr(ner_gliner, "_load_gliner", _loader)
    policy = _policy_with_ml_overrides({"model": "urchade/gliner_multi_pii-v1"})
    GlinerPiiDetector().detect(make_doc(["Nadeem Shaikh"]), policy)
    assert seen["model"] == "urchade/gliner_multi_pii-v1"


def test_score_threshold_override_filters(monkeypatch: pytest.MonkeyPatch) -> None:
    _use_fake(monkeypatch, [("Nadeem Shaikh", "person", 0.6)])
    policy = _policy_with_ml_overrides({"score_threshold": 0.8})
    # 0.6 < 0.8 threshold → the fake drops it.
    assert GlinerPiiDetector().detect(make_doc(["Nadeem Shaikh"]), policy) == []


def test_label_map_override(monkeypatch: pytest.MonkeyPatch) -> None:
    _use_fake(monkeypatch, [("Room 12B", "room number", 0.9)])
    policy = _policy_with_ml_overrides({"labels": {"room number": "LOCATION"}})
    out = GlinerPiiDetector().detect(make_doc(["Meet at Room 12B please"]), policy)
    assert len(out) == 1 and out[0].category == "LOCATION"


@pytest.mark.parametrize(
    "overrides",
    [
        {"model": ""},
        {"score_threshold": 2},
        {"score_threshold": True},
        {"score_threshold": "high"},
        {"labels": {}},
        {"labels": {"person": "NOPE"}},
    ],
)
def test_invalid_overrides_raise(
    monkeypatch: pytest.MonkeyPatch, overrides: dict[str, object]
) -> None:
    _use_fake(monkeypatch, [("Nadeem Shaikh", "person", 0.9)])
    policy = _policy_with_ml_overrides(overrides)
    with pytest.raises(RedactError) as exc:
        GlinerPiiDetector().detect(make_doc(["Nadeem Shaikh"]), policy)
    assert exc.value.code == "E_POLICY"
