"""Tesseract OCR adapter (ADR-008).

Uses ``pytesseract.image_to_data`` with ``output_type=DICT`` so we can
recover token-level bboxes and confidences (FR-2.2, FR-2.4). The dict
is then composed into the canonical ``Document`` tree (BUILD_SPEC §7.1).
"""

from __future__ import annotations

import hashlib
import io
import shutil
from collections.abc import Iterable
from functools import lru_cache
from typing import Any

import pytesseract
from PIL import Image

from redact_ai.errors import ocr_error
from redact_ai.models.document import (
    BBox,
    Block,
    Document,
    Line,
    Page,
    Token,
)
from redact_ai.pipeline.ingest import IngestedImage
from redact_ai.pipeline.ocr.base import OCRAdapter


@lru_cache(maxsize=1)
def _tesseract_version() -> str:
    try:
        version = str(pytesseract.get_tesseract_version()).strip().split()[0]
    except Exception:
        version = "unknown"
    return f"tesseract-{version}"


class TesseractAdapter(OCRAdapter):
    """Wrap ``pytesseract`` behind the project's adapter contract."""

    def __init__(self, lang: str = "eng") -> None:
        self.lang = lang

    def engine_id(self) -> str:
        return _tesseract_version()

    def recognise(self, ingested: IngestedImage) -> Document:
        if shutil.which("tesseract") is None:
            raise ocr_error("tesseract binary not found on PATH")
        image = ingested.normalised
        try:
            # First pass locates text regions; the authoritative pass runs on a
            # copy whose text regions have been contrast-boosted (ADR-008: OCR
            # bounds recall, and low-contrast small print reads as noise). The
            # boost is confined to text regions so colour/medical imagery — OCT
            # scans, fundus photos — passes through untouched.
            first = pytesseract.image_to_data(
                image,
                lang=self.lang,
                output_type=pytesseract.Output.DICT,
                config="--psm 6",
            )
            ocr_input = _boost_text_regions(image, first)
            data = pytesseract.image_to_data(
                ocr_input,
                lang=self.lang,
                output_type=pytesseract.Output.DICT,
                config="--psm 6",
            )
        except pytesseract.TesseractError as exc:
            raise ocr_error(str(exc)) from exc

        page = _compose_page(data, page_size=image.size)
        source_hash = _hash_image(ingested.original)
        return Document(
            pages=(page,),
            source_hash=source_hash,
            input_width=ingested.original.width,
            input_height=ingested.original.height,
            transform=ingested.transform,
        )


def _boost_text_regions(image: Image.Image, first_pass: dict[str, Any]) -> Image.Image:
    """Return a copy of ``image`` with text regions contrast-boosted.

    Uses the first OCR pass's word boxes to build a text-region mask, dilates it
    so glyph edges are covered, and applies a global-Otsu binarisation *only*
    inside that mask. Pixels outside any word box are left byte-identical, so
    non-text imagery (OCT B-scans, fundus photos) is never degraded (FR-2.x /
    ADR-008). Deterministic: a fixed dilation kernel and Otsu's argmax make the
    output a pure function of the input pixels (NFR-2.3).

    Returns the input unchanged when the first pass found no usable word boxes
    (a pure image) or when the OpenCV/NumPy stack is unavailable.
    """
    try:
        import cv2
        import numpy as np
    except ImportError:  # pragma: no cover - both ship in the base install
        return image

    grey = np.asarray(image.convert("L"))
    mask = np.zeros(grey.shape, dtype=np.uint8)
    boxes = 0
    n = len(first_pass.get("text", []))
    for i in range(n):
        if not (first_pass["text"][i] or "").strip():
            continue
        try:
            conf = float(first_pass["conf"][i])
        except (TypeError, ValueError):
            conf = -1.0
        if conf < 0:
            continue
        x = int(first_pass["left"][i])
        y = int(first_pass["top"][i])
        w = int(first_pass["width"][i])
        h = int(first_pass["height"][i])
        cv2.rectangle(mask, (x, y), (x + w, y + h), color=255, thickness=-1)
        boxes += 1

    if boxes == 0:
        return image

    # A wide, short kernel joins characters within a word/line without bleeding
    # into adjacent image regions.
    mask = cv2.dilate(mask, np.ones((3, 9), dtype=np.uint8))
    binarised = cv2.threshold(grey, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

    boosted = np.asarray(image.convert("RGB")).copy()
    region = mask > 0
    boosted[region] = binarised[region][:, None]  # grey → RGB by broadcast
    return Image.fromarray(boosted, mode="RGB")


def _compose_page(data: dict[str, Any], *, page_size: tuple[int, int]) -> Page:
    width, height = page_size
    groups: dict[tuple[int, int, int], dict[int, list[int]]] = {}
    n = len(data.get("text", []))
    for i in range(n):
        text = (data["text"][i] or "").strip()
        if not text:
            continue
        block_id = int(data["block_num"][i])
        par_id = int(data["par_num"][i])
        line_id = int(data["line_num"][i])
        key = (block_id, par_id, line_id)
        groups.setdefault(key, {}).setdefault(int(data["word_num"][i]), []).append(i)

    blocks: dict[int, dict[tuple[int, int], list[Line]]] = {}
    reading_order = 0
    for (block_id, par_id, line_id), word_groups in sorted(groups.items()):
        tokens: list[Token] = []
        for word_num in sorted(word_groups):
            idx = word_groups[word_num][0]
            text = (data["text"][idx] or "").strip()
            if not text:
                continue
            left = int(data["left"][idx])
            top = int(data["top"][idx])
            w = max(int(data["width"][idx]), 1)
            h = max(int(data["height"][idx]), 1)
            conf = _scale_confidence(data["conf"][idx])
            tok_id = f"t-0-{block_id}-{par_id}-{line_id}-{word_num}"
            tokens.append(
                Token(
                    id=tok_id,
                    text=text,
                    bbox=BBox(x=left, y=top, w=w, h=h),
                    confidence=conf,
                )
            )
        if not tokens:
            continue
        line_bbox = _union(t.bbox for t in tokens)
        line = Line(
            id=f"l-0-{block_id}-{par_id}-{line_id}",
            bbox=line_bbox,
            tokens=tuple(tokens),
            reading_order=reading_order,
        )
        reading_order += 1
        blocks.setdefault(block_id, {}).setdefault((block_id, par_id), []).append(line)

    block_list: list[Block] = []
    for block_id in sorted(blocks):
        lines_in_block: list[Line] = []
        for par_key in sorted(blocks[block_id]):
            lines_in_block.extend(blocks[block_id][par_key])
        block_bbox = _union(line.bbox for line in lines_in_block)
        block_list.append(
            Block(
                id=f"b-0-{block_id}",
                bbox=block_bbox,
                lines=tuple(lines_in_block),
                block_type="paragraph",
            )
        )

    return Page(index=0, width=width, height=height, blocks=tuple(block_list))


def _scale_confidence(raw: Any) -> float:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return 0.0
    if value < 0:
        return 0.0
    return max(0.0, min(1.0, value / 100.0))


def _union(bboxes: Iterable[BBox]) -> BBox:
    items = list(bboxes)
    out: BBox = items[0]
    for b in items[1:]:
        out = out.union(b)
    return out


def _hash_image(image: Image.Image) -> str:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return hashlib.sha256(buf.getvalue()).hexdigest()


__all__ = ["TesseractAdapter"]
