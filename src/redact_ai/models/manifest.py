"""Manifest schema (BUILD_SPEC §9)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from redact_ai.models.document import BBox
from redact_ai.models.findings import Category, Confidence


class FindingOut(BaseModel):
    """Public-facing finding as serialised in the manifest."""

    model_config = {"frozen": True}

    id: str
    rule_id: str
    category: Category
    bbox: BBox
    confidence: Confidence
    matched_text: str | None = None


class Stats(BaseModel):
    model_config = {"frozen": True}

    redactions_total: int = Field(ge=0)
    by_category: dict[Category, int]


class Warning(BaseModel):
    model_config = {"frozen": True}

    code: str
    message: str
    source: Literal["ingest", "ocr", "detect", "redact", "report", "http"]


class Manifest(BaseModel):
    """Top-level manifest emitted alongside the redacted image (BUILD_SPEC §9.1)."""

    model_config = {"frozen": True}

    schema_version: Literal["1"] = "1"
    policy_id: str
    policy_version: str
    runtime_version: str
    ocr_engine: str
    input_hash: str
    output_hash: str
    created_at: str
    stats: Stats
    findings: tuple[FindingOut, ...]
    warnings: tuple[Warning, ...] = ()
