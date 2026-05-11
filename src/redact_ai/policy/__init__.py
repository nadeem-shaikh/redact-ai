"""Policy schema and loader (BUILD_SPEC §6)."""

from redact_ai.policy.loader import builtin_policies, load_default_policy, load_policy
from redact_ai.policy.schema import (
    BlockStyle,
    DetectorRef,
    LabelStyle,
    PixelateStyle,
    Policy,
    RedactionStyle,
)

__all__ = [
    "BlockStyle",
    "DetectorRef",
    "LabelStyle",
    "PixelateStyle",
    "Policy",
    "RedactionStyle",
    "builtin_policies",
    "load_default_policy",
    "load_policy",
]
