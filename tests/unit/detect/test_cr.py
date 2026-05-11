"""CREDENTIALS detector tests (CR-001..CR-003)."""

from __future__ import annotations

from redact_ai.pipeline.detect.credentials import (
    CloudKeyDetector,
    HighEntropyTokenDetector,
    SshPrivateKeyDetector,
    shannon_bits_per_char,
)
from redact_ai.policy.loader import load_default_policy
from tests.unit.detect._helpers import make_doc, make_doc_block


def test_shannon_entropy() -> None:
    assert shannon_bits_per_char("aaaa") < 1.0
    assert shannon_bits_per_char("a1b2c3d4e5f6") > 3.0


def test_high_entropy_with_keyword_context_high() -> None:
    doc = make_doc(["api_key sk-Tg7HsfRqLk9PzZmXwVuC4Bn2"])
    out = HighEntropyTokenDetector().detect(doc, load_default_policy())
    assert any(f.confidence == "high" for f in out)


def test_low_entropy_string_skipped() -> None:
    doc = make_doc(["aaaaaaaaaaaaaaaaaaaaa"])
    out = HighEntropyTokenDetector().detect(doc, load_default_policy())
    assert out == []


def test_cloud_key_aws() -> None:
    doc = make_doc(["AKIAIOSFODNN7EXAMPLE"])
    out = CloudKeyDetector().detect(doc, load_default_policy())
    assert len(out) == 1
    assert out[0].confidence == "high"


def test_cloud_key_negative() -> None:
    doc = make_doc(["JUSTSOMETEXT"])
    out = CloudKeyDetector().detect(doc, load_default_policy())
    assert out == []


def test_ssh_block_redacted() -> None:
    doc = make_doc_block(
        [
            "-----BEGIN OPENSSH PRIVATE KEY-----",
            "abc123abc123abc123",
            "-----END OPENSSH PRIVATE KEY-----",
        ]
    )
    out = SshPrivateKeyDetector().detect(doc, load_default_policy())
    assert len(out) == 1


def test_ssh_no_marker() -> None:
    doc = make_doc(["just some lines"])
    out = SshPrivateKeyDetector().detect(doc, load_default_policy())
    assert out == []
