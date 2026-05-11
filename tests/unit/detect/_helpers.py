"""Test helpers — build synthetic ``Document`` instances without OCR.

Tests that exercise detectors directly should use ``make_doc`` so the
test only depends on the regex/heuristic, not on Tesseract output
stability across versions.
"""

from __future__ import annotations

from redact_ai.models.document import (
    AffineTransform,
    BBox,
    Block,
    Document,
    Line,
    Page,
    Token,
)


def make_doc(lines: list[str], *, token_confidence: float = 0.95) -> Document:
    """Lay out ``lines`` as a single page with one block per line.

    Tokens are placed left-to-right with a fixed character width so each
    detector can find them deterministically.
    """
    blocks: list[Block] = []
    y = 10
    line_height = 30
    char_w = 12
    block_idx = 0
    for line_idx, text in enumerate(lines):
        tokens: list[Token] = []
        x = 10
        for tok_idx, raw in enumerate(text.split(" ")):
            if not raw:
                continue
            w = max(len(raw) * char_w, 1)
            tokens.append(
                Token(
                    id=f"t-0-{block_idx}-{line_idx}-{tok_idx}",
                    text=raw,
                    bbox=BBox(x=x, y=y, w=w, h=line_height - 6),
                    confidence=token_confidence,
                )
            )
            x += w + char_w  # one space between tokens
        if not tokens:
            y += line_height
            continue
        line_bbox = tokens[0].bbox
        for t in tokens[1:]:
            line_bbox = line_bbox.union(t.bbox)
        line = Line(
            id=f"l-0-{block_idx}-{line_idx}",
            bbox=line_bbox,
            tokens=tuple(tokens),
            reading_order=line_idx,
        )
        block_bbox = line.bbox
        blocks.append(
            Block(
                id=f"b-0-{block_idx}",
                bbox=block_bbox,
                lines=(line,),
                block_type="paragraph",
            )
        )
        block_idx += 1
        y += line_height
    page = Page(index=0, width=2000, height=y + 10, blocks=tuple(blocks))
    return Document(
        pages=(page,),
        source_hash="0" * 64,
        input_width=2000,
        input_height=y + 10,
        transform=AffineTransform.identity(),
    )


def make_doc_block(lines: list[str], *, token_confidence: float = 0.95) -> Document:
    """Like :func:`make_doc`, but groups all lines into a single block.

    Useful when a detector needs trigger-and-value relationships on
    different lines of the *same* block (e.g. label-anchored rules).
    """
    base = make_doc(lines, token_confidence=token_confidence)
    page = base.pages[0]
    all_lines = [line for block in page.blocks for line in block.lines]
    if not all_lines:
        return base
    block_bbox = all_lines[0].bbox
    for line in all_lines[1:]:
        block_bbox = block_bbox.union(line.bbox)
    block = Block(
        id="b-0-0",
        bbox=block_bbox,
        lines=tuple(all_lines),
        block_type="paragraph",
    )
    new_page = Page(index=0, width=page.width, height=page.height, blocks=(block,))
    return Document(
        pages=(new_page,),
        source_hash=base.source_hash,
        input_width=base.input_width,
        input_height=base.input_height,
        transform=base.transform,
    )
