"""ID-007 — Haar-cascade face detector (ADR-012, DETECTORS_v0.1)."""

from __future__ import annotations

from functools import lru_cache
from typing import Any, ClassVar

from PIL import Image

from redact_ai.errors import policy_error
from redact_ai.models.document import BBox
from redact_ai.models.findings import Category, Confidence, Finding
from redact_ai.policy.schema import Policy

_DEFAULT_CASCADE = "haarcascade_frontalface_default.xml"
# Min face size as a fraction of the short side — gates out very small
# detections that would dominate a screenshot with false positives.
_DEFAULT_MIN_SIZE_FRACTION = 0.04
_DEFAULT_SCALE_FACTOR = 1.1
_DEFAULT_MIN_NEIGHBORS = 5


@lru_cache(maxsize=4)
def _load_cascade(cascade_name: str) -> Any:
    try:
        import cv2
    except ImportError as exc:  # pragma: no cover - opencv is a required dep
        raise RuntimeError(
            "opencv-python-headless is required for ID-007 FacePhotoDetector "
            "but is not installed."
        ) from exc
    haarcascades_dir = cv2.data.haarcascades  # type: ignore[attr-defined]
    path = f"{haarcascades_dir}{cascade_name}"
    classifier = cv2.CascadeClassifier(path)
    if classifier.empty():
        raise RuntimeError(f"OpenCV Haar cascade '{cascade_name}' could not be loaded from {path}.")
    return classifier


class FacePhotoDetector:
    """ID-007 — detect human faces in the image (profile photos, avatars).

    Runs the OpenCV frontal-face Haar cascade on the original image and
    emits one finding per detected face. Bounding boxes are in original
    input pixel coordinates so the redactor masks the same region the
    user uploaded.
    """

    rule_id: ClassVar[str] = "ID-007"
    category: ClassVar[Category] = "IDENTITY"

    def detect(self, image: Image.Image, policy: Policy) -> list[Finding]:
        import cv2
        import numpy as np

        overrides = self._overrides(policy)
        cascade = overrides.get("cascade", _DEFAULT_CASCADE)
        scale_factor = float(overrides.get("scale_factor", _DEFAULT_SCALE_FACTOR))
        min_neighbors = int(overrides.get("min_neighbors", _DEFAULT_MIN_NEIGHBORS))
        min_size_fraction = float(overrides.get("min_size_fraction", _DEFAULT_MIN_SIZE_FRACTION))
        if scale_factor <= 1.0:
            raise policy_error(policy.id, "ID-007.scale_factor must be > 1.0")
        if min_neighbors < 0:
            raise policy_error(policy.id, "ID-007.min_neighbors must be >= 0")
        if not 0.0 < min_size_fraction <= 1.0:
            raise policy_error(policy.id, "ID-007.min_size_fraction must be in (0, 1]")

        try:
            classifier = _load_cascade(cascade)
        except RuntimeError as exc:
            raise policy_error(policy.id, str(exc)) from exc

        rgb = image if image.mode == "RGB" else image.convert("RGB")
        arr = np.asarray(rgb)
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)

        short_side = min(arr.shape[0], arr.shape[1])
        min_dim = max(int(short_side * min_size_fraction), 1)
        rects = classifier.detectMultiScale(
            gray,
            scaleFactor=scale_factor,
            minNeighbors=min_neighbors,
            minSize=(min_dim, min_dim),
        )
        if len(rects) == 0:
            return []

        out: list[Finding] = []
        # Confidence for an unranked Haar hit is `medium`; the cascade
        # has no per-detection score. min_neighbors gates spurious hits.
        conf: Confidence = "medium"
        for x, y, w, h in rects:
            out.append(
                Finding(
                    rule_id=self.rule_id,
                    category=self.category,
                    bbox=BBox(x=int(x), y=int(y), w=int(w), h=int(h)),
                    confidence=conf,
                    matched_text="",
                    page_index=0,
                )
            )
        return out

    def _overrides(self, policy: Policy) -> dict[str, Any]:
        for det in policy.detectors:
            if det.id == self.rule_id:
                return dict(det.overrides)
        return {}
