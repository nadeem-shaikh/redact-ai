"""Manifest builder tests (BUILD_SPEC §9)."""

from __future__ import annotations

from redact_ai.models.document import BBox
from redact_ai.models.findings import Finding
from redact_ai.pipeline.report import build_manifest
from redact_ai.policy.loader import load_default_policy


def _finding(rule: str, category: str, x: int, y: int, idx: int = 0) -> Finding:
    return Finding(
        rule_id=rule,
        category=category,  # type: ignore[arg-type]
        bbox=BBox(x=x, y=y, w=10, h=10),
        confidence="high",
        matched_text=f"secret-{idx}",
        page_index=0,
    )


def test_findings_sorted_and_numbered() -> None:
    policy = load_default_policy()
    findings = [
        _finding("ID-001", "IDENTITY", 50, 100, 0),
        _finding("CO-001", "CONTACT", 10, 50, 0),
        _finding("ID-001", "IDENTITY", 30, 50, 1),
    ]
    manifest = build_manifest(
        policy=policy,
        runtime_version="0.1.0",
        ocr_engine="tesseract-5.3.4",
        input_hash="x" * 64,
        output_hash="y" * 64,
        created_at="2026-05-11T00:00:00Z",
        findings=findings,
        warnings=[],
        include_matched_text=False,
    )
    # Sorted by (page, y, x, rule_id).
    ids = [f.id for f in manifest.findings]
    assert ids == ["f-CO-001-0", "f-ID-001-0", "f-ID-001-1"]
    # matched_text suppressed in non-verbose mode (ADR-006).
    assert all(f.matched_text is None for f in manifest.findings)


def test_verbose_mode_includes_matched_text() -> None:
    policy = load_default_policy()
    findings = [_finding("ID-001", "IDENTITY", 10, 10, 0)]
    manifest = build_manifest(
        policy=policy,
        runtime_version="0.1.0",
        ocr_engine="tesseract-5.3.4",
        input_hash="x" * 64,
        output_hash="y" * 64,
        created_at="2026-05-11T00:00:00Z",
        findings=findings,
        warnings=[],
        include_matched_text=True,
    )
    assert manifest.findings[0].matched_text == "secret-0"


def test_stats_count_by_category() -> None:
    policy = load_default_policy()
    findings = [
        _finding("ID-001", "IDENTITY", 0, 0, 0),
        _finding("ID-001", "IDENTITY", 0, 50, 1),
        _finding("CO-001", "CONTACT", 0, 100, 0),
    ]
    manifest = build_manifest(
        policy=policy,
        runtime_version="0.1.0",
        ocr_engine="tesseract-5.3.4",
        input_hash="x" * 64,
        output_hash="y" * 64,
        created_at="2026-05-11T00:00:00Z",
        findings=findings,
        warnings=[],
        include_matched_text=False,
    )
    assert manifest.stats.redactions_total == 3
    assert manifest.stats.by_category == {"IDENTITY": 2, "CONTACT": 1}
