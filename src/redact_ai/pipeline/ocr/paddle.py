"""PaddleOCR adapter (ADR-008, optional extra ``redact-ai[ocr-paddle]``).

This module is intentionally lightweight: PaddleOCR is a 0.5–1 GB
dependency, so we *only* import it when callers actually instantiate
the adapter. The class exists so the registry / docs can advertise it;
quality work and the recall baseline live with Tesseract for v0.1.
"""

from __future__ import annotations

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


class PaddleAdapter(OCRAdapter):
    """Thin wrapper around PaddleOCR.

    PaddleOCR is opt-in. Importing this class is cheap; constructing it
    triggers the heavy import.
    """

    def __init__(self, lang: str = "en") -> None:
        try:
            from paddleocr import PaddleOCR  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover — exercised only with extra.
            raise ocr_error(
                "PaddleOCR is not installed. Reinstall with 'pip install redact-ai[ocr-paddle]'."
            ) from exc
        self._engine = PaddleOCR(use_angle_cls=False, lang=lang, show_log=False)
        self.lang = lang

    def engine_id(self) -> str:
        return "paddleocr"

    def recognise(self, ingested: IngestedImage) -> Document:  # pragma: no cover - heavy
        import numpy as np

        arr = np.array(ingested.normalised)
        try:
            result = self._engine.ocr(arr, cls=False)
        except Exception as exc:  # noqa: BLE001 — fail closed.
            raise ocr_error(str(exc)) from exc

        tokens: list[Token] = []
        if result and result[0]:
            for idx, entry in enumerate(result[0]):
                points, (text, conf) = entry
                xs = [p[0] for p in points]
                ys = [p[1] for p in points]
                x = int(min(xs))
                y = int(min(ys))
                w = max(int(max(xs) - x), 1)
                h = max(int(max(ys) - y), 1)
                tokens.append(
                    Token(
                        id=f"t-0-0-0-{idx}",
                        text=str(text),
                        bbox=BBox(x=x, y=y, w=w, h=h),
                        confidence=float(conf),
                    )
                )
        if tokens:
            line_bbox = tokens[0].bbox
            for t in tokens[1:]:
                line_bbox = line_bbox.union(t.bbox)
            line = Line(id="l-0-0-0", bbox=line_bbox, tokens=tuple(tokens), reading_order=0)
            block = Block(id="b-0-0", bbox=line_bbox, lines=(line,), block_type="paragraph")
            blocks: tuple[Block, ...] = (block,)
        else:
            blocks = ()
        # PaddleOCR can legitimately find nothing; emit an empty page in that case.
        page = Page(
            index=0,
            width=ingested.normalised.width,
            height=ingested.normalised.height,
            blocks=blocks,
        )
        import hashlib
        import io

        buf = io.BytesIO()
        ingested.original.save(buf, format="PNG")
        return Document(
            pages=(page,),
            source_hash=hashlib.sha256(buf.getvalue()).hexdigest(),
            input_width=ingested.original.width,
            input_height=ingested.original.height,
            transform=ingested.transform,
        )


__all__ = ["PaddleAdapter"]
