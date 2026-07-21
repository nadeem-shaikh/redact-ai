"""ML-001 — GLiNER strong PII engine (ADR-013).

A transformer-based generalist NER engine that detects PII across every
category in a single deterministic forward pass. It **complements** — it does
not replace — the deterministic regex/checksum detectors, which stay
authoritative for structured identifiers (Luhn PANs, IBAN mod-97, cloud-key
prefixes) where a validator beats a probabilistic model.

Optional: the runtime ships in the ``redact-ai[strong]`` extra and the detector
is disabled by default in the shipped policy. When enabled without the extra
installed it fails closed with ``E_POLICY`` (ADR-005), the same contract as the
spaCy detector ``ID-006``.

Runs entirely on-device (ADR-002): the model resolves from the local Hugging
Face cache; fetching is an install/first-load step, not a redaction-hot-path
network call. Inference is deterministic under greedy/argmax decoding with the
model in eval mode (NFR-2.3).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, ClassVar, get_args

from redact_ai.errors import policy_error
from redact_ai.models.document import Document
from redact_ai.models.findings import Category, Confidence, Finding
from redact_ai.pipeline.detect.base import (
    cap_confidence,
    confidence_from_tokens,
    line_text_and_offsets,
    policy_override,
    tokens_covering,
    union_bboxes,
)
from redact_ai.policy.schema import Policy

# Safe, proven default: the stable ``gliner`` runtime plus this PII checkpoint.
# GLiNER2-PII (Fastino) leads the SPY benchmark but may require a newer runtime,
# so it is reached via ``overrides.model`` rather than pinned here (KTD2).
_DEFAULT_MODEL = "urchade/gliner_multi_pii-v1"
# Pin the default model to an immutable commit so two installs of the same
# redact-ai release load byte-identical weights (NFR-2.3) — the repo name alone
# is a mutable branch pointer. Override with ``overrides.revision`` for a custom
# model; a bare ``overrides.model`` clears this default pin (a different repo has
# its own history).
_DEFAULT_MODEL_REVISION = "1fcf13e85f4eef5394e1fcd406cf2ca9ea82351d"
_DEFAULT_SCORE_THRESHOLD = 0.5

_VALID_CATEGORIES: frozenset[str] = frozenset(get_args(Category))

# Natural-language GLiNER labels → redact-ai category. Keys are lowercased; the
# model is prompted with exactly these labels. Overridable via policy.
_DEFAULT_LABEL_MAP: dict[str, Category] = {
    "person": "IDENTITY",
    "date of birth": "IDENTITY",
    "passport number": "IDENTITY",
    "driver's license number": "IDENTITY",
    "social security number": "IDENTITY",
    "national id number": "IDENTITY",
    "tax identification number": "IDENTITY",
    "email address": "CONTACT",
    "phone number": "CONTACT",
    "address": "CONTACT",
    "credit card number": "FINANCIAL",
    "bank account number": "FINANCIAL",
    "iban": "FINANCIAL",
    "medical record number": "HEALTH",
    "health condition": "HEALTH",
    "api key": "CREDENTIALS",
    "password": "CREDENTIALS",
    "secret": "CREDENTIALS",
    "gps coordinates": "LOCATION",
}

_INSTALL_HINT = (
    "The GLiNER engine ships in the optional extra: install it with "
    "`pip install redact-ai[strong]`. The model loads from the local Hugging "
    "Face cache only (ADR-002) — pre-fetch it once with "
    "`huggingface-cli download <model> --revision <revision>`, or set the "
    "ML-001 override `allow_download: true` for a one-time online fetch."
)


@lru_cache(maxsize=2)
def _load_gliner(model_name: str, revision: str | None, local_files_only: bool) -> Any:
    """Load and cache a GLiNER model in deterministic eval mode.

    ``gliner`` is imported lazily so merely registering ``ML-001`` never pulls
    torch/transformers into a base install (the detector only imports them when
    it actually runs). ``local_files_only`` keeps the redaction hot path offline
    (ADR-002): a cold cache raises rather than reaching the network mid-request.
    ``revision`` pins the exact weights for reproducibility (NFR-2.3).
    """
    try:
        from gliner import GLiNER
    except ImportError as exc:
        raise RuntimeError(
            "GLiNER is required for ML-001 but is not installed. " + _INSTALL_HINT
        ) from exc
    try:
        model = GLiNER.from_pretrained(
            model_name, revision=revision, local_files_only=local_files_only
        )
    except Exception as exc:
        # Missing package, cold cache under local_files_only, or resolution
        # failure — all fail closed with a prefetch hint.
        pinned = f"@{revision}" if revision else ""
        raise RuntimeError(
            f"GLiNER model '{model_name}{pinned}' could not be loaded. {_INSTALL_HINT}"
        ) from exc
    # Deterministic inference: eval mode disables dropout; GLiNER decodes with
    # argmax over spans (no sampling), so output is a pure function of the
    # (model version, input) pair (NFR-2.3).
    model.eval()
    return model


def _score_to_confidence(score: float) -> Confidence:
    """Map a GLiNER span score to the detector's own confidence tier."""
    if score >= 0.85:
        return "high"
    if score >= 0.65:
        return "medium"
    return "low"


def _resolve_label_map(policy: Policy, raw: object) -> dict[str, Category]:
    """Validate a policy-supplied ``{label: category}`` override map."""
    if not isinstance(raw, dict) or not raw:
        raise policy_error(policy.id, "ML-001.labels must be a non-empty mapping")
    out: dict[str, Category] = {}
    for label, category in raw.items():
        if not isinstance(label, str) or not label.strip():
            raise policy_error(policy.id, "ML-001.labels keys must be non-empty strings")
        if not isinstance(category, str) or category not in _VALID_CATEGORIES:
            raise policy_error(
                policy.id,
                f"ML-001.labels['{label}'] must be one of {sorted(_VALID_CATEGORIES)}",
            )
        out[label.strip().lower()] = category  # type: ignore[assignment]
    return out


class GlinerPiiDetector:
    """ML-001 — GLiNER generalist PII detector."""

    rule_id: ClassVar[str] = "ML-001"
    # Nominal protocol default; each Finding's category is set from the label
    # map (a single detector spans multiple categories — see KTD4).
    category: ClassVar[Category] = "IDENTITY"

    def detect(self, doc: Document, policy: Policy) -> list[Finding]:
        model_name = _DEFAULT_MODEL
        revision: str | None = _DEFAULT_MODEL_REVISION
        score_threshold = _DEFAULT_SCORE_THRESHOLD
        label_map = dict(_DEFAULT_LABEL_MAP)
        allow_download = False

        ref = policy_override(policy, self.rule_id)
        if ref is not None:
            overrides = ref.overrides
            model_override = overrides.get("model")
            if model_override is not None:
                if not isinstance(model_override, str) or not model_override:
                    raise policy_error(policy.id, "ML-001.model must be a non-empty string")
                model_name = model_override
                # A different repo has its own history — drop the default's
                # pinned revision unless the policy pins one explicitly below.
                revision = None
            revision_override = overrides.get("revision")
            if revision_override is not None:
                if not isinstance(revision_override, str) or not revision_override:
                    raise policy_error(policy.id, "ML-001.revision must be a non-empty string")
                revision = revision_override
            allow_download_override = overrides.get("allow_download")
            if allow_download_override is not None:
                if not isinstance(allow_download_override, bool):
                    raise policy_error(policy.id, "ML-001.allow_download must be a boolean")
                allow_download = allow_download_override
            threshold_override = overrides.get("score_threshold")
            if threshold_override is not None:
                if isinstance(threshold_override, bool) or not isinstance(
                    threshold_override, int | float
                ):
                    raise policy_error(policy.id, "ML-001.score_threshold must be a number")
                if not 0.0 <= float(threshold_override) <= 1.0:
                    raise policy_error(policy.id, "ML-001.score_threshold must be in [0, 1]")
                score_threshold = float(threshold_override)
            if "labels" in overrides:
                label_map = _resolve_label_map(policy, overrides.get("labels"))

        try:
            model = _load_gliner(model_name, revision, not allow_download)
        except RuntimeError as exc:
            raise policy_error(policy.id, str(exc)) from exc

        labels = list(label_map.keys())
        out: list[Finding] = []
        for page in doc.pages:
            for block in page.blocks:
                for line in block.lines:
                    text, spans = line_text_and_offsets(line)
                    if not text.strip():
                        continue
                    entities = model.predict_entities(text, labels, threshold=score_threshold)
                    for ent in entities:
                        category = label_map.get(str(ent.get("label", "")).strip().lower())
                        if category is None:
                            continue
                        start = int(ent["start"])
                        end = int(ent["end"])
                        covered = tokens_covering(spans, start, end)
                        if not covered:
                            continue
                        ocr_conf = confidence_from_tokens(covered)
                        detector_conf = _score_to_confidence(float(ent.get("score", 1.0)))
                        out.append(
                            Finding(
                                rule_id=self.rule_id,
                                category=category,
                                bbox=union_bboxes(t.bbox for t in covered),
                                confidence=cap_confidence(detector_conf, ocr_conf),
                                matched_text=str(ent.get("text", text[start:end])),
                                page_index=page.index,
                            )
                        )
        return out
