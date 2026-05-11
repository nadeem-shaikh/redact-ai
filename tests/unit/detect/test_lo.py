"""LO-001 GPS detector tests."""

from __future__ import annotations

from redact_ai.pipeline.detect.location import GpsCoordsDetector
from redact_ai.policy.loader import load_default_policy
from tests.unit.detect._helpers import make_doc


def test_decimal_with_direction_markers() -> None:
    doc = make_doc(["37.4220 N, 122.0841 W"])
    out = GpsCoordsDetector().detect(doc, load_default_policy())
    assert len(out) == 1
    assert out[0].confidence == "high"


def test_decimal_with_degree_signs() -> None:
    doc = make_doc(["37.4220 °, 122.0841 °"])
    out = GpsCoordsDetector().detect(doc, load_default_policy())
    assert len(out) == 1


def test_bare_number_pair_ignored() -> None:
    doc = make_doc(["44 20"])
    out = GpsCoordsDetector().detect(doc, load_default_policy())
    assert out == []


def test_out_of_range_filtered() -> None:
    doc = make_doc(["91.0 N, 200.0 W"])
    out = GpsCoordsDetector().detect(doc, load_default_policy())
    assert out == []
