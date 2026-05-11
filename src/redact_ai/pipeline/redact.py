"""Redactor (BUILD_SPEC §10, FR-4.x).

Draws the safe overlay on the **input** image (after projecting bboxes
through the inverse preprocessing transform). The output preserves the
input format and dimensions (FR-4.4), and zero original sensitive
pixels survive in any masked region (FR-4.5).
"""

from __future__ import annotations

import io
from dataclasses import dataclass

from PIL import Image, ImageDraw, ImageFont

from redact_ai.errors import redaction_error
from redact_ai.models.document import BBox
from redact_ai.models.findings import Finding
from redact_ai.pipeline.ingest import IngestedImage
from redact_ai.policy.schema import (
    BlockStyle,
    LabelStyle,
    PixelateStyle,
    RedactionStyle,
)

_CATEGORY_LABELS: dict[str, str] = {
    "IDENTITY": "IDENTITY",
    "CONTACT": "CONTACT",
    "FINANCIAL": "FINANCIAL",
    "HEALTH": "HEALTH",
    "CREDENTIALS": "CREDS",
    "LOCATION": "LOCATION",
    "CUSTOM": "CUSTOM",
}


@dataclass(slots=True)
class RedactedImage:
    bytes: bytes
    mime_type: str
    width: int
    height: int
    projected_findings: tuple[Finding, ...]


def render_redacted(
    ingested: IngestedImage,
    findings: list[Finding],
    style: RedactionStyle,
) -> RedactedImage:
    """Apply the redaction style to ``ingested.original`` and serialise."""
    if style.kind == "blur":
        # Per BUILD_SPEC §10.5 the pipeline downgrades blur to block
        # *before* reaching this function; finding it here is a bug.
        raise redaction_error("blur style must be downgraded before rendering")

    image = ingested.original.copy()
    if image.mode == "RGBA":
        image = image.convert("RGB")
    width, height = image.size
    inverse = ingested.transform.inverse()
    projected: list[Finding] = []
    for f in findings:
        projected_bbox = inverse.project_bbox(f.bbox)
        projected_bbox = _clip(projected_bbox, width, height)
        projected.append(f.model_copy(update={"bbox": projected_bbox}))

    draw = ImageDraw.Draw(image)
    for finding in projected:
        bbox = finding.bbox
        if isinstance(style, BlockStyle):
            _draw_block(draw, bbox, width, height, style.color, style.padding_px)
        elif isinstance(style, PixelateStyle):
            _draw_pixelate(image, bbox, width, height, style.padding_px)
        elif isinstance(style, LabelStyle):
            _draw_block(draw, bbox, width, height, style.color, style.padding_px)
            _draw_label(draw, bbox, finding.category, style)
        else:  # pragma: no cover — schema discriminator prevents this.
            raise redaction_error(f"unsupported style kind: {style.kind}")

    buf = io.BytesIO()
    save_format = ingested.pil_format
    save_kwargs: dict[str, object] = {}
    if save_format == "JPEG":
        save_kwargs["quality"] = 92
        save_kwargs["optimize"] = True
    elif save_format == "PNG":
        save_kwargs["optimize"] = True
    elif save_format == "WEBP":
        save_kwargs["quality"] = 92
    image.save(buf, format=save_format, **save_kwargs)
    data = buf.getvalue()
    return RedactedImage(
        bytes=data,
        mime_type=ingested.mime_type,
        width=width,
        height=height,
        projected_findings=tuple(projected),
    )


def _clip(bbox: BBox, max_w: int, max_h: int) -> BBox:
    x = min(max(bbox.x, 0), max_w - 1)
    y = min(max(bbox.y, 0), max_h - 1)
    x2 = min(max(bbox.x2, x + 1), max_w)
    y2 = min(max(bbox.y2, y + 1), max_h)
    return BBox(x=x, y=y, w=x2 - x, h=y2 - y)


def _draw_block(
    draw: ImageDraw.ImageDraw,
    bbox: BBox,
    max_w: int,
    max_h: int,
    color_hex: str,
    padding: int,
) -> None:
    padded = bbox.expanded(padding, max_w, max_h)
    rgb = _hex_to_rgb(color_hex)
    draw.rectangle(
        (padded.x, padded.y, padded.x2 - 1, padded.y2 - 1),
        fill=rgb,
        outline=rgb,
    )


def _draw_pixelate(
    image: Image.Image,
    bbox: BBox,
    max_w: int,
    max_h: int,
    padding: int,
) -> None:
    padded = bbox.expanded(padding, max_w, max_h)
    if padded.w <= 0 or padded.h <= 0:
        return
    region = image.crop((padded.x, padded.y, padded.x2, padded.y2))
    pixels = region.getdata()
    n = len(pixels)
    if n == 0:
        return
    if region.mode != "RGB":
        region = region.convert("RGB")
        pixels = region.getdata()
        n = len(pixels)
    r = sum(p[0] for p in pixels) // n
    g = sum(p[1] for p in pixels) // n
    b = sum(p[2] for p in pixels) // n
    fill = Image.new("RGB", (padded.w, padded.h), (r, g, b))
    image.paste(fill, (padded.x, padded.y))


def _draw_label(
    draw: ImageDraw.ImageDraw,
    bbox: BBox,
    category: str,
    style: LabelStyle,
) -> None:
    label = f"[{_CATEGORY_LABELS.get(category, category)}]"
    font = _label_font(bbox)
    bbox_inner = bbox
    try:
        tx0, ty0, tx1, ty1 = draw.textbbox((0, 0), label, font=font)
    except AttributeError:  # pragma: no cover — Pillow ≥10 always has textbbox.
        text_w, text_h = draw.textsize(label, font=font)
        tx0 = ty0 = 0
        tx1, ty1 = text_w, text_h
    text_w = tx1 - tx0
    text_h = ty1 - ty0
    if text_w > bbox_inner.w - 4:
        initials = "".join(c for c in category if c.isalpha())[:3]
        label = f"[{initials}]"
        try:
            tx0, ty0, tx1, ty1 = draw.textbbox((0, 0), label, font=font)
        except AttributeError:  # pragma: no cover
            text_w, text_h = draw.textsize(label, font=font)
            tx0 = ty0 = 0
            tx1, ty1 = text_w, text_h
        text_w = tx1 - tx0
        text_h = ty1 - ty0
    cx = bbox_inner.x + bbox_inner.w // 2 - text_w // 2 - tx0
    cy = bbox_inner.y + bbox_inner.h // 2 - text_h // 2 - ty0
    draw.text((cx, cy), label, fill=_hex_to_rgb(style.text_color), font=font)


def _label_font(bbox: BBox) -> ImageFont.ImageFont:
    size = min(max(int(bbox.h * 0.6), 10), 24)
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", size=size)
    except OSError:  # pragma: no cover — DejaVu is shipped with Pillow.
        return ImageFont.load_default()


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    v = value.lstrip("#")
    return (int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16))
