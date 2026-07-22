---
title: GLiNER Strong PII Engine - Plan
type: feat
date: 2026-07-21
artifact_contract: ce-unified-plan/v1
artifact_readiness: implementation-ready
product_contract_source: ce-plan-bootstrap
execution: code
---

# GLiNER Strong PII Engine - Plan

## Goal Capsule

Add a strong, ML-based detection engine to redact-ai so entities the current
regex + spaCy-`md` engine misses get redacted. Ship it as an **optional extra**
(`redact-ai[strong]`) that plugs into the existing detector registry as rule
`ML-001`, disabled by default.

- **Authority hierarchy:** ADR-002 (local-first, no runtime network) and
  NFR-2.3 (determinism) are non-negotiable and outrank recall gains. The base
  install must stay lean (ADR-011 footprint concern).
- **Stop conditions:** `ML-001` detector exists, is registered, is deterministic,
  fails closed when the extra is absent, has passing mocked unit tests, and the
  full existing suite stays green. Real-model validation is explicitly deferred
  to a network-enabled environment (see Risks).

## Product Contract

**Product Contract preservation:** new plan, `ce-plan-bootstrap` — no upstream
brainstorm to preserve.

### Summary

redact-ai detects PII via hand-written regex/dictionary/label rules plus spaCy
`en_core_web_md` (PERSON-only, en-US). Recall is structurally bounded to what
those rules encode. Integrate **GLiNER** — the current best OSS PII NER (a
deterministic transformer encoder that scores an arbitrary label schema in one
forward pass) — as a new detector that complements, not replaces, the
deterministic detectors. It runs on-device, on CPU, and maps model spans back to
OCR tokens through the same helpers the spaCy detector (`ID-006`) already uses.

### Problem Frame

Two failure modes motivate this:

1. **Weak recall.** Anything not matching a rule or the `md` model is missed —
   non-Western names, unlabeled IDs, addresses without a street-suffix, PHI in
   prose.
2. **Structural rule-bound ceiling.** Adding more regex chases the long tail
   forever. A generalist NER model raises the floor across every category at
   once.

The engine choice must not weaken the two guarantees that define the product:
local-first operation (ADR-002) and deterministic, reproducible output
(NFR-2.3).

### Requirements

Engine and detection:
- R1. A new text detector, rule id `ML-001`, implements the `Detector` protocol
  and emits `Finding`s for PII spans found by a GLiNER model.
- R2. `ML-001` maps each GLiNER entity label to a redact-ai `Category` via a
  configurable label→category map, and maps model span offsets to OCR tokens
  with the existing `line_text_and_offsets` / `tokens_covering` helpers.
- R3. The model runs deterministically: evaluation mode, greedy/argmax decoding,
  no sampling — byte-identical findings for a fixed model version + input
  (NFR-2.3).
- R4. The model name, per-entity score threshold, and label→category map are
  overridable via the policy `overrides` block on the `ML-001` detector.

Packaging and safety:
- R5. The engine ships behind an optional extra `redact-ai[strong]`; the base
  install and its dependency footprint are unchanged.
- R6. `ML-001` is present but `enabled: false` in the shipped default policy, so
  default runs never import GLiNER.
- R7. When `ML-001` is enabled but the `gliner` package or the model is
  unavailable, the detector fails closed with `E_POLICY` and an actionable hint
  (mirrors `ID-006`, ADR-005).
- R8. No runtime network call on the redaction hot path — the model resolves
  from the local cache; fetching is an install/first-load step (ADR-002).

Traceability and docs:
- R9. `ML-001` findings carry the model version so the manifest can record it
  for reproducibility (parity with the spaCy model version note).
- R10. A ready-to-use example policy enables the engine; `docs/DETECTORS_v0.1.md`
  documents `ML-001`; an ADR records the decision.

### Scope Boundaries

- In scope: the `ML-001` detector, its registration, packaging extra, default +
  example policy, mocked tests, and docs/ADR.
- Deferred: replacing spaCy `ID-006` or any regex detector (the deterministic
  detectors stay authoritative for structured IDs — Luhn PANs, IBAN mod-97,
  cloud-key prefixes — where regex+checksum beats ML). Real-model benchmark
  tuning. Fixing the pre-existing `en_core_web_md` install-fragility (tracked
  separately; not selected for this change).

### Sources

- Current engine: `src/redact_ai/pipeline/detect/identity.py` (`ID-006`
  `PersonNameNerDetector`, the closest integration analogue).
- Detector protocol + helpers: `src/redact_ai/pipeline/detect/base.py`.
- Registry: `src/redact_ai/pipeline/detect/registry.py`.
- Findings model: `src/redact_ai/models/findings.py` (`Category`, `Confidence`,
  `Finding`).
- Policy schema: `src/redact_ai/policy/schema.py` (rule-id regex
  `^[A-Z]{2}-[0-9]{3}$`; `DetectorRef.overrides`).
- Default policy (two synced copies): `examples/default_policy.yaml` and
  `src/redact_ai/resources/default_policy.yaml` (parity asserted by
  `tests/unit/policy/test_loader.py::test_policy_yaml_matches_shipped`).
- Test pattern: `tests/unit/detect/test_id_006.py`, `tests/unit/detect/_helpers.py`
  (`make_doc`).
- Engine research: GLiNER (`urchade/GLiNER`, `gliner` on PyPI) and GLiNER2-PII
  (Fastino/Pioneer AI) — SOTA span-F1 on the SPY PII benchmark; deterministic
  single-pass encoder; runs on CPU.

## Planning Contract

### Key Technical Decisions

- KTD1. **Engine = GLiNER, integrated directly as a detector** — not Microsoft
  Presidio. redact-ai already owns orchestration (registry + merge + thresholds),
  so Presidio's recognizer/orchestration layer is redundant weight; GLiNER is the
  model Presidio would wrap anyway.
  (session-settled: user-directed — chosen over Presidio/OpenMed after "find the
  best OSS": GLiNER2-PII leads the SPY benchmark and is CPU/deterministic.)
- KTD2. **Default model `urchade/gliner_multi_pii-v1`; GLiNER2-PII overridable.**
  The stable `gliner` runtime + `gliner_multi_pii-v1` is the safe, proven default;
  GLiNER2-PII (SOTA) may need a newer runtime, so expose it via `overrides.model`
  rather than pinning it as default. Model is policy-overridable, so this is not a
  one-way door.
  (session-settled: user-approved — GLiNER2-PII is by Fastino, not Nvidia;
  `nvidia/gliner-PII` is a separate, weaker model.)
- KTD3. **Optional extra, disabled by default** (R5/R6). The engine adds
  torch/transformers/huggingface_hub + a ~200–300 MB model; forcing that on every
  install violates the ADR-011 footprint constraint. Opt-in via
  `pip install redact-ai[strong]` + enabling `ML-001` in policy.
  (session-settled: user-directed — chose "Optional extra" over "New default
  engine".)
- KTD4. **Single rule id `ML-001`, per-finding `Category` from the label map.**
  The rule-id regex forbids a cross-category id; `ML-001` is the policy handle
  (one threshold, one enable switch) while each `Finding.category` is set from the
  label map so downstream merge/report/threshold logic works unchanged. Nominal
  ClassVar `category = "IDENTITY"` satisfies the protocol.
- KTD5. **Per-line inference, mirroring `ID-006`.** Run the model on each OCR
  line and map offsets with `tokens_covering`. Keeps the token round-trip
  identical to the proven spaCy path; block-level context is a deferred
  optimization.
- KTD6. **Determinism via eval mode + argmax; lazy import.** `gliner` is imported
  only inside the cached loader, so registering the detector never pulls torch
  unless `ML-001` actually runs (protects base-install import time and R6).

### High-Level Technical Design

```text
OCR Document ──► ML-001.detect(doc, policy)
                    │  read overrides (model, score_threshold, labels)
                    │  _load_gliner(model)  ── lazy import gliner; eval(); lru_cache
                    ▼
              for each line: text, spans = line_text_and_offsets(line)
                    │  ents = model.predict_entities(text, labels, threshold)
                    ▼
              per ent: category = label_map[ent.label]
                       covered  = tokens_covering(spans, ent.start, ent.end)
                       conf     = cap_confidence(score→conf, ocr_conf)
                    ▼
              Finding(rule_id="ML-001", category, bbox=union(covered), ...)
                    │
                    └► existing merge → oversize guard → thresholds → redact
```

### Assumptions

- A1. `gliner`'s `GLiNER.from_pretrained(model).predict_entities(text, labels,
  threshold=...)` returns dicts with `start`, `end`, `text`, `label`, `score`
  (documented stable API). Verified against a mock; real-model verification
  deferred (Risks).
- A2. For strict ADR-002, the model is pre-fetched at install/first-load and
  served from the huggingface cache thereafter; the redaction hot path does no
  network I/O. Documented in the extra's install note.

### Sequencing

U1 → U2 → U3 → U4 → U5 → U6 (each builds on the prior; U6 docs can proceed once
U1–U3 land).

## Implementation Units

### U1. GLiNER detector module (`ML-001`)

- Goal: implement `GlinerPiiDetector` with a cached, lazily-imported model
  loader, deterministic inference, label→category mapping, and fail-closed
  behavior.
- Requirements: R1, R2, R3, R4, R7, R8, R9.
- Files: `src/redact_ai/pipeline/detect/ner_gliner.py` (new).
- Approach: follow `PersonNameNerDetector` (`ID-006`) structure. `_load_gliner`
  (`lru_cache`) imports `gliner` inside the function, calls `from_pretrained`,
  `.eval()`, raises `RuntimeError` with an install hint on `ImportError` or load
  failure. `detect` reads `overrides` (model / score_threshold / labels via
  `policy_override`), validates them (raise `policy_error` on bad input), runs
  per line, maps score→confidence (`>=0.85` high, `>=0.65` medium, else low),
  capped by `confidence_from_tokens`. Default label map covers person, DOB,
  passport/DL/SSN/national-id/tax-id → IDENTITY; email/phone/address → CONTACT;
  credit-card/bank-account/iban → FINANCIAL; MRN/health-condition → HEALTH;
  api-key/password/secret → CREDENTIALS; gps → LOCATION. Expose `model_version`
  on findings via a helper for R9.
- Test scenarios (mock `_load_gliner` to return a fake with `predict_entities`):
  - person span → one IDENTITY finding, bbox = union of covered tokens.
  - email span → CONTACT; credit-card span → FINANCIAL (category mapping).
  - score 0.9 → high; 0.7 → medium; 0.5 → low (before OCR cap).
  - low OCR-confidence tokens cap the finding confidence down.
  - empty/whitespace line → no call / no finding.
  - unknown label from model → skipped, no finding.
  - `gliner` not importable → `RedactError` (E_POLICY) fail-closed.
  - bad override (`model: ""`, `score_threshold: 2`) → `RedactError`.
- Verification: `pytest tests/unit/detect/test_ml_001.py`.

### U2. Register `ML-001` in the detector registry

- Goal: make `ML-001` buildable from policy.
- Requirements: R1, R6.
- Files: `src/redact_ai/pipeline/detect/registry.py`.
- Approach: import `GlinerPiiDetector`, add `"ML-001": GlinerPiiDetector` to
  `REGISTRY`. Import stays cheap (no torch) because the module only imports
  `gliner` lazily.
- Test scenarios: `build_detectors` on a policy enabling `ML-001` returns the
  detector; disabled → not built.
- Verification: `pytest tests/unit/detect -q`.

### U3. Default policy entry (disabled)

- Goal: register `ML-001` as a known, disabled detector so the schema accepts it
  and default runs never touch GLiNER.
- Requirements: R6.
- Files: `examples/default_policy.yaml` and
  `src/redact_ai/resources/default_policy.yaml` (edit both identically).
- Approach: add an `ML-001` block under a new `# --- ML ENGINE (optional extra) ---`
  comment, `enabled: false`, `threshold: low`, with a note pointing at
  `redact-ai[strong]`.
- Test scenarios: `test_policy_yaml_matches_shipped` stays green; loader parses;
  `ML-001` present and disabled.
- Verification: `pytest tests/unit/policy -q`.

### U4. Packaging: `redact-ai[strong]` extra

- Goal: pull the GLiNER runtime only when the user opts in.
- Requirements: R5.
- Files: `pyproject.toml`.
- Approach: add `strong = ["gliner==<pinned>"]` under
  `[project.optional-dependencies]` (gliner pulls torch/transformers/hf-hub
  transitively). Mirror the existing `ocr-paddle` extra's shape. Add a short note
  that the model is fetched on first load and cached (A2).
- Test scenarios: n/a (packaging); `pip install -e .` base still resolves.
- Verification: base editable install unaffected; extra key present.

### U5. Example strong policy

- Goal: give users a one-file way to run the strong engine.
- Requirements: R10.
- Files: `examples/strong_policy.yaml` (new).
- Approach: copy the default policy, set `ML-001` `enabled: true`, `id: strong`,
  with a header comment: requires `pip install redact-ai[strong]`.
- Test scenarios: `load_policy("examples/strong_policy.yaml")` parses and
  `ML-001` is enabled.
- Verification: `pytest tests/unit/policy -q`.

### U6. Docs + ADR

- Goal: document the engine and record the decision.
- Requirements: R10.
- Files: `docs/DETECTORS_v0.1.md` (add `ML-001` section + registry note),
  `docs/DECISIONS.md` (add `ADR-013 — GLiNER optional strong PII engine`),
  optional short note in `README.md`.
- Approach: describe approach, engine, overrides, determinism, install-time model
  fetch, and the complement-not-replace stance vs. regex/checksum detectors.
- Test scenarios: n/a.
- Verification: docs render; cross-references resolve.

## Verification Contract

- `python3 -m pytest tests/unit/detect -q` — detector suite incl. new
  `test_ml_001.py`; existing 77 pass, spaCy tests still skip (model unavailable
  in this env).
- `python3 -m pytest tests/unit/policy -q` — policy parity + parsing.
- `python3 -m pytest -q` — full suite green (Tesseract-dependent OCR/golden
  tests may skip in this env; note any skips honestly).
- `ruff check src tests` and `mypy src` — lint + types clean for new code.
- Real-model behavioral check (`gliner_multi_pii-v1` actually redacting a
  screenshot) is **deferred** to a network-enabled environment — call it out, do
  not claim it as done.

## Definition of Done

Global:
- `ML-001` implemented, registered, disabled-by-default, fails closed without the
  extra, deterministic.
- Mocked unit tests pass; full existing suite stays green (skips reported, not
  hidden).
- `ruff` + `mypy` clean on new/changed files.
- Docs + ADR-013 landed; example strong policy present.
- No abandoned/experimental code left in the diff.

Per-unit: each U-ID's Test Scenarios pass and its Verification command is green.

## Risks & Dependencies

- Risk: **No real-model validation in this environment.** GitHub + Hugging Face
  model downloads are blocked here (403), so tests use a mocked model; the GLiNER
  API shape (A1) is verified only against the mock. Mitigation: code to the
  documented stable `gliner` API; gate the real run behind the extra; flag the
  deferred validation in the Verification Contract and the PR.
- Risk: **Determinism across hardware/threads.** Transformer float ops can vary
  across CPUs/BLAS thread counts. Mitigation: eval mode + argmax gets logical
  determinism; document CPU + pinned-thread guidance and record model version in
  the manifest (R9). Prefer the ONNX runtime path in a follow-up if byte-identity
  matters across machines.
- Risk: **Footprint** if a user misreads the extra as required. Mitigation:
  disabled-by-default + explicit install note.
- Dependency: `gliner` (PyPI) + its torch/transformers/hf-hub chain — only under
  the `strong` extra.
