"""Shared pytest fixtures."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont


@pytest.fixture(scope="session")
def default_font() -> ImageFont.ImageFont:
    """Return a DejaVu font at 26pt; falls back to PIL's default."""
    try:
        return ImageFont.truetype("DejaVuSans.ttf", 26)
    except OSError:  # pragma: no cover — env-specific fallback.
        return ImageFont.load_default()


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def render_lines(
    lines: list[str],
    *,
    width: int = 1600,
    margin: int = 50,
    line_gap: int = 16,
    font: ImageFont.ImageFont | None = None,
) -> bytes:
    """Render ``lines`` as black text on a white PNG and return the bytes."""
    if font is None:
        try:
            font = ImageFont.truetype("DejaVuSans.ttf", 26)
        except OSError:  # pragma: no cover
            font = ImageFont.load_default()
    line_height = 32
    height = margin * 2 + (line_height + line_gap) * max(len(lines), 1)
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    y = margin
    for line in lines:
        draw.text((margin, y), line, fill="black", font=font)
        y += line_height + line_gap
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
