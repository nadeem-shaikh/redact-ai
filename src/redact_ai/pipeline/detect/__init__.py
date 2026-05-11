"""Detector engine package (DETECTORS_v0.1)."""

from redact_ai.pipeline.detect.base import Detector
from redact_ai.pipeline.detect.registry import REGISTRY, build_detectors

__all__ = ["Detector", "REGISTRY", "build_detectors"]
