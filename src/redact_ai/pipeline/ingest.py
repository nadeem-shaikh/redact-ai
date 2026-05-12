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

# Register the HEIC/HEIF and AVIF Pillow plugins on import so
# ``Image.open`` recognises those byte streams. Both plugins call
# ``Image.register_open`` as a side effect of being imported.
import pillow_avif  # noqa: F401  -- imported for side effects
from PIL import Image, ImageOps, UnidentifiedImageError
from pillow_heif import register_heif_opener

from redact_ai.config import get_settings
from redact_ai.errors import (
    input_format_error,
    input_too_large_error,
)
from redact_ai.models.document import AffineTransform

register_heif_opener()


# MIME → (PIL formats accepted on input, output PIL format, output MIME).
#
# Some input formats (GIF, BMP, TIFF, HEIC/HEIF, AVIF) are either not
# universally rendered by browsers or are unsuitable for the redacted
# output (animated, multi-page, or no alpha). We re-encode those as the
# closest browser-friendly format so the preview/download always works:
#   - HEIC/HEIF → JPEG (similar lossy character)
#   - AVIF      → WebP
#   - GIF/BMP/TIFF → PNG (lossless, universal)
_FORMATS: dict[str, tuple[frozenset[str], str, str]] = {
    "image/png": (frozenset({"PNG"}), "PNG", "image/png"),
    "image/jpeg": (frozenset({"JPEG"}), "JPEG", "image/jpeg"),
    "image/jpg": (frozenset({"JPEG"}), "JPEG", "image/jpeg"),
    "image/webp": (frozenset({"WEBP"}), "WEBP", "image/webp"),
    "image/gif": (frozenset({"GIF"}), "PNG", "image/png"),
    "image/bmp": (frozenset({"BMP"}), "PNG", "image/png"),
    "image/x-bmp": (frozenset({"BMP"}), "PNG", "image/png"),
    "image/x-ms-bmp": (frozenset({"BMP"}), "PNG", "image/png"),
    "image/tiff": (frozenset({"TIFF"}), "PNG", "image/png"),
    "image/x-tiff": (frozenset({"TIFF"}), "PNG", "image/png"),
    "image/heic": (frozenset({"HEIF"}), "JPEG", "image/jpeg"),
    "image/heif": (frozenset({"HEIF"}), "JPEG", "image/jpeg"),
    "image/avif": (frozenset({"AVIF"}), "WEBP", "image/webp"),
}

SUPPORTED_INPUT_MIMES: frozenset[str] = frozenset(_FORMATS)

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
    """Output MIME type — the format the redacted image will be encoded
    as. Equals the input MIME for PNG/JPEG/WebP; for other inputs this
    is the closest browser-friendly format (PNG / JPEG / WebP)."""

    pil_format: str
    """Output PIL format string passed to ``Image.save(format=...)``."""

    transform: AffineTransform
    """Maps input pixel coordinates → ``normalised`` pixel coordinates."""


def ingest_bytes(data: bytes, mime_type: str) -> IngestedImage:
    settings = get_settings()
    if len(data) > settings.max_upload_bytes:
        raise input_too_large_error(len(data), settings.max_upload_bytes)
    if mime_type not in _FORMATS:
        raise input_format_error(mime_type)
    accepted_formats, out_pil_format, out_mime_type = _FORMATS[mime_type]

    try:
        with Image.open(io.BytesIO(data)) as probe:
            probe.load()
            detected_format = probe.format or ""
            original = probe.convert("RGBA" if probe.mode == "RGBA" else "RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise input_format_error(mime_type) from exc

    if detected_format.upper() not in accepted_formats:
        raise input_format_error(mime_type)

    original = ImageOps.exif_transpose(original)
    # ImageOps.exif_transpose strips EXIF as a side effect, but be
    # explicit so a downstream save() never re-emits it.
    original.info.pop("exif", None)
    original.info.pop("XML:com.adobe.xmp", None)

    # JPEG and AVIF→WebP output can't carry an alpha channel safely;
    # drop it now so the redactor's save() path doesn't surprise-fail.
    if original.mode == "RGBA" and out_pil_format == "JPEG":
        original = original.convert("RGB")

    normalised, transform = _normalise(original)
    return IngestedImage(
        original=original,
        normalised=normalised,
        mime_type=out_mime_type,
        pil_format=out_pil_format,
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
