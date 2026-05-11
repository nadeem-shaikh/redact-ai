"""Merge algorithm property tests (BUILD_SPEC §11)."""

from __future__ import annotations

import random

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from redact_ai.models.document import BBox
from redact_ai.models.findings import Finding
from redact_ai.pipeline.merge import merge_findings

CATEGORIES = ["IDENTITY", "CONTACT", "FINANCIAL"]


@st.composite
def _finding(draw) -> Finding:
    x = draw(st.integers(min_value=0, max_value=400))
    y = draw(st.integers(min_value=0, max_value=400))
    w = draw(st.integers(min_value=10, max_value=80))
    h = draw(st.integers(min_value=10, max_value=40))
    category = draw(st.sampled_from(CATEGORIES))
    confidence = draw(st.sampled_from(["low", "medium", "high"]))
    rule = draw(st.sampled_from(["ID-001", "CO-001", "FI-001"]))
    return Finding(
        rule_id=rule,
        category=category,
        bbox=BBox(x=x, y=y, w=w, h=h),
        confidence=confidence,
        matched_text="x",
        page_index=0,
    )


@settings(max_examples=80, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(st.lists(_finding(), min_size=0, max_size=20))
def test_merge_idempotent(findings: list[Finding]) -> None:
    once = merge_findings(findings)
    twice = merge_findings(once)
    assert _key(once) == _key(twice)


@settings(max_examples=80, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(st.lists(_finding(), min_size=0, max_size=15))
def test_merge_order_independent(findings: list[Finding]) -> None:
    shuffled = list(findings)
    random.Random(123).shuffle(shuffled)
    assert _key(merge_findings(findings)) == _key(merge_findings(shuffled))


def _key(findings: list[Finding]) -> list[tuple]:
    return sorted(
        (
            f.category,
            f.page_index,
            f.bbox.x,
            f.bbox.y,
            f.bbox.w,
            f.bbox.h,
            f.confidence,
        )
        for f in findings
    )


def test_merge_combines_overlapping_same_category() -> None:
    a = Finding(
        rule_id="ID-001",
        category="IDENTITY",
        bbox=BBox(x=0, y=0, w=20, h=20),
        confidence="medium",
        matched_text="A",
    )
    b = Finding(
        rule_id="ID-002",
        category="IDENTITY",
        bbox=BBox(x=10, y=5, w=20, h=20),
        confidence="high",
        matched_text="B",
    )
    out = merge_findings([a, b])
    assert len(out) == 1
    assert out[0].rule_id == "ID-002"
    assert out[0].confidence == "high"
    assert "ID-001" in out[0].merged_from


def test_merge_keeps_different_categories_apart() -> None:
    a = Finding(
        rule_id="ID-001",
        category="IDENTITY",
        bbox=BBox(x=0, y=0, w=20, h=20),
        confidence="high",
        matched_text="",
    )
    b = Finding(
        rule_id="CO-001",
        category="CONTACT",
        bbox=BBox(x=0, y=0, w=20, h=20),
        confidence="high",
        matched_text="",
    )
    out = merge_findings([a, b])
    assert len(out) == 2


def test_merge_skips_already_consumed_inner_index() -> None:
    """Cover the ``if j in consumed: continue`` path.

    F0 has a tall bbox; sorted order is [F0, F1, F2]. The inner loop
    rejects (F0, F1) but accepts (F0, F2). After consuming F2, the next
    outer iteration (F1) re-enters the inner loop and immediately hits
    the already-consumed index (= line 91 in pipeline/merge.py).
    """
    f0 = Finding(
        rule_id="ID-001",
        category="IDENTITY",
        bbox=BBox(x=0, y=0, w=50, h=100),
        confidence="high",
        matched_text="",
    )
    f1 = Finding(
        rule_id="ID-002",
        category="IDENTITY",
        bbox=BBox(x=80, y=30, w=10, h=10),  # 30 px to the right of F0 — no merge
        confidence="high",
        matched_text="",
    )
    f2 = Finding(
        rule_id="ID-003",
        category="IDENTITY",
        bbox=BBox(x=0, y=80, w=60, h=30),  # overlaps F0 at its bottom
        confidence="high",
        matched_text="",
    )
    out = merge_findings([f0, f1, f2])
    # F0 ∪ F2 collapses; F1 stays alone (it sits to the right of F0).
    assert len(out) == 2


def test_merge_close_same_line_collapses() -> None:
    a = Finding(
        rule_id="CO-001",
        category="CONTACT",
        bbox=BBox(x=0, y=0, w=20, h=20),
        confidence="high",
        matched_text="",
    )
    b = Finding(
        rule_id="CO-001",
        category="CONTACT",
        bbox=BBox(x=23, y=0, w=20, h=20),  # 3 px gap, same line
        confidence="high",
        matched_text="",
    )
    out = merge_findings([a, b])
    assert len(out) == 1
