"""Image ingestion (FR-1.x, BUILD_SPEC §13.1).

Responsibilities:

* validate the declared MIME type and the image header (FR-1.1, FR-1.2);
* strip EXIF from the working copy (FR-1.3);
* enforce the 25 MB size limit;
* return both the original image (used by the redactor so the output
  byte format matches the input) and the OCR-targeted normalised copy.
"""

from __future__ import annotations

import io
from dataclasses import dataclass

from PIL import Image, ImageOps, UnidentifiedImageError

from redact_ai.config import get_settings
from redact_ai.errors import (
    input_format_error,
    input_too_large_error,
)
from redact_ai.models.document import AffineTransform

_SUPPORTED: dict[str, str] = {
    "image/png": "PNG",
    "image/jpeg": "JPEG",
    "image/webp": "WEBP",
}

# Tesseract is happiest at ~300 DPI / ≈1500 px on the long side. We
# never *downscale* the input — we only upsample low-DPI screenshots —
# so the affine transform stays a uniform scale (BUILD_SPEC §7.3).
_OCR_TARGET_MIN_SIDE = 1500


@dataclass(slots=True)
class IngestedImage:
    """The product of the ingest stage."""

    original: Image.Image
    """The original image with EXIF stripped (mode preserved as RGB/RGBA)."""

    normalised: Image.Image
    """The post-preprocessing image fed to OCR. Always RGB."""

    mime_type: str
    pil_format: str
    transform: AffineTransform
    """Maps input pixel coordinates → ``normalised`` pixel coordinates."""


def ingest_bytes(data: bytes, mime_type: str) -> IngestedImage:
    settings = get_settings()
    if len(data) > settings.max_upload_bytes:
        raise input_too_large_error(len(data), settings.max_upload_bytes)
    if mime_type not in _SUPPORTED:
        raise input_format_error(mime_type)

    try:
        with Image.open(io.BytesIO(data)) as probe:
            probe.load()
            detected_format = probe.format or ""
            original = probe.convert("RGBA" if probe.mode == "RGBA" else "RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise input_format_error(mime_type) from exc

    if detected_format.upper() != _SUPPORTED[mime_type]:
        raise input_format_error(mime_type)

    original = ImageOps.exif_transpose(original)
    # ImageOps.exif_transpose strips EXIF as a side effect, but be
    # explicit so a downstream save() never re-emits it.
    original.info.pop("exif", None)
    original.info.pop("XML:com.adobe.xmp", None)

    normalised, transform = _normalise(original)
    return IngestedImage(
        original=original,
        normalised=normalised,
        mime_type=mime_type,
        pil_format=_SUPPORTED[mime_type],
        transform=transform,
    )


def _normalise(image: Image.Image) -> tuple[Image.Image, AffineTransform]:
    """Convert to RGB, upsample small inputs so OCR has enough signal."""
    rgb = image.convert("RGB") if image.mode != "RGB" else image
    w, h = rgb.size
    long_side = max(w, h)
    if long_side >= _OCR_TARGET_MIN_SIDE:
        return rgb, AffineTransform.identity()
    scale = _OCR_TARGET_MIN_SIDE / float(long_side)
    new_size = (max(int(round(w * scale)), 1), max(int(round(h * scale)), 1))
    resized = rgb.resize(new_size, Image.Resampling.LANCZOS)
    # Use the *actual* per-axis scale (it can drift by a fraction of a
    # pixel after rounding) so the inverse round-trips cleanly.
    sx = new_size[0] / float(w)
    sy = new_size[1] / float(h)
    return resized, AffineTransform.scale(sx, sy)
