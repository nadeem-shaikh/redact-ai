"""Detector registry (DETECTORS_v0.1 §Registry).

ID-007 (face photos) ships in v0.1 per ADR-012. LO-002 (vehicle
plates) remains absent — that specific image-content detector is
still deferred.
"""

from __future__ import annotations

from redact_ai.errors import policy_error
from redact_ai.pipeline.detect.base import Detector
from redact_ai.pipeline.detect.contact import (
    EmailDetector,
    PhoneDetector,
    PostalAddressDetector,
)
from redact_ai.pipeline.detect.credentials import (
    CloudKeyDetector,
    HighEntropyTokenDetector,
    SshPrivateKeyDetector,
)
from redact_ai.pipeline.detect.custom import CustomRegexDetector
from redact_ai.pipeline.detect.financial import (
    BankAccountDetector,
    CvvExpiryDetector,
    IbanDetector,
    MaskedAccountDetector,
    PanDetector,
)
from redact_ai.pipeline.detect.health import (
    Icd10Detector,
    MrnDetector,
    PrescriptionDetector,
)
from redact_ai.pipeline.detect.identity import (
    DateOfBirthDetector,
    DriverLicenceDetector,
    FullNameDetector,
    GovernmentIdDetector,
    PassportDetector,
    PaymentRecipientNameDetector,
    PersonNameNerDetector,
)
from redact_ai.pipeline.detect.location import GpsCoordsDetector
from redact_ai.pipeline.detect.ner_gliner import GlinerPiiDetector
from redact_ai.pipeline.detect.ner_openmed import OpenMedPiiDetector
from redact_ai.pipeline.detect.vision import VisionDetector
from redact_ai.pipeline.detect.vision.face import FacePhotoDetector
from redact_ai.policy.schema import Policy

REGISTRY: dict[str, type[Detector]] = {
    "ID-001": FullNameDetector,
    "ID-002": DateOfBirthDetector,
    "ID-003": GovernmentIdDetector,
    "ID-004": PassportDetector,
    "ID-005": DriverLicenceDetector,
    "ID-006": PersonNameNerDetector,
    "ID-008": PaymentRecipientNameDetector,
    "CO-001": EmailDetector,
    "CO-002": PhoneDetector,
    "CO-003": PostalAddressDetector,
    "FI-001": PanDetector,
    "FI-002": IbanDetector,
    "FI-003": BankAccountDetector,
    "FI-004": CvvExpiryDetector,
    "FI-005": MaskedAccountDetector,
    "HE-001": MrnDetector,
    "HE-002": Icd10Detector,
    "HE-003": PrescriptionDetector,
    "CR-001": HighEntropyTokenDetector,
    "CR-002": SshPrivateKeyDetector,
    "CR-003": CloudKeyDetector,
    "LO-001": GpsCoordsDetector,
    "CU-001": CustomRegexDetector,
    # ML ENGINE — optional strong PII engine (ADR-013). Disabled by default;
    # ships in the redact-ai[strong] extra. The module imports gliner lazily,
    # so registering it here does not pull torch into a base install.
    "ML-001": GlinerPiiDetector,
    # ML-002 — OpenMed strong PHI engine (complements ML-001). Same optional
    # extra, same lazy-import discipline; transformers is imported only when
    # the detector actually runs.
    "ML-002": OpenMedPiiDetector,
}

VISION_REGISTRY: dict[str, type[VisionDetector]] = {
    "ID-007": FacePhotoDetector,
}


def build_detectors(policy: Policy) -> list[Detector]:
    """Instantiate one text detector per enabled policy entry.

    Unknown rule IDs raise :class:`E_POLICY` (BUILD_SPEC §6.2). Vision
    rule IDs (those in :data:`VISION_REGISTRY`) are skipped here — the
    pipeline orchestrator builds them via :func:`build_vision_detectors`.
    """
    out: list[Detector] = []
    for ref in policy.enabled_detectors():
        if ref.id in VISION_REGISTRY:
            continue
        cls = REGISTRY.get(ref.id)
        if cls is None:
            raise policy_error(policy.id, f"unknown detector rule id: {ref.id}")
        out.append(cls())
    return out


def build_vision_detectors(policy: Policy) -> list[VisionDetector]:
    """Instantiate one vision detector per enabled policy entry."""
    out: list[VisionDetector] = []
    for ref in policy.enabled_detectors():
        cls = VISION_REGISTRY.get(ref.id)
        if cls is None:
            continue
        out.append(cls())
    return out
