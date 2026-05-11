"""Manifest builder (BUILD_SPEC §9)."""

from __future__ import annotations

from collections import Counter

from redact_ai.models.findings import Category, Finding
from redact_ai.models.manifest import FindingOut, Manifest, Stats, Warning
from redact_ai.policy.schema import Policy


def build_manifest(
    *,
    policy: Policy,
    runtime_version: str,
    ocr_engine: str,
    input_hash: str,
    output_hash: str,
    created_at: str,
    findings: list[Finding],
    warnings: list[Warning],
    include_matched_text: bool,
) -> Manifest:
    """Compose the manifest. Findings are sorted by (page, y, x, rule_id)."""
    sorted_findings = sorted(
        findings,
        key=lambda f: (f.page_index, f.bbox.y, f.bbox.x, f.rule_id),
    )
    out_findings: list[FindingOut] = []
    counter_by_rule: Counter[str] = Counter()
    for f in sorted_findings:
        seq = counter_by_rule[f.rule_id]
        counter_by_rule[f.rule_id] += 1
        out_findings.append(
            FindingOut(
                id=f"f-{f.rule_id}-{seq}",
                rule_id=f.rule_id,
                category=f.category,
                bbox=f.bbox,
                confidence=f.confidence,
                matched_text=f.matched_text if include_matched_text else None,
            )
        )
    stats = Stats(
        redactions_total=len(out_findings),
        by_category=_count_by_category(out_findings),
    )
    return Manifest(
        schema_version="1",
        policy_id=policy.id,
        policy_version=policy.version,
        runtime_version=runtime_version,
        ocr_engine=ocr_engine,
        input_hash=input_hash,
        output_hash=output_hash,
        created_at=created_at,
        stats=stats,
        findings=tuple(out_findings),
        warnings=tuple(warnings),
    )


def _count_by_category(findings: list[FindingOut]) -> dict[Category, int]:
    counter: Counter[Category] = Counter()
    for f in findings:
        counter[f.category] += 1
    return dict(sorted(counter.items()))
