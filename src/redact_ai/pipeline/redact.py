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
    # JPEG cannot store an alpha channel — drop it only for JPEG output.
    # PNG and WebP both support RGBA, so preserve transparency there
    # (CodeRabbit review #15: unconditional RGB conversion was lossy).
    if image.mode == "RGBA" and ingested.pil_format == "JPEG":
        image = image.convert("RGB")
    width, height = image.size
    inverse = ingested.transform.inverse()
    projected: list[Finding] = []
    for f in findings:
        projected_bbox = inverse.project_bbox(f.bbox)
        projected_bbox = _clip(projected_bbox, width, height)
        projected.append(f.model_copy(update={"bbox": projected_bbox}))

    draw = ImageDraw.Draw(image)
    rgba = image.mode == "RGBA"
    for finding in projected:
        bbox = finding.bbox
        if isinstance(style, BlockStyle):
            _draw_block(draw, bbox, width, height, style.color, style.padding_px, rgba=rgba)
        elif isinstance(style, PixelateStyle):
            _draw_pixelate(image, bbox, width, height, style.padding_px)
        elif isinstance(style, LabelStyle):
            _draw_block(draw, bbox, width, height, style.color, style.padding_px, rgba=rgba)
            _draw_label(draw, bbox, finding.category, style)
        else:  # pragma: no cover — schema discriminator prevents this.
            raise redaction_error(f"unsupported style kind: {style.kind}")

    buf = io.BytesIO()
    save_format = ingested.pil_format
    save_kwargs: dict[str, object] = _save_kwargs(save_format)
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
    *,
    rgba: bool = False,
) -> None:
    padded = bbox.expanded(padding, max_w, max_h)
    fill = (*_hex_to_rgb(color_hex), 255) if rgba else _hex_to_rgb(color_hex)
    draw.rectangle(
        (padded.x, padded.y, padded.x2 - 1, padded.y2 - 1),
        fill=fill,
        outline=fill,
    )


def _draw_pixelate(
    image: Image.Image,
    bbox: BBox,
    max_w: int,
    max_h: int,
    padding: int,
) -> None:
    padded = bbox.expanded(padding, max_w, max_h)
    region = image.crop((padded.x, padded.y, padded.x2, padded.y2))
    pixels = list(region.getdata())
    n = len(pixels)
    r = sum(p[0] for p in pixels) // n
    g = sum(p[1] for p in pixels) // n
    b = sum(p[2] for p in pixels) // n
    # Match the image's mode so RGBA inputs stay RGBA (the alpha channel
    # of the redacted region is forced to fully opaque so the mask is
    # never see-through).
    if image.mode == "RGBA":
        fill = Image.new("RGBA", (padded.w, padded.h), (r, g, b, 255))
    else:
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
    tx0, ty0, tx1, ty1 = draw.textbbox((0, 0), label, font=font)
    text_w = tx1 - tx0
    text_h = ty1 - ty0
    if text_w > bbox.w - 4:
        initials = "".join(c for c in category if c.isalpha())[:3]
        label = f"[{initials}]"
        tx0, ty0, tx1, ty1 = draw.textbbox((0, 0), label, font=font)
        text_w = tx1 - tx0
        text_h = ty1 - ty0
    cx = bbox.x + bbox.w // 2 - text_w // 2 - tx0
    cy = bbox.y + bbox.h // 2 - text_h // 2 - ty0
    draw.text((cx, cy), label, fill=_hex_to_rgb(style.text_color), font=font)


def _label_font(bbox: BBox):  # type: ignore[no-untyped-def]
    """Return the vendored DejaVuSans-Bold sized to the bbox height
    (BUILD_SPEC §10.4). We bundle the font so the label style renders
    identically across macOS / Linux / Windows."""
    import io as _io
    from importlib.resources import files

    size = min(max(int(bbox.h * 0.6), 10), 24)
    try:
        font_bytes = files("redact_ai.resources").joinpath("DejaVuSans-Bold.ttf").read_bytes()
        return ImageFont.truetype(_io.BytesIO(font_bytes), size=size)
    except (OSError, FileNotFoundError):  # pragma: no cover — bundled file.
        return ImageFont.load_default()


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    v = value.lstrip("#")
    return (int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16))


_SAVE_KWARGS: dict[str, dict[str, object]] = {
    "PNG": {"optimize": True},
    "JPEG": {"quality": 92, "optimize": True},
    "WEBP": {"quality": 92},
}


def _save_kwargs(pil_format: str) -> dict[str, object]:
    return dict(_SAVE_KWARGS[pil_format])
