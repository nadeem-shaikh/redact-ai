"""Tesseract OCR adapter (ADR-008).

Uses ``pytesseract.image_to_data`` with ``output_type=DICT`` so we can
recover token-level bboxes and confidences (FR-2.2, FR-2.4). The dict
is then composed into the canonical ``Document`` tree (BUILD_SPEC §7.1).

After the full-page pass, low-confidence tokens are individually
re-OCR'd in isolation: the adapter crops each token's bbox (with a
few pixels of padding) and runs Tesseract again with ``--psm 7``
(single text line). Tesseract's whole-page layout analysis sometimes
merges a typed row with adjacent noise — a cursive signature, an
image edge, a chart legend — and emits gibberish tokens with very
low confidence; re-running on the crop alone bypasses that
contamination and recovers the underlying text. Replacement only
happens when the new tokens average above the floor, so noisy
regions (image artefacts) keep their original low-confidence tokens
rather than being swapped for equally-bad alternatives.
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

# Tokens at or below this confidence trigger a per-token re-OCR pass.
# 0.40 catches Tesseract's "I have no idea" output (typically 0.0–0.3)
# while leaving merely-noisy text alone.
_REOCR_TOKEN_THRESHOLD: float = 0.40
# Re-OCR'd tokens replace the original only if their *average*
# confidence clears this floor. Prevents swapping bad output for
# equally-bad output (image artefacts that are unrecognisable text
# under any pass).
_REOCR_REPLACEMENT_FLOOR: float = 0.75
# Pixels of padding around the cropped bbox passed to the per-token
# re-OCR. A small margin gives Tesseract enough context to recognise
# the character without bleeding in neighbouring tokens.
_REOCR_CROP_PAD: int = 3
# Hard cap on the number of per-token re-OCR calls per page. A heavily
# noisy scan can have hundreds of sub-threshold tokens; without a cap
# the refinement pass turns one Tesseract call into many and can blow
# the OCR-stage latency budget. 50 is comfortably enough for the
# realistic case (a typed form with a cursive-signature region: ~6
# refinements) and bounds the worst case at 50× a single-line OCR
# call, which is still small compared to a full-page pass.
_REOCR_MAX_PER_PAGE: int = 50


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
            data = pytesseract.image_to_data(
                image,
                lang=self.lang,
                output_type=pytesseract.Output.DICT,
                config="--psm 6",
            )
        except pytesseract.TesseractError as exc:
            raise ocr_error(str(exc)) from exc

        page = _compose_page(data, page_size=image.size)
        page = self._refine_low_confidence_tokens(page, image)
        source_hash = _hash_image(ingested.original)
        return Document(
            pages=(page,),
            source_hash=source_hash,
            input_width=ingested.original.width,
            input_height=ingested.original.height,
            transform=ingested.transform,
        )

    def _refine_low_confidence_tokens(self, page: Page, image: Image.Image) -> Page:
        """Walk the page and re-OCR each below-threshold token in isolation.

        Bounded by ``_REOCR_MAX_PER_PAGE`` so a noisy scan can't turn
        one full-page OCR call into hundreds of crop calls. Once the
        budget is exhausted any remaining sub-threshold tokens are
        kept as-is.
        """
        budget = [_REOCR_MAX_PER_PAGE]
        new_blocks: list[Block] = []
        for block in page.blocks:
            new_lines: list[Line] = []
            for line in block.lines:
                refined = self._refine_line(line, image, budget)
                new_lines.append(refined if refined is not None else line)
            if not new_lines:
                continue
            new_blocks.append(
                Block(
                    id=block.id,
                    bbox=_union(line.bbox for line in new_lines),
                    lines=tuple(new_lines),
                    block_type=block.block_type,
                )
            )
        return Page(
            index=page.index,
            width=page.width,
            height=page.height,
            blocks=tuple(new_blocks),
        )

    def _refine_line(self, line: Line, image: Image.Image, budget: list[int]) -> Line | None:
        """Return a new Line with replaced tokens, or ``None`` when no
        token was refined (caller keeps the original).

        ``budget`` is a single-element mutable list used as a shared
        counter across the whole page walk; each re-OCR attempt
        decrements it and the loop short-circuits when it hits zero.
        """
        refined_any = False
        out: list[Token] = []
        for tok in line.tokens:
            if tok.confidence > _REOCR_TOKEN_THRESHOLD or budget[0] <= 0:
                out.append(tok)
                continue
            budget[0] -= 1
            replacement = self._reocr_token(tok, image)
            if replacement is None:
                out.append(tok)
            else:
                out.extend(replacement)
                refined_any = True
        if not refined_any or not out:
            return None
        return Line(
            id=line.id,
            bbox=_union(t.bbox for t in out),
            tokens=tuple(out),
            reading_order=line.reading_order,
        )

    def _reocr_token(self, tok: Token, image: Image.Image) -> list[Token] | None:
        """Crop the token's bbox + padding and re-run Tesseract as a
        single text line. Return the new tokens only when their
        average confidence clears ``_REOCR_REPLACEMENT_FLOOR`` and
        each new bbox geometrically overlaps the original token's
        bbox (the 3px padded crop can pick up an adjacent word on
        tightly spaced text; importing it would duplicate text that's
        already on the line)."""
        pad = _REOCR_CROP_PAD
        x = max(0, tok.bbox.x - pad)
        y = max(0, tok.bbox.y - pad)
        x2 = min(image.width, tok.bbox.x + tok.bbox.w + pad)
        y2 = min(image.height, tok.bbox.y + tok.bbox.h + pad)
        if x2 <= x + 1 or y2 <= y + 1:
            return None
        crop = image.crop((x, y, x2, y2))
        try:
            data = pytesseract.image_to_data(
                crop,
                lang=self.lang,
                output_type=pytesseract.Output.DICT,
                config="--psm 7",
            )
        except pytesseract.TesseractError:
            return None
        new_tokens: list[Token] = []
        n = len(data.get("text", []))
        for i in range(n):
            text = (data["text"][i] or "").strip()
            if not text:
                continue
            left = int(data["left"][i])
            top = int(data["top"][i])
            w = max(int(data["width"][i]), 1)
            h = max(int(data["height"][i]), 1)
            conf = _scale_confidence(data["conf"][i])
            candidate = Token(
                id=f"{tok.id}-r{i}",
                text=text,
                bbox=BBox(x=x + left, y=y + top, w=w, h=h),
                confidence=conf,
            )
            # Geometric guard: a new bbox that doesn't overlap the
            # original at all came from the padding zone (an adjacent
            # word). Drop it so we don't duplicate text already
            # recognised elsewhere on the line.
            if candidate.bbox.iou(tok.bbox) == 0.0:
                continue
            new_tokens.append(candidate)
        if not new_tokens:
            return None
        avg = sum(t.confidence for t in new_tokens) / len(new_tokens)
        if avg < _REOCR_REPLACEMENT_FLOOR:
            return None
        return new_tokens


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
