"""Bounding-box merge (BUILD_SPEC §11, FR-3.5).

Algorithm:

1. Sort findings by ``(category, bbox.y, bbox.x)``.
2. For each pair ``(a, b)`` with the same category, merge if
   ``iou(a, b) >= 0.30`` *or* the bboxes are within ``MERGE_GAP_PX``
   pixels on the same text line.
3. Repeat until a fixed point.

The merged finding keeps the union bbox, the *higher* confidence, and
records both rule ids in ``merged_from``.
"""

from __future__ import annotations

from redact_ai.models.findings import Finding, confidence_max

IOU_THRESHOLD: float = 0.30
MERGE_GAP_PX: int = 8

_CONFIDENCE_ORDER = {"low": 0, "medium": 1, "high": 2}


def _same_line(a: Finding, b: Finding) -> bool:
    """Approximate ``same text line``: vertical overlap covers ≥ 50% of the smaller bbox."""
    overlap = min(a.bbox.y2, b.bbox.y2) - max(a.bbox.y, b.bbox.y)
    if overlap <= 0:
        return False
    return overlap >= 0.5 * min(a.bbox.h, b.bbox.h)


def _horizontal_gap(a: Finding, b: Finding) -> int:
    if a.bbox.x2 <= b.bbox.x:
        return b.bbox.x - a.bbox.x2
    if b.bbox.x2 <= a.bbox.x:
        return a.bbox.x - b.bbox.x2
    return 0  # they overlap horizontally


def _should_merge(a: Finding, b: Finding) -> bool:
    if a.category != b.category:
        return False
    if a.page_index != b.page_index:
        return False
    if a.bbox.iou(b.bbox) >= IOU_THRESHOLD:
        return True
    if _same_line(a, b) and _horizontal_gap(a, b) <= MERGE_GAP_PX:
        return True
    return False


def _merge_pair(a: Finding, b: Finding) -> Finding:
    if _CONFIDENCE_ORDER[a.confidence] >= _CONFIDENCE_ORDER[b.confidence]:
        primary, secondary = a, b
    else:
        primary, secondary = b, a
    union = a.bbox.union(b.bbox)
    merged_ids = tuple(
        dict.fromkeys(
            (primary.rule_id, secondary.rule_id, *primary.merged_from, *secondary.merged_from)
        )
    )
    merged_from = tuple(rid for rid in merged_ids if rid != primary.rule_id)
    matched_text = primary.matched_text or secondary.matched_text
    return Finding(
        rule_id=primary.rule_id,
        category=primary.category,
        bbox=union,
        confidence=confidence_max(a.confidence, b.confidence),
        matched_text=matched_text,
        page_index=primary.page_index,
        merged_from=merged_from,
    )


def merge_findings(findings: list[Finding]) -> list[Finding]:
    """Return the fixed-point merged list (BUILD_SPEC §11)."""
    items = sorted(
        findings,
        key=lambda f: (f.category, f.page_index, f.bbox.y, f.bbox.x, f.rule_id),
    )
    while True:
        merged = False
        out: list[Finding] = []
        consumed: set[int] = set()
        for i, a in enumerate(items):
            if i in consumed:
                continue
            current = a
            for j in range(i + 1, len(items)):
                if j in consumed:
                    continue
                b = items[j]
                if _should_merge(current, b):
                    current = _merge_pair(current, b)
                    consumed.add(j)
                    merged = True
            out.append(current)
        items = sorted(
            out, key=lambda f: (f.category, f.page_index, f.bbox.y, f.bbox.x, f.rule_id)
        )
        if not merged:
            return items
