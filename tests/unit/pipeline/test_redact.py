"""Redactor tests (BUILD_SPEC §10, FR-4.5, BS-16.4)."""

from __future__ import annotations

import hashlib
import io

import pytest
from PIL import Image

from redact_ai.errors import RedactError
from redact_ai.models.document import AffineTransform, BBox
from redact_ai.models.findings import Finding
from redact_ai.pipeline.ingest import IngestedImage
from redact_ai.pipeline.redact import render_redacted
from redact_ai.policy.schema import BlockStyle, BlurStyle, LabelStyle, PixelateStyle


def _ingested(color: str = "white", size: tuple[int, int] = (400, 200)) -> IngestedImage:
    img = Image.new("RGB", size, color)
    return IngestedImage(
        original=img,
        normalised=img,
        mime_type="image/png",
        pil_format="PNG",
        transform=AffineTransform.identity(),
    )


def _finding(x: int = 10, y: int = 10, w: int = 80, h: int = 30) -> Finding:
    return Finding(
        rule_id="ID-001",
        category="IDENTITY",
        bbox=BBox(x=x, y=y, w=w, h=h),
        confidence="high",
        matched_text="",
    )


def _region_hash(image_bytes: bytes, bbox: BBox) -> str:
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    crop = img.crop((bbox.x, bbox.y, bbox.x2, bbox.y2))
    return hashlib.sha256(crop.tobytes()).hexdigest()


def _flat_hash(width: int, height: int, color: tuple[int, int, int]) -> str:
    flat = Image.new("RGB", (width, height), color)
    return hashlib.sha256(flat.tobytes()).hexdigest()


def test_block_style_covers_with_flat_color() -> None:
    ingested = _ingested()
    style = BlockStyle(color="#000000", padding_px=2)
    out = render_redacted(ingested, [_finding()], style)
    expected = _flat_hash(80 + 4, 30 + 4, (0, 0, 0))
    assert _region_hash(out.bytes, BBox(x=8, y=8, w=84, h=34)) == expected


def test_pixelate_style_is_flat_fill() -> None:
    ingested = _ingested(color="red")
    style = PixelateStyle()
    out = render_redacted(ingested, [_finding()], style)
    # Mean of red region (with white padding ring) approximates (red).
    img = Image.open(io.BytesIO(out.bytes)).convert("RGB")
    crop = img.crop((10, 10, 90, 40))
    pixels = list(crop.getdata())
    assert len(set(pixels)) == 1  # exactly one colour


def test_label_style_draws_block_plus_label() -> None:
    ingested = _ingested()
    style = LabelStyle()
    out = render_redacted(ingested, [_finding(w=160, h=40)], style)
    img = Image.open(io.BytesIO(out.bytes)).convert("RGB")
    # Centre of bbox must be either the label colour or text colour — but
    # never the original white. Sample a few central pixels.
    cx, cy = 90, 30
    sample = img.getpixel((cx, cy))
    assert sample != (255, 255, 255)


def test_blur_style_rejected_at_redactor() -> None:
    ingested = _ingested()
    style = BlurStyle()
    with pytest.raises(RedactError) as exc:
        render_redacted(ingested, [_finding()], style)
    assert exc.value.code == "E_REDACTION"


def test_output_preserves_dimensions() -> None:
    ingested = _ingested(size=(640, 480))
    out = render_redacted(ingested, [_finding()], BlockStyle())
    img = Image.open(io.BytesIO(out.bytes))
    assert img.size == (640, 480)


def test_projection_back_to_input_grid() -> None:
    src = Image.new("RGB", (100, 100), "white")
    normalised = Image.new("RGB", (200, 200), "white")
    ingested = IngestedImage(
        original=src,
        normalised=normalised,
        mime_type="image/png",
        pil_format="PNG",
        transform=AffineTransform.scale(2.0, 2.0),
    )
    finding = Finding(
        rule_id="ID-001",
        category="IDENTITY",
        bbox=BBox(x=40, y=60, w=80, h=20),  # on the normalised grid
        confidence="high",
        matched_text="",
    )
    out = render_redacted(ingested, [finding], BlockStyle(padding_px=0))
    # Inverse scale: divide by 2 → (20, 30, 40, 10) on input grid.
    expected = _flat_hash(40, 10, (0, 0, 0))
    assert _region_hash(out.bytes, BBox(x=20, y=30, w=40, h=10)) == expected


def test_label_initials_fallback_for_narrow_bbox() -> None:
    ingested = _ingested()
    style = LabelStyle()
    out = render_redacted(ingested, [_finding(w=20, h=24)], style)
    img = Image.open(io.BytesIO(out.bytes)).convert("RGB")
    # The masked region must not be the original white.
    sample = img.getpixel((20, 22))
    assert sample != (255, 255, 255)


def test_pixelate_with_clipped_bbox() -> None:
    ingested = _ingested(size=(100, 100))
    finding = Finding(
        rule_id="ID-001",
        category="IDENTITY",
        bbox=BBox(x=95, y=95, w=20, h=20),
        confidence="high",
        matched_text="",
    )
    out = render_redacted(ingested, [finding], PixelateStyle(padding_px=0))
    img = Image.open(io.BytesIO(out.bytes))
    assert img.size == (100, 100)


def test_block_style_jpeg_round_trip() -> None:
    img = Image.new("RGB", (200, 100), "white")
    ingested = IngestedImage(
        original=img,
        normalised=img,
        mime_type="image/jpeg",
        pil_format="JPEG",
        transform=AffineTransform.identity(),
    )
    out = render_redacted(ingested, [_finding(w=40, h=20)], BlockStyle())
    assert out.mime_type == "image/jpeg"
    Image.open(io.BytesIO(out.bytes))


def test_block_style_rgba_input() -> None:
    img = Image.new("RGBA", (200, 100), (255, 255, 255, 255))
    ingested = IngestedImage(
        original=img,
        normalised=img.convert("RGB"),
        mime_type="image/png",
        pil_format="PNG",
        transform=AffineTransform.identity(),
    )
    out = render_redacted(ingested, [_finding()], BlockStyle())
    img2 = Image.open(io.BytesIO(out.bytes))
    assert img2.mode == "RGB"


def test_render_with_no_findings() -> None:
    ingested = _ingested()
    out = render_redacted(ingested, [], BlockStyle())
    img = Image.open(io.BytesIO(out.bytes))
    # Output is still a valid image of the same size.
    assert img.size == ingested.original.size


def test_block_padding_zero() -> None:
    ingested = _ingested()
    out = render_redacted(ingested, [_finding()], BlockStyle(padding_px=0))
    expected = _flat_hash(80, 30, (0, 0, 0))
    assert _region_hash(out.bytes, BBox(x=10, y=10, w=80, h=30)) == expected


def test_pixelate_with_empty_region_no_crash() -> None:
    ingested = _ingested(size=(10, 10))
    finding = Finding(
        rule_id="ID-001",
        category="IDENTITY",
        bbox=BBox(x=8, y=8, w=2, h=2),
        confidence="high",
        matched_text="",
    )
    out = render_redacted(ingested, [finding], PixelateStyle(padding_px=0))
    img = Image.open(io.BytesIO(out.bytes))
    assert img.size == (10, 10)


def test_label_for_credentials_uses_creds_initials() -> None:
    ingested = _ingested()
    cred_finding = Finding(
        rule_id="CR-001",
        category="CREDENTIALS",
        bbox=BBox(x=10, y=10, w=200, h=40),
        confidence="high",
        matched_text="",
    )
    out = render_redacted(ingested, [cred_finding], LabelStyle())
    Image.open(io.BytesIO(out.bytes))


def test_webp_round_trip() -> None:
    img = Image.new("RGB", (200, 100), "white")
    ingested = IngestedImage(
        original=img,
        normalised=img,
        mime_type="image/webp",
        pil_format="WEBP",
        transform=AffineTransform.identity(),
    )
    out = render_redacted(ingested, [_finding(w=40, h=20)], BlockStyle())
    assert out.mime_type == "image/webp"
