"""Typed errors with stable codes (BUILD_SPEC §13.1).

The pipeline must fail closed on any error that risks leaking sensitive
content (ADR-005). Every error carries a stable machine-readable ``code``
plus a one-line ``hint`` that the local UI surfaces to the user
(NFR-5.2).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True, slots=True)
class ErrorDetail:
    code: str
    message: str
    hint: str
    http_status: int


# HTTP status mapping mirrors BUILD_SPEC §8.1.
E_INPUT_FORMAT: Final = "E_INPUT_FORMAT"
E_INPUT_TOO_LARGE: Final = "E_INPUT_TOO_LARGE"
E_OCR: Final = "E_OCR"
E_DETECTOR: Final = "E_DETECTOR"
E_REDACTION: Final = "E_REDACTION"
E_IO: Final = "E_IO"
E_POLICY: Final = "E_POLICY"
E_CSRF: Final = "E_CSRF"
E_ORIGIN: Final = "E_ORIGIN"


_HTTP_STATUS: Final[dict[str, int]] = {
    E_INPUT_FORMAT: 415,
    E_INPUT_TOO_LARGE: 413,
    E_POLICY: 400,
    E_OCR: 502,
    E_DETECTOR: 502,
    E_REDACTION: 500,
    E_IO: 500,
    E_CSRF: 403,
    E_ORIGIN: 403,
}


class RedactError(Exception):
    """Terminal pipeline error with a stable code."""

    def __init__(self, code: str, message: str, *, hint: str = "") -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.hint = hint

    @property
    def http_status(self) -> int:
        return _HTTP_STATUS.get(self.code, 500)

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message, "hint": self.hint}


def input_format_error(mime: str) -> RedactError:
    return RedactError(
        E_INPUT_FORMAT,
        (
            f"Unsupported MIME type: {mime}. "
            "Supported: PNG, JPEG, WebP, GIF, BMP, TIFF, HEIC/HEIF, AVIF."
        ),
        hint="Try saving the file as one of those formats and upload again.",
    )


def input_too_large_error(actual_bytes: int, limit_bytes: int) -> RedactError:
    actual_mb = actual_bytes / (1024 * 1024)
    limit_mb = limit_bytes / (1024 * 1024)
    return RedactError(
        E_INPUT_TOO_LARGE,
        f"Input exceeds {limit_mb:.0f} MB limit ({actual_mb:.1f} MB).",
        hint="Crop or compress the image, then retry.",
    )


def ocr_error(reason: str) -> RedactError:
    return RedactError(
        E_OCR,
        f"OCR engine failed: {reason}. Try a higher-resolution image.",
        hint="Re-take the screenshot at full resolution or rescan.",
    )


def detector_error(reason: str) -> RedactError:
    return RedactError(
        E_DETECTOR,
        f"All detectors failed. See logs for details. ({reason})",
        hint="This is a bug — please report it with the request id from your logs.",
    )


def redaction_error(reason: str) -> RedactError:
    return RedactError(
        E_REDACTION,
        f"Could not produce a safe redacted image. No output written. ({reason})",
        hint="Try a different redaction style or a sharper image.",
    )


def policy_error(policy_id: str, reason: str) -> RedactError:
    return RedactError(
        E_POLICY,
        f"Policy '{policy_id}' is invalid: {reason}.",
        hint="Check the policy YAML against the schema in BUILD_SPEC §6.",
    )


def csrf_error() -> RedactError:
    return RedactError(
        E_CSRF,
        "Missing or invalid CSRF token.",
        hint="Reload the page to obtain a fresh token and retry.",
    )


def origin_error() -> RedactError:
    return RedactError(
        E_ORIGIN,
        "Request origin is not loopback; rejected.",
        hint="Only requests from 127.0.0.1 are accepted.",
    )
