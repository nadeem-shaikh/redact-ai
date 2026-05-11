"""Image ingest tests (FR-1.x)."""

from __future__ import annotations

import io

import pytest
from PIL import Image

from redact_ai.errors import RedactError
from redact_ai.pipeline.ingest import ingest_bytes


def _png_bytes(size: tuple[int, int] = (100, 100), color: str = "white") -> bytes:
    img = Image.new("RGB", size, color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _jpeg_bytes() -> bytes:
    img = Image.new("RGB", (100, 100), "white")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_png_round_trip() -> None:
    data = _png_bytes()
    ingested = ingest_bytes(data, "image/png")
    assert ingested.pil_format == "PNG"
    assert ingested.original.size == (100, 100)
    # Small input upsamples for OCR but original stays the same size.
    assert ingested.normalised.size != (100, 100)


def test_unsupported_mime_rejected() -> None:
    with pytest.raises(RedactError) as exc:
        ingest_bytes(_png_bytes(), "image/bmp")
    assert exc.value.code == "E_INPUT_FORMAT"


def test_truncated_bytes_rejected() -> None:
    with pytest.raises(RedactError) as exc:
        ingest_bytes(b"\x89PNGtruncated", "image/png")
    assert exc.value.code == "E_INPUT_FORMAT"


def test_too_large_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    from redact_ai.pipeline import ingest as ingest_module

    class _SmallSettings:
        max_upload_bytes = 100

    monkeypatch.setattr(ingest_module, "get_settings", lambda: _SmallSettings())
    with pytest.raises(RedactError) as exc:
        ingest_bytes(b"x" * 200, "image/png")
    assert exc.value.code == "E_INPUT_TOO_LARGE"


def test_mime_mismatch_rejected() -> None:
    with pytest.raises(RedactError):
        ingest_bytes(_png_bytes(), "image/jpeg")


def test_large_input_keeps_size() -> None:
    data = _png_bytes(size=(2000, 1500))
    ingested = ingest_bytes(data, "image/png")
    assert ingested.original.size == (2000, 1500)
    assert ingested.normalised.size == (2000, 1500)


def test_jpeg_round_trip() -> None:
    ingested = ingest_bytes(_jpeg_bytes(), "image/jpeg")
    assert ingested.pil_format == "JPEG"
