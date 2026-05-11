"""TC-001..TC-010 golden tests (BUILD_SPEC §16, TEST_CASES_v0.1)."""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

import pytest
from PIL import Image

from redact_ai import redact
from redact_ai.errors import RedactError
from redact_ai.policy.loader import load_default_policy

INPUTS = Path(__file__).parent / "inputs"
EXPECTED = Path(__file__).parent / "expected"


def _expected(name: str) -> dict:
    return json.loads((EXPECTED / f"{name}.json").read_text(encoding="utf-8"))


def _run(name: str):
    data = (INPUTS / f"{name}.png").read_bytes()
    return data, redact(data, "image/png", load_default_policy())


def _assert_matches(name: str, manifest, warnings) -> None:
    expected = _expected(name)
    rule_ids = [f.rule_id for f in manifest.findings]
    for required in expected.get("rule_ids_required", []):
        assert required in rule_ids, f"{name}: missing rule {required} (got {rule_ids})"
    for forbidden in expected.get("rule_ids_forbidden", []):
        assert forbidden not in rule_ids, f"{name}: forbidden rule {forbidden} present"
    by_cat = dict(manifest.stats.by_category)
    for cat, n in expected.get("by_category_min", {}).items():
        assert by_cat.get(cat, 0) >= n, f"{name}: expected ≥{n} {cat}, got {by_cat}"
    assert manifest.stats.redactions_total >= expected.get("min_total", 0)
    if "max_total" in expected:
        assert manifest.stats.redactions_total <= expected["max_total"]
    warning_codes = {w.code for w in warnings}
    for code in expected.get("warnings_required", []):
        assert code in warning_codes, f"{name}: missing warning {code}"
    for code in expected.get("warnings_forbidden", []):
        assert code not in warning_codes, f"{name}: forbidden warning {code} present"


@pytest.mark.parametrize(
    "name",
    [
        "TC-001",
        "TC-002",
        "TC-003",
        "TC-004",
        "TC-005",
        "TC-006",
        "TC-007",
        "TC-008",
        "TC-009",
    ],
)
def test_golden_manifest(name: str) -> None:
    _, result = _run(name)
    _assert_matches(name, result.manifest, result.warnings)


def test_tc_010_unsupported_format_rejected() -> None:
    """TC-010 — empty / unsupported input must fail with ``E_INPUT_FORMAT``."""
    data = (INPUTS / "TC-010.bmp").read_bytes()
    with pytest.raises(RedactError) as exc:
        redact(data, "image/bmp", load_default_policy())
    assert exc.value.code == "E_INPUT_FORMAT"
    assert exc.value.hint


def test_redacted_pixel_block_is_solid_for_tc_001() -> None:
    """BUILD_SPEC §16.4 — masked regions must contain no original pixels.

    For ``style=block``, every projected bbox in the output image must be
    entirely the configured fill colour.
    """
    _, result = _run("TC-001")
    image = Image.open(io.BytesIO(result.image.bytes)).convert("RGB")
    expected = (0, 0, 0)
    for finding in result.image.projected_findings:
        crop = image.crop((finding.bbox.x, finding.bbox.y, finding.bbox.x2, finding.bbox.y2))
        pixels = set(crop.getdata())
        assert pixels == {expected}, f"{finding.rule_id}: leaked pixels {pixels - {expected}}"


def test_dt_001_byte_identical_outputs() -> None:
    """DT-001 — two runs on the same input produce byte-identical output
    and an equivalent manifest (BUILD_SPEC §9.2)."""
    data = (INPUTS / "TC-001.png").read_bytes()
    policy = load_default_policy()
    a = redact(data, "image/png", policy)
    b = redact(data, "image/png", policy)
    assert hashlib.sha256(a.image.bytes).hexdigest() == hashlib.sha256(b.image.bytes).hexdigest()
    assert _equivalent_manifest(a.manifest, b.manifest)


def _equivalent_manifest(a, b) -> bool:
    dump_a = a.model_dump(mode="json")
    dump_b = b.model_dump(mode="json")
    dump_a.pop("created_at", None)
    dump_b.pop("created_at", None)
    return dump_a == dump_b


def test_manifest_example_shape() -> None:
    """The TC-001 manifest matches ``examples/manifest_example.json`` in
    shape: same top-level keys, same ``stats`` keys, same ``findings``
    item keys."""
    repo_root = Path(__file__).resolve().parents[2]
    example = json.loads(
        (repo_root / "examples" / "manifest_example.json").read_text(encoding="utf-8")
    )
    _, result = _run("TC-001")
    manifest = result.manifest.model_dump(mode="json")
    assert set(manifest.keys()) == set(example.keys())
    assert set(manifest["stats"].keys()) == set(example["stats"].keys())
    assert manifest["findings"], "TC-001 must produce at least one finding"
    if example["findings"]:
        example_keys = set(example["findings"][0].keys())
        # Optional ``matched_text`` is present only in verbose mode.
        for finding in manifest["findings"]:
            keys = set(finding.keys()) - {"matched_text"}
            assert keys == example_keys - {"matched_text"}
