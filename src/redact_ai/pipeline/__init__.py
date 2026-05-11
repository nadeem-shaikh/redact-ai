"""Top-level pipeline entry point (BUILD_SPEC §7 / ADR-004).

The shape of :func:`redact` matches the API_SPEC §2 core operation:

    redact(input: ImageInput, policy: Policy) -> RedactionResult

In Python the ``ImageInput`` is simply the raw image bytes plus the MIME
type the client claimed. The result holds the redacted image bytes,
the manifest, and any warnings raised along the way.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime

from redact_ai.errors import (
    RedactError,
    detector_error,
    ocr_error,
    redaction_error,
)
from redact_ai.logging import get_logger
from redact_ai.models.document import Document
from redact_ai.models.findings import Confidence, Finding, confidence_ge
from redact_ai.models.manifest import Manifest, Warning
from redact_ai.pipeline.detect.registry import build_detectors
from redact_ai.pipeline.ingest import IngestedImage, ingest_bytes
from redact_ai.pipeline.merge import merge_findings
from redact_ai.pipeline.ocr.base import OCRAdapter
from redact_ai.pipeline.ocr.tesseract import TesseractAdapter
from redact_ai.pipeline.redact import RedactedImage, render_redacted
from redact_ai.pipeline.report import build_manifest
from redact_ai.policy.schema import BlockStyle, Policy, RedactionStyle
from redact_ai.version import __version__

log = get_logger("pipeline")


@dataclass(slots=True)
class RedactionResult:
    image: RedactedImage
    manifest: Manifest
    warnings: tuple[Warning, ...]


def redact(
    image_bytes: bytes,
    mime_type: str,
    policy: Policy,
    *,
    ocr: OCRAdapter | None = None,
    request_id: str | None = None,
) -> RedactionResult:
    """Run the full Ingest → OCR → Detect → Merge → Redact → Report pipeline.

    Fails closed (ADR-005): any unhandled error inside Ingest, OCR, or
    Redact propagates as :class:`~redact_ai.errors.RedactError`. Detector
    errors do not abort the run — they downgrade to a warning per FR-8.2.
    """
    ocr = ocr or TesseractAdapter()
    warnings: list[Warning] = []

    ingested = ingest_bytes(image_bytes, mime_type)
    document = _run_ocr(ocr, ingested, warnings)
    findings = _run_detectors(document, policy, warnings)
    merged = merge_findings(findings)
    final = _apply_thresholds(merged, policy, warnings)

    style = _effective_style(policy, warnings)
    try:
        redacted = render_redacted(ingested, final, style)
    except RedactError:
        raise
    except Exception as exc:
        raise redaction_error(str(exc)) from exc

    if policy.verbose_report:
        warnings.append(
            Warning(
                code="W_VERBOSE_REPORT_ENABLED",
                message="Manifest contains raw matched text.",
                source="report",
            )
        )

    if not final:
        warnings.append(
            Warning(
                code="W_NO_FINDINGS",
                message="Nothing was redacted. Output is the input re-encoded.",
                source="report",
            )
        )

    manifest = build_manifest(
        policy=policy,
        runtime_version=__version__,
        ocr_engine=ocr.engine_id(),
        input_hash=_sha256(image_bytes),
        output_hash=_sha256(redacted.bytes),
        created_at=_now_iso(),
        findings=final,
        warnings=warnings,
        include_matched_text=policy.verbose_report,
    )
    return RedactionResult(image=redacted, manifest=manifest, warnings=tuple(warnings))


def _run_ocr(ocr: OCRAdapter, ingested: IngestedImage, warnings: list[Warning]) -> Document:
    try:
        document = ocr.recognise(ingested)
    except RedactError:
        raise
    except Exception as exc:
        raise ocr_error(str(exc)) from exc
    if any(t.confidence < 0.60 for t in document.iter_tokens()):
        warnings.append(
            Warning(
                code="W_LOW_CONFIDENCE_TOKEN",
                message="At least one token had OCR confidence < 0.60.",
                source="ocr",
            )
        )
    return document


def _run_detectors(document: Document, policy: Policy, warnings: list[Warning]) -> list[Finding]:
    detectors = build_detectors(policy)
    if not detectors:
        return []
    out: list[Finding] = []
    errors: list[str] = []
    succeeded = 0
    for detector in detectors:
        try:
            out.extend(detector.detect(document, policy))
            succeeded += 1
        except Exception as exc:
            errors.append(f"{detector.rule_id}: {exc}")
            log.warning(
                "detector_failed",
                extra={"stage": "detect", "fields": {"rule_id": detector.rule_id}},
            )
    if errors and succeeded == 0:
        raise detector_error("; ".join(errors))
    if errors:
        warnings.append(
            Warning(
                code="W_DETECTOR_PARTIAL_FAILURE",
                message="One or more detectors errored; others ran.",
                source="detect",
            )
        )
    return out


def _apply_thresholds(
    findings: list[Finding], policy: Policy, warnings: list[Warning]
) -> list[Finding]:
    thresholds: dict[str, Confidence] = {
        d.id: policy.effective_threshold(d) for d in policy.enabled_detectors()
    }
    out: list[Finding] = []
    for f in findings:
        # If the finding was merged from multiple rules, use the most
        # permissive (lowest) threshold so we don't drop a high-confidence
        # PAN finding because a tagalong rule had threshold=high.
        rule_ids = (f.rule_id, *f.merged_from)
        thresh = min(
            (thresholds.get(rid, "low") for rid in rule_ids),
            key=lambda t: {"low": 0, "medium": 1, "high": 2}[t],
        )
        if confidence_ge(f.confidence, thresh):
            out.append(f)
    return out


def _effective_style(policy: Policy, warnings: list[Warning]) -> RedactionStyle:
    style = policy.redaction_style
    if style.kind == "blur":
        warnings.append(
            Warning(
                code="W_STYLE_DOWNGRADED_TO_BLOCK",
                message="Blur is reversible on text; downgraded to block.",
                source="redact",
            )
        )
        return BlockStyle(color=style.color, padding_px=style.padding_px)
    return style


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _now_iso() -> str:
    return datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


__all__ = ["RedactionResult", "redact"]
