"""Document model + affine transform tests (BUILD_SPEC §7)."""

from __future__ import annotations

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from redact_ai.models.document import AffineTransform, BBox, Block, Document, Line, Page, Token


def _bbox(x: int = 0, y: int = 0, w: int = 10, h: int = 10) -> BBox:
    return BBox(x=x, y=y, w=w, h=h)


def test_bbox_iou_overlap() -> None:
    a = _bbox(0, 0, 10, 10)
    b = _bbox(5, 5, 10, 10)
    assert 0.0 < a.iou(b) < 1.0


def test_bbox_iou_disjoint() -> None:
    assert _bbox(0, 0, 5, 5).iou(_bbox(100, 100, 5, 5)) == 0.0


def test_bbox_union() -> None:
    a = _bbox(0, 0, 10, 10)
    b = _bbox(5, 5, 10, 10)
    u = a.union(b)
    assert (u.x, u.y, u.w, u.h) == (0, 0, 15, 15)


def test_bbox_expanded_clips() -> None:
    a = _bbox(0, 0, 10, 10)
    out = a.expanded(padding=20, max_w=15, max_h=12)
    assert (out.x, out.y, out.x2, out.y2) == (0, 0, 15, 12)


@settings(suppress_health_check=[HealthCheck.too_slow])
@given(
    st.floats(min_value=0.5, max_value=4.0),
    st.floats(min_value=0.5, max_value=4.0),
    st.integers(min_value=0, max_value=500),
    st.integers(min_value=0, max_value=500),
    st.integers(min_value=4, max_value=500),
    st.integers(min_value=4, max_value=500),
)
def test_affine_round_trip(sx: float, sy: float, x: int, y: int, w: int, h: int) -> None:
    """Scaling and inverse-scaling a bbox returns the same bbox within one
    pixel per side, provided the bbox is at least 4 px on each side so a
    single rounding step can't swallow it."""
    bbox = BBox(x=x, y=y, w=w, h=h)
    t = AffineTransform.scale(sx, sy)
    projected = t.project_bbox(bbox)
    back = t.inverse().project_bbox(projected)
    assert abs(back.x - bbox.x) <= 1
    assert abs(back.y - bbox.y) <= 1
    assert abs(back.x2 - bbox.x2) <= 1
    assert abs(back.y2 - bbox.y2) <= 1


def test_document_requires_one_page() -> None:
    page = Page(index=0, width=10, height=10, blocks=())
    Document(pages=(page,), source_hash="x" * 64, input_width=10, input_height=10)
    with pytest.raises(ValueError):
        Document(pages=(), source_hash="x" * 64, input_width=10, input_height=10)


def test_line_text() -> None:
    tokens = (
        Token(id="t1", text="Hello", bbox=_bbox(0, 0, 30, 10), confidence=0.9),
        Token(id="t2", text="World", bbox=_bbox(35, 0, 30, 10), confidence=0.9),
    )
    line = Line(id="l", bbox=_bbox(0, 0, 65, 10), tokens=tokens, reading_order=0)
    assert line.text == "Hello World"


def test_block_construction() -> None:
    tokens = (Token(id="t", text="x", bbox=_bbox(0, 0, 5, 5), confidence=1.0),)
    line = Line(id="l", bbox=_bbox(0, 0, 5, 5), tokens=tokens, reading_order=0)
    Block(id="b", bbox=_bbox(0, 0, 5, 5), lines=(line,), block_type="paragraph")


def test_affine_inverse_zero_det() -> None:
    bad = AffineTransform(a=0.0, b=0.0, tx=0.0, c=0.0, d=0.0, ty=0.0)
    with pytest.raises(ValueError):
        bad.inverse()
