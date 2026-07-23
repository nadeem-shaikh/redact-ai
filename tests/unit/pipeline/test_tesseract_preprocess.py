"""Tests for the two-pass OCR text-region contrast boost (_boost_text_regions).

These exercise the preprocessing helper directly with a synthetic first-pass
word-box dict, so they need neither the tesseract binary nor a real OCR run.
The invariant that matters most is R3: pixels outside any text box are never
altered, so colour/medical imagery (OCT scans, fundus photos) is preserved.
"""

from __future__ import annotations

import numpy as np
from PIL import Image

from redact_ai.pipeline.ocr.tesseract import _boost_text_regions


def _first_pass(words: list[tuple[str, int, int, int, int, int]]) -> dict[str, list]:
    """Build an image_to_data-shaped dict from (text, conf, x, y, w, h) tuples."""
    keys = ("text", "conf", "left", "top", "width", "height")
    cols: dict[str, list] = {k: [] for k in keys}
    for text, conf, x, y, w, h in words:
        cols["text"].append(text)
        cols["conf"].append(conf)
        cols["left"].append(x)
        cols["top"].append(y)
        cols["width"].append(w)
        cols["height"].append(h)
    return cols


def _mixed_image() -> Image.Image:
    """A small canvas: dark text-ish block top-left, colour photo block bottom."""
    arr = np.full((80, 120, 3), 240, dtype=np.uint8)
    # a low-contrast grey "text" smear in the top-left region
    arr[8:24, 8:60] = 150
    # a saturated colour block bottom-right (stands in for a fundus/OCT region)
    rng = np.random.RandomState(0)
    arr[48:72, 70:110] = rng.randint(0, 255, size=(24, 40, 3), dtype=np.uint8)
    return Image.fromarray(arr, mode="RGB")


def test_no_text_returns_input_unchanged() -> None:
    img = _mixed_image()
    out = _boost_text_regions(img, _first_pass([]))
    assert np.array_equal(np.asarray(img), np.asarray(out))


def test_color_region_outside_text_boxes_is_byte_identical() -> None:
    img = _mixed_image()
    # Word box covers only the top-left text smear, never the colour block.
    first = _first_pass([("Name", 90, 8, 8, 52, 16)])
    out = _boost_text_regions(img, first)

    src = np.asarray(img)
    res = np.asarray(out)
    # The colour block (bottom-right) must be untouched (R3).
    assert np.array_equal(src[48:72, 70:110], res[48:72, 70:110])
    # The text region should have changed (binarised to pure black/white).
    assert not np.array_equal(src[8:24, 8:60], res[8:24, 8:60])
    boosted_vals = set(np.unique(res[10:22, 10:58]).tolist())
    assert boosted_vals <= {0, 255}


def test_deterministic() -> None:
    img = _mixed_image()
    first = _first_pass([("Name", 90, 8, 8, 52, 16)])
    a = _boost_text_regions(img, first)
    b = _boost_text_regions(img, first)
    assert np.array_equal(np.asarray(a), np.asarray(b))


def test_negative_confidence_boxes_ignored() -> None:
    img = _mixed_image()
    # conf < 0 is tesseract's "no word here" sentinel — must not seed a region.
    out = _boost_text_regions(img, _first_pass([("", -1, 8, 8, 52, 16)]))
    assert np.array_equal(np.asarray(img), np.asarray(out))
