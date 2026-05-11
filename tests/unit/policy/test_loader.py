"""Policy loader tests (BUILD_SPEC §6)."""

from __future__ import annotations

from pathlib import Path

import pytest

from redact_ai.errors import RedactError
from redact_ai.policy.loader import builtin_policies, load_default_policy, load_policy


def test_default_policy_round_trip() -> None:
    policy = load_default_policy()
    assert policy.id == "default"
    assert policy.version == "0.1.0"
    assert policy.posture == "strict"
    assert any(d.id == "FI-001" and d.enabled for d in policy.detectors)
    assert any(d.id == "HE-002" and not d.enabled for d in policy.detectors)


def test_builtin_policies_returns_default() -> None:
    policies = builtin_policies()
    assert any(p.id == "default" for p in policies)


def test_policy_yaml_matches_shipped(repo_root: Path) -> None:
    shipped = (repo_root / "examples" / "default_policy.yaml").read_text()
    packaged = (repo_root / "src" / "redact_ai" / "resources" / "default_policy.yaml").read_text()
    assert shipped == packaged


def test_load_policy_invalid_id_raises() -> None:
    with pytest.raises(RedactError) as exc:
        load_policy("id: not valid!\nversion: 0.1.0\ndetectors: []\n")
    assert exc.value.code == "E_POLICY"


def test_load_policy_duplicate_detector_raises() -> None:
    yaml = """
id: dup
version: 0.1.0
detectors:
  - id: ID-001
    enabled: true
    threshold: low
  - id: ID-001
    enabled: true
    threshold: low
"""
    with pytest.raises(RedactError):
        load_policy(yaml)


def test_load_policy_unknown_detector_passes_schema() -> None:
    """Unknown rule IDs only fail at *build_detectors* time, not at parse time."""
    yaml = """
id: weird
version: 0.1.0
detectors:
  - id: ZZ-999
    enabled: true
    threshold: low
"""
    load_policy(yaml)


def test_lenient_posture_raises_thresholds() -> None:
    yaml = """
id: lenient
version: 0.1.0
posture: lenient
detectors:
  - id: ID-001
    enabled: true
    threshold: low
  - id: ID-002
    enabled: true
    threshold: medium
  - id: ID-003
    enabled: true
    threshold: high
"""
    policy = load_policy(yaml)
    refs = {d.id: d for d in policy.detectors}
    assert policy.effective_threshold(refs["ID-001"]) == "medium"
    assert policy.effective_threshold(refs["ID-002"]) == "high"
    assert policy.effective_threshold(refs["ID-003"]) == "high"


def test_policy_inline_yaml_error() -> None:
    with pytest.raises(RedactError):
        load_policy("id: [unclosed\n")
