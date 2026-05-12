"""TesseractAdapter low-confidence re-OCR pass.

Tesseract's whole-page layout analysis sometimes merges a typed row
with adjacent noise (a cursive signature, a chart legend) and emits
gibberish tokens with very low confidence. The adapter re-OCRs each
sub-threshold token on its own cropped bbox using ``--psm 7`` (single
text line) and swaps in the recovered tokens when their average
confidence clears the replacement floor.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from PIL import Image

from redact_ai.pipeline.ingest import ingest_bytes
from redact_ai.pipeline.ocr.tesseract import TesseractAdapter


def _png_bytes(size: tuple[int, int] = (300, 100)) -> bytes:
    import io

    img = Image.new("RGB", size, "white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _td(
    rows: list[tuple[str, int, int, int, int, int, int, int, int, int]],
) -> dict[str, list[Any]]:
    """Build a ``pytesseract.image_to_data`` DICT result from rows.

    Row tuple: ``(text, conf_0_100, left, top, width, height,
    block_num, par_num, line_num, word_num)``.
    """
    keys = (
        "text",
        "conf",
        "left",
        "top",
        "width",
        "height",
        "block_num",
        "par_num",
        "line_num",
        "word_num",
    )
    out: dict[str, list[Any]] = {k: [] for k in keys}
    for row in rows:
        for k, v in zip(keys, row, strict=True):
            out[k].append(v)
    return out


def test_low_confidence_token_replaced_by_better_reocr() -> None:
    """A ``hl`` (conf 0.15) gets re-OCR'd into ``Laura Bennett,`` when
    the per-token pass returns high-confidence tokens."""
    first_pass = _td(
        [
            ("Reported", 96, 50, 100, 80, 14, 1, 1, 1, 1),
            ("by:", 96, 140, 100, 30, 14, 1, 1, 1, 2),
            ("hl", 15, 180, 100, 100, 14, 1, 1, 1, 3),
            ("MD", 95, 290, 100, 25, 14, 1, 1, 1, 4),
        ]
    )
    reocr_pass = _td(
        [
            ("Laura", 96, 4, 4, 50, 12, 1, 1, 1, 1),
            ("Bennett,", 96, 56, 4, 50, 12, 1, 1, 1, 2),
        ]
    )
    ingested = ingest_bytes(_png_bytes(), "image/png")

    def _fake_image_to_data(image: Image.Image, **kwargs: Any) -> dict[str, list[Any]]:
        config = kwargs.get("config", "")
        return reocr_pass if "--psm 7" in config else first_pass

    with patch(
        "redact_ai.pipeline.ocr.tesseract.pytesseract.image_to_data",
        side_effect=_fake_image_to_data,
    ):
        with patch(
            "redact_ai.pipeline.ocr.tesseract.shutil.which", return_value="/usr/bin/tesseract"
        ):
            doc = TesseractAdapter().recognise(ingested)

    tokens = list(doc.iter_tokens())
    texts = [t.text for t in tokens]
    assert "Laura" in texts
    assert "Bennett," in texts
    assert "hl" not in texts
    # Original high-confidence tokens are preserved.
    assert "Reported" in texts
    assert "MD" in texts
    # Replacement tokens carry the audit-trail ID suffix `-r{i}` so a
    # reviewer can tell at a glance which tokens came from the
    # per-token re-OCR pass versus the original whole-page pass.
    replacements = [t for t in tokens if t.text in {"Laura", "Bennett,"}]
    assert all("-r" in t.id for t in replacements)


def test_low_confidence_token_kept_when_reocr_is_no_better() -> None:
    """An OCR artefact over a chart (e.g. ``SS``) stays as the original
    low-confidence token when the per-token pass also fails."""
    first_pass = _td(
        [
            ("SS", 10, 50, 100, 60, 14, 1, 1, 1, 1),
        ]
    )
    reocr_pass = _td(
        [
            ("eae", 0, 4, 4, 30, 12, 1, 1, 1, 1),
            ("ote", 31, 36, 4, 30, 12, 1, 1, 1, 2),
        ]
    )
    ingested = ingest_bytes(_png_bytes(), "image/png")

    def _fake_image_to_data(image: Image.Image, **kwargs: Any) -> dict[str, list[Any]]:
        config = kwargs.get("config", "")
        return reocr_pass if "--psm 7" in config else first_pass

    with patch(
        "redact_ai.pipeline.ocr.tesseract.pytesseract.image_to_data",
        side_effect=_fake_image_to_data,
    ):
        with patch(
            "redact_ai.pipeline.ocr.tesseract.shutil.which", return_value="/usr/bin/tesseract"
        ):
            doc = TesseractAdapter().recognise(ingested)

    texts = [t.text for t in doc.iter_tokens()]
    # Original artefact is kept; re-OCR'd noise is not swapped in.
    assert texts == ["SS"]


def test_high_confidence_token_skips_reocr() -> None:
    """A clean token never invokes the per-token re-OCR pass."""
    first_pass = _td(
        [
            ("Hello", 95, 10, 20, 60, 14, 1, 1, 1, 1),
            ("World", 96, 80, 20, 60, 14, 1, 1, 1, 2),
        ]
    )
    ingested = ingest_bytes(_png_bytes(), "image/png")
    calls: list[str] = []

    def _fake_image_to_data(image: Image.Image, **kwargs: Any) -> dict[str, list[Any]]:
        calls.append(kwargs.get("config", ""))
        return first_pass

    with patch(
        "redact_ai.pipeline.ocr.tesseract.pytesseract.image_to_data",
        side_effect=_fake_image_to_data,
    ):
        with patch(
            "redact_ai.pipeline.ocr.tesseract.shutil.which", return_value="/usr/bin/tesseract"
        ):
            TesseractAdapter().recognise(ingested)

    # Only the first-pass call; no per-token re-OCR for high-confidence tokens.
    assert calls == ["--psm 6"]


def test_threshold_and_floor_are_inclusive_at_the_boundary() -> None:
    """Locks the boundary semantics:

    - A token whose first-pass confidence equals ``_REOCR_TOKEN_THRESHOLD``
      (0.40) *does* trigger re-OCR (the gate is ``> threshold``).
    - A re-OCR'd token whose confidence equals ``_REOCR_REPLACEMENT_FLOOR``
      (0.75) *is* accepted as a replacement (the gate is ``< floor``).
    """
    first_pass = _td(
        [
            ("edge", 40, 10, 20, 40, 12, 1, 1, 1, 1),
        ]
    )
    reocr_pass = _td(
        [
            ("Edge", 75, 1, 1, 35, 10, 1, 1, 1, 1),
        ]
    )
    ingested = ingest_bytes(_png_bytes(), "image/png")

    def _fake_image_to_data(image: Image.Image, **kwargs: Any) -> dict[str, list[Any]]:
        config = kwargs.get("config", "")
        return reocr_pass if "--psm 7" in config else first_pass

    with patch(
        "redact_ai.pipeline.ocr.tesseract.pytesseract.image_to_data",
        side_effect=_fake_image_to_data,
    ):
        with patch(
            "redact_ai.pipeline.ocr.tesseract.shutil.which", return_value="/usr/bin/tesseract"
        ):
            doc = TesseractAdapter().recognise(ingested)

    assert [t.text for t in doc.iter_tokens()] == ["Edge"]


def test_reocr_error_falls_back_to_original_token() -> None:
    """If the per-token pass raises ``TesseractError``, the original
    token is preserved (no swallowed crash)."""
    import pytesseract

    first_pass = _td(
        [
            ("garbage", 5, 50, 100, 60, 14, 1, 1, 1, 1),
        ]
    )
    ingested = ingest_bytes(_png_bytes(), "image/png")

    def _fake_image_to_data(image: Image.Image, **kwargs: Any) -> dict[str, list[Any]]:
        config = kwargs.get("config", "")
        if "--psm 7" in config:
            raise pytesseract.TesseractError(1, "synthetic failure")
        return first_pass

    with patch(
        "redact_ai.pipeline.ocr.tesseract.pytesseract.image_to_data",
        side_effect=_fake_image_to_data,
    ):
        with patch(
            "redact_ai.pipeline.ocr.tesseract.shutil.which", return_value="/usr/bin/tesseract"
        ):
            doc = TesseractAdapter().recognise(ingested)

    texts = [t.text for t in doc.iter_tokens()]
    assert texts == ["garbage"]


def test_per_page_reocr_budget_caps_calls() -> None:
    """On a noisy scan with many sub-threshold tokens, re-OCR stops
    after ``_REOCR_MAX_PER_PAGE`` attempts so OCR latency stays
    bounded. Remaining low-confidence tokens are kept as-is."""
    from redact_ai.pipeline.ocr import tesseract as adapter_module

    # 100 tokens, all at conf 0.10 — every one is a re-OCR candidate.
    first_pass_rows = [
        (f"bad{i:03d}", 10, 10 + i * 20, 100, 15, 12, 1, 1, 1, i + 1) for i in range(100)
    ]
    first_pass = _td(first_pass_rows)
    # Re-OCR returns one good replacement per call.
    reocr_pass = _td([("ok", 95, 1, 1, 12, 10, 1, 1, 1, 1)])
    ingested = ingest_bytes(_png_bytes(size=(3000, 200)), "image/png")
    psm7_calls = 0

    def _fake_image_to_data(image: Image.Image, **kwargs: Any) -> dict[str, list[Any]]:
        nonlocal psm7_calls
        config = kwargs.get("config", "")
        if "--psm 7" in config:
            psm7_calls += 1
            return reocr_pass
        return first_pass

    with patch(
        "redact_ai.pipeline.ocr.tesseract.pytesseract.image_to_data",
        side_effect=_fake_image_to_data,
    ):
        with patch(
            "redact_ai.pipeline.ocr.tesseract.shutil.which", return_value="/usr/bin/tesseract"
        ):
            doc = TesseractAdapter().recognise(ingested)

    assert psm7_calls == adapter_module._REOCR_MAX_PER_PAGE
    texts = [t.text for t in doc.iter_tokens()]
    # First _REOCR_MAX_PER_PAGE tokens were refined; the rest stayed as
    # the original low-confidence text.
    refined_count = sum(1 for t in texts if t == "ok")
    kept_count = sum(1 for t in texts if t.startswith("bad"))
    assert refined_count == adapter_module._REOCR_MAX_PER_PAGE
    assert refined_count + kept_count == 100


def test_reocr_drops_tokens_outside_original_bbox() -> None:
    """When the padded crop catches an adjacent word, the new token
    sits entirely outside the original bbox and must be rejected so
    we don't duplicate text already recognised elsewhere on the
    line."""
    # Original sub-threshold token at x=100..120 (w=20), conf 0.10.
    # An adjacent typed word at x=150..200 already exists at full
    # confidence in the first pass — re-OCR'ing the 3px-padded crop
    # could pick it up and double-emit.
    first_pass = _td(
        [
            ("noise", 10, 100, 50, 20, 12, 1, 1, 1, 1),
            ("Alice", 95, 150, 50, 50, 12, 1, 1, 1, 2),
        ]
    )
    # Re-OCR returns two tokens: one *outside* the original bbox
    # (would be "Alice" picked up from the padding), one *inside*.
    # Crop origin is x=97 (100-3 padding), so token at left=53 in
    # crop coords lands at page x=150 — outside [100..120].
    # Token at left=2 lands at page x=99 — overlaps the original.
    reocr_pass = _td(
        [
            ("real", 95, 2, 1, 18, 10, 1, 1, 1, 1),
            ("Alice", 95, 53, 1, 50, 10, 1, 1, 1, 2),
        ]
    )
    ingested = ingest_bytes(_png_bytes(size=(400, 100)), "image/png")

    def _fake_image_to_data(image: Image.Image, **kwargs: Any) -> dict[str, list[Any]]:
        config = kwargs.get("config", "")
        return reocr_pass if "--psm 7" in config else first_pass

    with patch(
        "redact_ai.pipeline.ocr.tesseract.pytesseract.image_to_data",
        side_effect=_fake_image_to_data,
    ):
        with patch(
            "redact_ai.pipeline.ocr.tesseract.shutil.which", return_value="/usr/bin/tesseract"
        ):
            doc = TesseractAdapter().recognise(ingested)

    texts = [t.text for t in doc.iter_tokens()]
    # The replacement ``real`` swapped in for ``noise``; the spurious
    # ``Alice`` from the padding zone was rejected, leaving only the
    # original ``Alice`` already on the line.
    assert texts.count("Alice") == 1
    assert "real" in texts
    assert "noise" not in texts
