"""Fail-closed semantics for detector failures in the pipeline (ADR-005).

A configuration/availability failure (E_POLICY) from an opted-in detector —
e.g. ML-001 when the `strong` extra or model is missing — must fail the whole
request, not degrade to a partial-failure warning while other detectors
succeed. Unexpected runtime detector bugs still degrade gracefully (FR-8.2).
"""

from __future__ import annotations

import pytest

from redact_ai.errors import RedactError
from redact_ai.models.manifest import Warning
from redact_ai.pipeline import _run_detectors
from redact_ai.pipeline.detect import ner_gliner
from redact_ai.pipeline.detect.contact import EmailDetector
from redact_ai.policy.loader import load_policy
from tests.unit.detect._helpers import make_doc

_ML_PLUS_EMAIL = """
id: strong-test
version: 0.1.0
detectors:
  - id: CO-001
    enabled: true
    threshold: low
  - id: ML-001
    enabled: true
    threshold: low
"""

_TWO_CONTACT = """
id: contact-test
version: 0.1.0
detectors:
  - id: CO-001
    enabled: true
    threshold: low
  - id: CO-002
    enabled: true
    threshold: low
"""


def test_ml001_load_failure_is_fatal_even_when_others_succeed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # CO-001 succeeds; ML-001's model load fails -> the whole run must fail closed.
    def _raise(model_name: str, revision: object, local_files_only: object) -> object:
        raise RuntimeError("GLiNER is required for ML-001 but is not installed.")

    monkeypatch.setattr(ner_gliner, "_load_gliner", _raise)
    doc = make_doc(["Email jane@acme.com"])
    with pytest.raises(RedactError) as exc:
        _run_detectors(doc, load_policy(_ML_PLUS_EMAIL), [])
    assert exc.value.code == "E_POLICY"


def test_runtime_detector_bug_is_tolerated(monkeypatch: pytest.MonkeyPatch) -> None:
    # An unexpected runtime exception in one detector degrades to a warning when
    # another detector still succeeds — it does not fail the request.
    def _boom(self: EmailDetector, doc: object, policy: object) -> list:
        raise ValueError("unexpected runtime bug")

    monkeypatch.setattr(EmailDetector, "detect", _boom)
    doc = make_doc(["Call +1 415 555 0100"])
    warnings: list[Warning] = []
    out = _run_detectors(doc, load_policy(_TWO_CONTACT), warnings)
    assert any(w.code == "W_DETECTOR_PARTIAL_FAILURE" for w in warnings)
    # CO-002 (phone) still ran, so we get its findings rather than an exception.
    assert isinstance(out, list)
