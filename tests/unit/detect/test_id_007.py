"""ID-007 FacePhotoDetector tests."""

from __future__ import annotations

import pytest
from PIL import Image, ImageDraw

from redact_ai.errors import RedactError
from redact_ai.policy.loader import load_default_policy

pytest.importorskip("cv2")

from redact_ai.pipeline.detect.vision.face import FacePhotoDetector  # noqa: E402


def _blank(
    width: int = 800, height: int = 600, color: tuple[int, int, int] = (220, 220, 220)
) -> Image.Image:
    return Image.new("RGB", (width, height), color)


def _synthetic_face(image: Image.Image, cx: int, cy: int, r: int) -> None:
    """Draw a crude face — light oval head + two dark eyes + dark mouth.

    Real Haar cascades won't fire on this (they want photographic
    intensity gradients) — used only for negative tests.
    """
    draw = ImageDraw.Draw(image)
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 220, 180))
    eye_r = max(r // 8, 2)
    eye_y = cy - r // 5
    draw.ellipse(
        (cx - r // 2 - eye_r, eye_y - eye_r, cx - r // 2 + eye_r, eye_y + eye_r),
        fill=(40, 40, 40),
    )
    draw.ellipse(
        (cx + r // 2 - eye_r, eye_y - eye_r, cx + r // 2 + eye_r, eye_y + eye_r),
        fill=(40, 40, 40),
    )
    draw.line(
        (cx - r // 3, cy + r // 3, cx + r // 3, cy + r // 3),
        fill=(40, 40, 40),
        width=max(r // 12, 2),
    )


def test_no_face_no_finding() -> None:
    """Blank image -> no detections, no errors."""
    out = FacePhotoDetector().detect(_blank(), load_default_policy())
    assert out == []


def test_synthetic_drawing_does_not_false_trigger() -> None:
    """A flat-shaded oval+eyes drawing isn't a real face -> no detection.

    The negative case matters: it confirms the cascade isn't matching
    on simple geometric shapes that happen to be present in UI icons.
    """
    image = _blank()
    _synthetic_face(image, cx=200, cy=200, r=120)
    out = FacePhotoDetector().detect(image, load_default_policy())
    assert out == []


def test_invalid_scale_factor_rejected() -> None:
    """scale_factor <= 1.0 would cause OpenCV to spin forever; fail closed."""
    policy = load_default_policy()
    overridden = policy.model_copy(
        update={
            "detectors": tuple(
                det.model_copy(update={"overrides": {"scale_factor": 1.0}})
                if det.id == "ID-007"
                else det
                for det in policy.detectors
            )
        }
    )
    with pytest.raises(RedactError):
        FacePhotoDetector().detect(_blank(), overridden)


def test_invalid_min_size_fraction_rejected() -> None:
    policy = load_default_policy()
    overridden = policy.model_copy(
        update={
            "detectors": tuple(
                det.model_copy(update={"overrides": {"min_size_fraction": 0.0}})
                if det.id == "ID-007"
                else det
                for det in policy.detectors
            )
        }
    )
    with pytest.raises(RedactError):
        FacePhotoDetector().detect(_blank(), overridden)


def test_missing_cascade_raises_policy_error() -> None:
    """Pointing at a non-existent cascade file fails closed (ADR-005)."""
    policy = load_default_policy()
    overridden = policy.model_copy(
        update={
            "detectors": tuple(
                det.model_copy(update={"overrides": {"cascade": "no_such_cascade.xml"}})
                if det.id == "ID-007"
                else det
                for det in policy.detectors
            )
        }
    )
    with pytest.raises(RedactError):
        FacePhotoDetector().detect(_blank(), overridden)
