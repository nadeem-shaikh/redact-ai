"""Detector registry (DETECTORS_v0.1 §Registry).

LO-002 (vehicle plates) is intentionally absent — image-content
detection is deferred to a future release.
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
    PersonNameNerDetector,
)
from redact_ai.pipeline.detect.location import GpsCoordsDetector
from redact_ai.policy.schema import Policy

REGISTRY: dict[str, type[Detector]] = {
    "ID-001": FullNameDetector,
    "ID-002": DateOfBirthDetector,
    "ID-003": GovernmentIdDetector,
    "ID-004": PassportDetector,
    "ID-005": DriverLicenceDetector,
    "ID-006": PersonNameNerDetector,
    "CO-001": EmailDetector,
    "CO-002": PhoneDetector,
    "CO-003": PostalAddressDetector,
    "FI-001": PanDetector,
    "FI-002": IbanDetector,
    "FI-003": BankAccountDetector,
    "FI-004": CvvExpiryDetector,
    "HE-001": MrnDetector,
    "HE-002": Icd10Detector,
    "HE-003": PrescriptionDetector,
    "CR-001": HighEntropyTokenDetector,
    "CR-002": SshPrivateKeyDetector,
    "CR-003": CloudKeyDetector,
    "LO-001": GpsCoordsDetector,
    "CU-001": CustomRegexDetector,
}


def build_detectors(policy: Policy) -> list[Detector]:
    """Instantiate one detector per enabled policy entry.

    Unknown rule IDs raise :class:`E_POLICY` (BUILD_SPEC §6.2).
    """
    out: list[Detector] = []
    for ref in policy.enabled_detectors():
        cls = REGISTRY.get(ref.id)
        if cls is None:
            raise policy_error(policy.id, f"unknown detector rule id: {ref.id}")
        out.append(cls())
    return out
