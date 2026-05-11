"""CU-001 custom regex detector tests."""

from __future__ import annotations

import pytest

from redact_ai.errors import RedactError
from redact_ai.pipeline.detect.custom import CustomRegexDetector
from redact_ai.policy.loader import load_policy
from redact_ai.policy.schema import Policy
from tests.unit.detect._helpers import make_doc


def _policy_with_cu(pattern: str) -> Policy:
    yaml = f"""
id: custom-test
version: 0.1.0
detectors:
  - id: CU-001
    enabled: true
    threshold: low
    overrides:
      kind: regex
      pattern: "{pattern}"
      category: CUSTOM
      confidence: medium
"""
    return load_policy(yaml)


def test_custom_regex_matches() -> None:
    policy = _policy_with_cu(r"INTERNAL-[0-9]{6}")
    doc = make_doc(["This is INTERNAL-123456 token"])
    out = CustomRegexDetector().detect(doc, policy)
    assert len(out) == 1
    assert out[0].matched_text == "INTERNAL-123456"


def test_invalid_regex_raises() -> None:
    policy = _policy_with_cu(r"(")
    doc = make_doc(["whatever"])
    with pytest.raises(RedactError) as exc:
        CustomRegexDetector().detect(doc, policy)
    assert exc.value.code == "E_POLICY"


def test_dictionary_kind() -> None:
    yaml = """
id: custom-dict
version: 0.1.0
detectors:
  - id: CU-001
    enabled: true
    threshold: low
    overrides:
      kind: dictionary
      words: ["secret-word"]
      category: CUSTOM
      confidence: medium
"""
    policy = load_policy(yaml)
    doc = make_doc(["leading secret-word trailing"])
    out = CustomRegexDetector().detect(doc, policy)
    assert len(out) == 1


def test_not_in_policy_returns_empty() -> None:
    from redact_ai.policy.loader import load_default_policy

    doc = make_doc(["anything"])
    out = CustomRegexDetector().detect(doc, load_default_policy())
    assert out == []
