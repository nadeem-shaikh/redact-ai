"""Pipeline-level safety guards (oversized bbox sanity check)."""

from __future__ import annotations

from redact_ai.models.document import (
    AffineTransform,
    BBox,
    Block,
    Document,
    Line,
    Page,
    Token,
)
from redact_ai.models.findings import Finding
from redact_ai.models.manifest import Warning
from redact_ai.pipeline import _guard_oversized


def _doc(width: int = 1000, height: int = 1000) -> Document:
    token = Token(
        id="t-0",
        text="x",
        bbox=BBox(x=0, y=0, w=10, h=10),
        confidence=0.95,
    )
    line = Line(id="l-0", bbox=token.bbox, tokens=(token,), reading_order=0)
    block = Block(id="b-0", bbox=line.bbox, lines=(line,), block_type="paragraph")
    page = Page(index=0, width=width, height=height, blocks=(block,))
    return Document(
        pages=(page,),
        source_hash="0" * 64,
        input_width=width,
        input_height=height,
        transform=AffineTransform.identity(),
    )


def _finding(w: int, h: int, *, rule: str = "ID-006", confidence: str = "high") -> Finding:
    return Finding(
        rule_id=rule,
        category="IDENTITY",
        bbox=BBox(x=0, y=0, w=w, h=h),
        confidence=confidence,  # type: ignore[arg-type]
        matched_text="secret",
        page_index=0,
    )


def test_normal_finding_unchanged() -> None:
    warnings: list[Warning] = []
    findings = [_finding(100, 50)]  # 5 000 / 1 000 000 = 0.5 % of page
    out = _guard_oversized(findings, _doc(), warnings)
    assert out == findings
    assert warnings == []


def test_oversized_finding_downgraded_and_warned() -> None:
    warnings: list[Warning] = []
    # 800 x 300 = 240 000 / 1 000 000 = 24 % of page → over the 20 % limit.
    findings = [_finding(800, 300, rule="ID-006", confidence="high")]
    out = _guard_oversized(findings, _doc(), warnings)
    assert len(out) == 1
    assert out[0].confidence == "low"
    assert out[0].bbox == findings[0].bbox  # geometry preserved
    assert len(warnings) == 1
    assert warnings[0].code == "W_OVERSIZED_REDACTION"
    assert "ID-006" in warnings[0].message


def test_multiple_oversized_findings_share_one_warning() -> None:
    warnings: list[Warning] = []
    findings = [
        _finding(800, 300, rule="ID-006"),
        _finding(900, 400, rule="ID-001"),
    ]
    out = _guard_oversized(findings, _doc(), warnings)
    assert all(f.confidence == "low" for f in out)
    assert len(warnings) == 1
    msg = warnings[0].message
    assert "ID-006" in msg and "ID-001" in msg


def test_empty_findings_no_warning() -> None:
    warnings: list[Warning] = []
    out = _guard_oversized([], _doc(), warnings)
    assert out == []
    assert warnings == []
