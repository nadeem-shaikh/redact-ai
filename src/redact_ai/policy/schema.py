"""Pydantic schema for the policy YAML (BUILD_SPEC §6)."""

from __future__ import annotations

import re
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from redact_ai.models.findings import Confidence

_ID_RE = re.compile(r"^[a-z][a-z0-9-]{1,63}$")
_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.\-]+)?$")
_RULE_ID_RE = re.compile(r"^[A-Z]{2}-[0-9]{3}$")
_HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


class BlockStyle(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    kind: Literal["block"] = "block"
    color: str = "#000000"
    padding_px: int = Field(default=2, ge=0, le=64)

    @field_validator("color")
    @classmethod
    def _hex(cls, v: str) -> str:
        if not _HEX_COLOR_RE.match(v):
            raise ValueError("color must be #RRGGBB hex")
        return v.lower()


class BlurStyle(BaseModel):
    """Accepted by the schema but downgraded to ``block`` at runtime
    (BUILD_SPEC §10.2 / FR-4.5 — blur on text is reversible)."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    kind: Literal["blur"] = "blur"
    color: str = "#000000"
    padding_px: int = Field(default=2, ge=0, le=64)

    @field_validator("color")
    @classmethod
    def _hex(cls, v: str) -> str:
        if not _HEX_COLOR_RE.match(v):
            raise ValueError("color must be #RRGGBB hex")
        return v.lower()


class PixelateStyle(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    kind: Literal["pixelate"] = "pixelate"
    padding_px: int = Field(default=2, ge=0, le=64)
    # ``mean_radius_px`` is accepted for forward compatibility but is
    # ignored in v0.1 (BUILD_SPEC §10.3): we always flat-fill with the mean.
    mean_radius_px: int = Field(default=8, ge=1, le=64)


class LabelStyle(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    kind: Literal["label"] = "label"
    color: str = "#000000"
    padding_px: int = Field(default=2, ge=0, le=64)
    text_color: str = "#ffffff"

    @field_validator("color", "text_color")
    @classmethod
    def _hex(cls, v: str) -> str:
        if not _HEX_COLOR_RE.match(v):
            raise ValueError("color must be #RRGGBB hex")
        return v.lower()


RedactionStyle = Annotated[
    BlockStyle | BlurStyle | PixelateStyle | LabelStyle,
    Field(discriminator="kind"),
]


class DetectorRef(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    id: str
    enabled: bool = True
    threshold: Confidence = "low"
    overrides: dict[str, Any] = Field(default_factory=dict)

    @field_validator("id")
    @classmethod
    def _shape(cls, v: str) -> str:
        if not _RULE_ID_RE.match(v):
            raise ValueError("rule id must look like 'XX-NNN'")
        return v


class Policy(BaseModel):
    """A complete policy as loaded from YAML."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    version: str
    description: str = Field(default="", max_length=240)
    posture: Literal["strict", "lenient"] = "strict"
    verbose_report: bool = False
    redaction_style: RedactionStyle = BlockStyle()
    detectors: tuple[DetectorRef, ...]

    @field_validator("id")
    @classmethod
    def _id_shape(cls, v: str) -> str:
        if not _ID_RE.match(v):
            raise ValueError("id must be kebab-case, 2-64 chars")
        return v

    @field_validator("version")
    @classmethod
    def _semver(cls, v: str) -> str:
        if not _SEMVER_RE.match(v):
            raise ValueError("version must be semver")
        return v

    @model_validator(mode="after")
    def _no_duplicate_detectors(self) -> Policy:
        seen: set[str] = set()
        for det in self.detectors:
            if det.id in seen:
                raise ValueError(f"detector listed twice: {det.id}")
            seen.add(det.id)
        return self

    def effective_threshold(self, ref: DetectorRef) -> Confidence:
        """Apply posture bumps. ``lenient`` raises the threshold by one step (BUILD_SPEC §6.2)."""
        if self.posture == "strict":
            return ref.threshold
        if ref.threshold == "low":
            return "medium"
        if ref.threshold == "medium":
            return "high"
        return "high"

    def enabled_detectors(self) -> list[DetectorRef]:
        return [d for d in self.detectors if d.enabled]
