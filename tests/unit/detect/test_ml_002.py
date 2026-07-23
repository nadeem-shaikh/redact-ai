"""ML-002 OpenMedPiiDetector tests.

The OpenMed model cannot be downloaded in CI/sandbox environments, so these
tests mock the pipeline loader with a deterministic fake whose ``__call__``
locates configured substrings in the line text. This exercises the detector's
mapping, confidence, override-validation, and fail-closed logic without the
transformer runtime.
"""

from __future__ import annotations

import pytest

from redact_ai.errors import RedactError
from redact_ai.pipeline.detect import ner_openmed
from redact_ai.pipeline.detect.ner_openmed import OpenMedPiiDetector
from redact_ai.policy.loader import load_default_policy
from redact_ai.policy.schema import Policy
from tests.unit.detect._helpers import make_doc


class FakePipeline:
    """Deterministic stand-in for an OpenMed token-classification pipeline.

    ``spans`` is a list of ``(substring, entity_group, score)``. On each line the
    fake returns an entity for every configured substring it finds, with correct
    character offsets so the token round-trip is real.
    """

    def __init__(self, spans: list[tuple[str, str, float]]) -> None:
        self._spans = spans

    def __call__(self, text: str) -> list[dict[str, object]]:
        out: list[dict[str, object]] = []
        for substring, group, score in self._spans:
            idx = text.find(substring)
            if idx < 0:
                continue
            out.append(
                {
                    "start": idx,
                    "end": idx + len(substring),
                    "entity_group": group,
                    "score": score,
                    "word": substring,
                }
            )
        return out


@pytest.fixture(autouse=True)
def _clear_loader_cache():
    ner_openmed._load_openmed.cache_clear()
    yield
    ner_openmed._load_openmed.cache_clear()


def _patch_pipeline(monkeypatch: pytest.MonkeyPatch, spans: list[tuple[str, str, float]]) -> None:
    fake = FakePipeline(spans)
    monkeypatch.setattr(ner_openmed, "_load_openmed", lambda *a, **k: fake)


def _capture_loader(monkeypatch: pytest.MonkeyPatch, spans=None) -> dict:
    """Patch the loader to record its (model, revision, local_files_only) args."""
    captured: dict = {}

    def _fake(model_name, revision, local_files_only):
        captured["model"] = model_name
        captured["revision"] = revision
        captured["local_files_only"] = local_files_only
        return FakePipeline(spans or [])

    monkeypatch.setattr(ner_openmed, "_load_openmed", _fake)
    return captured


def test_first_and_last_name_detected(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_pipeline(
        monkeypatch,
        [("John", "first_name", 0.99), ("Smith", "last_name", 0.98)],
    )
    doc = make_doc(["John Smith"])
    out = OpenMedPiiDetector().detect(doc, load_default_policy())
    assert len(out) == 2
    assert all(f.rule_id == "ML-002" for f in out)
    assert all(f.category == "IDENTITY" for f in out)
    assert {f.matched_text for f in out} == {"John", "Smith"}


def test_structured_phi_categories(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_pipeline(
        monkeypatch,
        [
            ("03/11/1985", "date_of_birth", 0.95),
            ("789456", "medical_record_number", 0.9),
        ],
    )
    doc = make_doc(["DOB 03/11/1985 MRN 789456"])
    out = OpenMedPiiDetector().detect(doc, load_default_policy())
    cats = {f.matched_text: f.category for f in out}
    assert cats["03/11/1985"] == "IDENTITY"
    assert cats["789456"] == "HEALTH"


def test_score_below_threshold_dropped(monkeypatch: pytest.MonkeyPatch) -> None:
    # Below the 0.5 default — the garble OpenMed emits on noise (e.g. cvv '268')
    # must not survive.
    _patch_pipeline(monkeypatch, [("268", "cvv", 0.42)])
    doc = make_doc(["pm 268"])
    out = OpenMedPiiDetector().detect(doc, load_default_policy())
    assert out == []


def test_unmapped_label_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_pipeline(monkeypatch, [("Acme", "organization", 0.99)])
    doc = make_doc(["Acme Corp"])
    out = OpenMedPiiDetector().detect(doc, load_default_policy())
    assert out == []


def test_ocr_confidence_caps_finding(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_pipeline(monkeypatch, [("John", "first_name", 0.99)])
    # A high-score hit sitting on a low-OCR-confidence token is capped down.
    doc = make_doc(["John"], token_confidence=0.30)
    out = OpenMedPiiDetector().detect(doc, load_default_policy())
    assert len(out) == 1
    assert out[0].confidence == "low"


def test_score_threshold_override_validated() -> None:
    policy = _policy_with_override({"score_threshold": 1.5})
    with pytest.raises(RedactError):
        OpenMedPiiDetector().detect(make_doc(["x"]), policy)


def test_empty_model_override_rejected() -> None:
    policy = _policy_with_override({"model": ""})
    with pytest.raises(RedactError):
        OpenMedPiiDetector().detect(make_doc(["x"]), policy)


def test_bad_labels_override_rejected() -> None:
    policy = _policy_with_override({"labels": {"first_name": "NOT_A_CATEGORY"}})
    with pytest.raises(RedactError):
        OpenMedPiiDetector().detect(make_doc(["x"]), policy)


def test_labels_override_applied(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_pipeline(monkeypatch, [("secret", "custom_secret", 0.99)])
    policy = _policy_with_override({"labels": {"custom_secret": "CREDENTIALS"}})
    out = OpenMedPiiDetector().detect(make_doc(["secret value"]), policy)
    assert len(out) == 1
    assert out[0].category == "CREDENTIALS"


def test_missing_runtime_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(*a, **k):
        raise RuntimeError("OpenMed model 'x' could not be loaded. install hint")

    monkeypatch.setattr(ner_openmed, "_load_openmed", _raise)
    with pytest.raises(RedactError):
        OpenMedPiiDetector().detect(make_doc(["John Smith"]), load_default_policy())


def test_deterministic(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_pipeline(monkeypatch, [("John", "first_name", 0.99)])
    doc = make_doc(["John Smith"])
    a = OpenMedPiiDetector().detect(doc, load_default_policy())
    b = OpenMedPiiDetector().detect(doc, load_default_policy())
    assert [(f.matched_text, f.category, f.confidence) for f in a] == [
        (f.matched_text, f.category, f.confidence) for f in b
    ]


def test_default_model_pinned_and_offline(monkeypatch: pytest.MonkeyPatch) -> None:
    cap = _capture_loader(monkeypatch)
    OpenMedPiiDetector().detect(make_doc(["x"]), load_default_policy())
    assert cap["model"] == ner_openmed._DEFAULT_MODEL
    assert cap["revision"] == ner_openmed._DEFAULT_MODEL_REVISION
    assert cap["local_files_only"] is True  # offline by default (ADR-002)


def test_model_override_unpins_default_revision(monkeypatch: pytest.MonkeyPatch) -> None:
    cap = _capture_loader(monkeypatch)
    policy = _policy_with_override({"model": "some/other-model"})
    OpenMedPiiDetector().detect(make_doc(["x"]), policy)
    assert cap["model"] == "some/other-model"
    assert cap["revision"] is None  # a different repo has its own history


def test_revision_override_applied(monkeypatch: pytest.MonkeyPatch) -> None:
    cap = _capture_loader(monkeypatch)
    policy = _policy_with_override({"model": "some/other-model", "revision": "abc123"})
    OpenMedPiiDetector().detect(make_doc(["x"]), policy)
    assert cap["revision"] == "abc123"


def test_allow_download_inverts_offline(monkeypatch: pytest.MonkeyPatch) -> None:
    cap = _capture_loader(monkeypatch)
    policy = _policy_with_override({"allow_download": True})
    OpenMedPiiDetector().detect(make_doc(["x"]), policy)
    assert cap["local_files_only"] is False


def test_score_threshold_override_filters(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_pipeline(monkeypatch, [("John", "first_name", 0.60)])
    # Default 0.5 would keep a 0.60 hit; an override of 0.8 must drop it.
    policy = _policy_with_override({"score_threshold": 0.8})
    assert OpenMedPiiDetector().detect(make_doc(["John"]), policy) == []


@pytest.mark.parametrize(
    "score,expected",
    [(0.85, "high"), (0.84, "medium"), (0.65, "medium"), (0.64, "low"), (0.50, "low")],
)
def test_score_confidence_boundaries(
    monkeypatch: pytest.MonkeyPatch, score: float, expected: str
) -> None:
    _patch_pipeline(monkeypatch, [("John", "first_name", score)])
    out = OpenMedPiiDetector().detect(make_doc(["John"]), load_default_policy())
    assert len(out) == 1
    assert out[0].confidence == expected


def test_multi_line_document(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_pipeline(
        monkeypatch,
        [("John", "first_name", 0.9), ("Smith", "last_name", 0.9), ("Acme", "occupation", 0.9)],
    )
    doc = make_doc(["John", "Smith", "Acme"])
    out = OpenMedPiiDetector().detect(doc, load_default_policy())
    assert {f.matched_text for f in out} == {"John", "Smith", "Acme"}


def _policy_with_override(overrides: dict) -> Policy:
    base = load_default_policy().model_dump()
    detectors = list(base["detectors"])
    for det in detectors:
        if det["id"] == "ML-002":
            det["enabled"] = True
            det["overrides"] = overrides
            break
    else:
        detectors.append(
            {"id": "ML-002", "enabled": True, "threshold": "low", "overrides": overrides}
        )
    base["detectors"] = detectors
    return Policy.model_validate(base)
