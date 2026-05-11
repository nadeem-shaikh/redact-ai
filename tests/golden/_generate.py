"""Generate synthetic test fixtures (TC-001..TC-010, BUILD_SPEC §16.1).

Run from the repo root::

    python tests/golden/_generate.py

The script writes PNG/JPEG inputs into ``tests/golden/inputs/`` and is
reproducible: re-running it produces byte-identical files.
"""

from __future__ import annotations

import io
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[2]
INPUTS = ROOT / "tests" / "golden" / "inputs"


@dataclass(slots=True, frozen=True)
class Spec:
    name: str
    lines: list[str]
    suffix: str = ".png"
    width: int = 1600
    margin: int = 60
    line_gap: int = 18
    font_size: int = 28
    background: str = "white"
    text_color: str = "black"
    post: Callable[[Image.Image], Image.Image] | None = None


def _font(size: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size=size)
    except OSError:
        return ImageFont.load_default()


def _render(spec: Spec) -> Image.Image:
    font = _font(spec.font_size)
    line_height = spec.font_size + 8
    height = spec.margin * 2 + (line_height + spec.line_gap) * max(len(spec.lines), 1)
    img = Image.new("RGB", (spec.width, height), spec.background)
    draw = ImageDraw.Draw(img)
    y = spec.margin
    for line in spec.lines:
        draw.text((spec.margin, y), line, fill=spec.text_color, font=font)
        y += line_height + spec.line_gap
    if spec.post is not None:
        img = spec.post(img)
    return img


def _save(spec: Spec, image: Image.Image) -> None:
    INPUTS.mkdir(parents=True, exist_ok=True)
    path = INPUTS / f"{spec.name}{spec.suffix}"
    fmt = "PNG" if spec.suffix == ".png" else "JPEG" if spec.suffix == ".jpg" else "WEBP"
    kwargs: dict[str, object] = {}
    if fmt == "JPEG":
        kwargs["quality"] = 92
    elif fmt == "PNG":
        kwargs["optimize"] = True
    elif fmt == "WEBP":
        kwargs["quality"] = 92
    image.save(path, format=fmt, **kwargs)


def _blur(img: Image.Image) -> Image.Image:
    """Simulate a phone snapshot of a printed letter (TC-008).

    Down-sample + re-up-sample to add aliasing, then a JPEG round-trip
    and a small blur. The result is still readable to Tesseract but
    materially noisier than a screenshot, which is the property the
    spec is reaching for in TC-008.
    """
    small = img.resize(
        (max(img.width // 3, 1), max(img.height // 3, 1)),
        Image.Resampling.BILINEAR,
    )
    again = small.resize(img.size, Image.Resampling.BILINEAR)
    blurred = again.filter(ImageFilter.GaussianBlur(radius=0.6))
    buf = io.BytesIO()
    blurred.save(buf, format="JPEG", quality=55)
    return Image.open(io.BytesIO(buf.getvalue())).convert("RGB")


SPECS: list[Spec] = [
    Spec(
        name="TC-001",
        lines=[
            "ACME BANK - Statement",
            "",
            "Aanya Sharma",
            "Account: 98765432",
            "IBAN: GB29 NWBK 6016 1331 9268 19",
            "",
            "Summary balance forward 1,250.00",
            "Closing balance available 3,892.18",
        ],
    ),
    Spec(
        name="TC-002",
        lines=[
            "From: alex.example@example.com",
            "To: priya.shaw@example.com",
            "Subject: lunch tomorrow",
            "",
            "Hey - confirming 12.30 at the bistro.",
            "Best,",
            "Alex",
            "Mobile +1 555 123 4567",
        ],
    ),
    Spec(
        name="TC-003",
        lines=[
            "City Lab Report",
            "",
            "Patient: Priya Shaw",
            "DOB",
            "12/04/1992",
            "MRN: 0001234",
            "",
            "Test: Glucose 110 mg/dL",
            "Test: Cholesterol 180 mg/dL",
        ],
    ),
    Spec(
        name="TC-004",
        lines=[
            "REPUBLIC OF EXAMPLE",
            "",
            "Name: Aanya Sharma",
            "DOB",
            "12/04/1992",
            "SSN: 123-45-6789",
        ],
    ),
    Spec(
        name="TC-005",
        lines=[
            "main.py - editor",
            "",
            "AWS_KEY = AKIAIOSFODNN7EXAMPLE",
            "TOKEN = sk-Tg7HsfRqLk9PzZmXwVuC4Bn2HsfRqLk9P",
            "print(client.run())",
        ],
    ),
    Spec(
        name="TC-006",
        lines=[
            "When the build is green",
            "and the tests still pass",
            "you deploy on Friday",
            "and pretend it is class.",
        ],
    ),
    Spec(
        name="TC-007",
        lines=[
            "Analytics Dashboard",
            "",
            "user.one@example.com 412",
            "user.two@example.com 318",
            "user.three@example.com 297",
            "",
            "Chart: weekly traffic up 12%",
        ],
    ),
    Spec(
        name="TC-008",
        lines=[
            "Priya Shaw",
            "221 Baker Street",
            "Springfield, IL 62704",
        ],
        post=_blur,
    ),
    Spec(
        name="TC-009",
        lines=[
            "RECEIPT / RECIBO",
            "",
            "Item / Articulo: cafe",
            "Total: 4.50 USD",
            "",
            "Card / Tarjeta: 4111 1111 1111 1111",
            "Thanks / Gracias",
        ],
    ),
]


def write_unsupported_fixture() -> None:
    """TC-010 — write a 1-byte BMP-like placeholder for the unsupported-format check."""
    INPUTS.mkdir(parents=True, exist_ok=True)
    (INPUTS / "TC-010.bmp").write_bytes(b"BM")


def main() -> None:
    for spec in SPECS:
        image = _render(spec)
        _save(spec, image)
    write_unsupported_fixture()
    print(f"wrote {len(SPECS) + 1} fixtures into {INPUTS}")


if __name__ == "__main__":
    main()
