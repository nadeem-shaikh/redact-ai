"""Canonical document model (BUILD_SPEC §7.1).

All coordinates are integer pixels on the **post-preprocessing** image.
The preprocessing affine transform is recorded alongside the document so
the redactor can project bboxes back onto the input pixel grid (§7.3).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class BBox(BaseModel):
    """Axis-aligned bounding box in pixel coordinates."""

    model_config = {"frozen": True}

    x: int = Field(ge=0)
    y: int = Field(ge=0)
    w: int = Field(gt=0)
    h: int = Field(gt=0)

    @property
    def x2(self) -> int:
        return self.x + self.w

    @property
    def y2(self) -> int:
        return self.y + self.h

    @property
    def area(self) -> int:
        return self.w * self.h

    def iou(self, other: BBox) -> float:
        inter_x1 = max(self.x, other.x)
        inter_y1 = max(self.y, other.y)
        inter_x2 = min(self.x2, other.x2)
        inter_y2 = min(self.y2, other.y2)
        if inter_x2 <= inter_x1 or inter_y2 <= inter_y1:
            return 0.0
        inter = (inter_x2 - inter_x1) * (inter_y2 - inter_y1)
        union = self.area + other.area - inter
        return inter / union if union else 0.0

    def union(self, other: BBox) -> BBox:
        x = min(self.x, other.x)
        y = min(self.y, other.y)
        x2 = max(self.x2, other.x2)
        y2 = max(self.y2, other.y2)
        return BBox(x=x, y=y, w=x2 - x, h=y2 - y)

    def expanded(self, padding: int, max_w: int, max_h: int) -> BBox:
        """Grow the bbox by ``padding`` px on each side, clipped to bounds.

        If the bbox already sits flush against ``max_w``/``max_h`` the clip
        could produce ``w == 0``; clamp to a minimum of 1 px on each axis
        so the resulting ``BBox`` always satisfies ``w > 0`` and ``h > 0``.
        """
        x = max(self.x - padding, 0)
        y = max(self.y - padding, 0)
        x2 = min(self.x2 + padding, max_w)
        y2 = min(self.y2 + padding, max_h)
        return BBox(x=x, y=y, w=max(x2 - x, 1), h=max(y2 - y, 1))


class Token(BaseModel):
    """A single OCR-recognised text fragment."""

    model_config = {"frozen": True}

    id: str
    text: str
    bbox: BBox
    confidence: float = Field(ge=0.0, le=1.0)


class Line(BaseModel):
    model_config = {"frozen": True}

    id: str
    bbox: BBox
    tokens: tuple[Token, ...]
    reading_order: int = Field(ge=0)

    @property
    def text(self) -> str:
        return " ".join(t.text for t in self.tokens)


class Block(BaseModel):
    model_config = {"frozen": True}

    id: str
    bbox: BBox
    lines: tuple[Line, ...]
    block_type: Literal["paragraph", "table_cell", "form_field", "other"] = "paragraph"


class Page(BaseModel):
    model_config = {"frozen": True}

    index: int = Field(ge=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    blocks: tuple[Block, ...]


class AffineTransform(BaseModel):
    """2×3 affine mapping ``input → post-preprocessing`` pixel coords (BUILD_SPEC §7.3).

    Stored as the six entries of the matrix::

        [a, b, tx]
        [c, d, ty]

    For v0.1 we only ever use uniform scale + translation (no rotation),
    which makes the inverse a closed-form computation.
    """

    model_config = {"frozen": True}

    a: float
    b: float
    tx: float
    c: float
    d: float
    ty: float

    @classmethod
    def identity(cls) -> AffineTransform:
        return cls(a=1.0, b=0.0, tx=0.0, c=0.0, d=1.0, ty=0.0)

    @classmethod
    def scale(cls, sx: float, sy: float) -> AffineTransform:
        return cls(a=sx, b=0.0, tx=0.0, c=0.0, d=sy, ty=0.0)

    def apply(self, x: float, y: float) -> tuple[float, float]:
        return (self.a * x + self.b * y + self.tx, self.c * x + self.d * y + self.ty)

    def inverse(self) -> AffineTransform:
        det = self.a * self.d - self.b * self.c
        if det == 0:
            raise ValueError("Affine transform is not invertible")
        a = self.d / det
        b = -self.b / det
        c = -self.c / det
        d = self.a / det
        tx = -(a * self.tx + b * self.ty)
        ty = -(c * self.tx + d * self.ty)
        return AffineTransform(a=a, b=b, tx=tx, c=c, d=d, ty=ty)

    def project_bbox(self, bbox: BBox) -> BBox:
        """Map ``bbox`` through this transform and snap to integer pixels."""
        x1, y1 = self.apply(bbox.x, bbox.y)
        x2, y2 = self.apply(bbox.x2, bbox.y2)
        nx1 = int(round(min(x1, x2)))
        ny1 = int(round(min(y1, y2)))
        nx2 = int(round(max(x1, x2)))
        ny2 = int(round(max(y1, y2)))
        nx1 = max(nx1, 0)
        ny1 = max(ny1, 0)
        w = max(nx2 - nx1, 1)
        h = max(ny2 - ny1, 1)
        return BBox(x=nx1, y=ny1, w=w, h=h)


class Document(BaseModel):
    """Top-level OCR output passed to the detector engine."""

    model_config = {"frozen": True}

    pages: tuple[Page, ...]
    source_hash: str
    input_width: int = Field(gt=0)
    input_height: int = Field(gt=0)
    transform: AffineTransform = AffineTransform.identity()

    @field_validator("pages")
    @classmethod
    def _exactly_one_page(cls, value: tuple[Page, ...]) -> tuple[Page, ...]:
        # v0.1 invariant (BUILD_SPEC §7.1): single-page documents only.
        if len(value) != 1:
            raise ValueError("v0.1 supports exactly one page per document")
        return value

    def iter_tokens(self) -> list[Token]:
        return [
            tok
            for page in self.pages
            for block in page.blocks
            for line in block.lines
            for tok in line.tokens
        ]

    def iter_lines(self) -> list[Line]:
        return [line for page in self.pages for block in page.blocks for line in block.lines]

    def iter_blocks(self) -> list[Block]:
        return [block for page in self.pages for block in page.blocks]
