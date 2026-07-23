# DECISIONS — redact-ai

> Architecture Decision Log (ADL). Append-only record of significant
> design choices. Each entry follows a lightweight ADR format.

Entry template:

```text
## ADR-NNN — <Title>

- **Date:** YYYY-MM-DD
- **Status:** Proposed | Accepted | Superseded by ADR-XXX | Deprecated
- **Context:** What forces are at play?
- **Decision:** What did we choose?
- **Consequences:** Trade-offs and follow-ups.
```

---

## ADR-001 — Image-first as the primary input modality

- **Date:** 2026-05-07
- **Status:** Accepted
- **Context:** Most existing PII tools focus on plain text. The most
  natural unit of "stuff users paste into AI tools" is a screenshot,
  and image-based redaction is materially harder than text.
- **Decision:** `redact-ai` treats images (screenshots, photos, scans)
  as the primary input. Text-only flows are a future convenience layer
  on top of the image pipeline, not a separate product.
- **Consequences:**
  - Requires an OCR + layout pipeline from day one.
  - Output fidelity (preserved layout, masked pixels) becomes a core
    correctness concern.
  - A pure-text mode can still emerge later as a thin adapter.

---

## ADR-002 — Local-first by default

- **Date:** 2026-05-07
- **Status:** Accepted
- **Context:** A privacy tool that calls home contradicts itself.
  Users will not trust a redactor whose default sends their data
  somewhere.
- **Decision:** The default pipeline runs entirely on-device with no
  outbound network calls. Optional cloud-assisted detectors require
  explicit, per-invocation user consent.
- **Consequences:**
  - Constrains the choice of OCR engines and models.
  - Forces clear UX around any non-default cloud feature.
  - Simplifies the threat model.

---

## ADR-003 — Technology-agnostic core specification

- **Date:** 2026-05-07
- **Status:** Accepted
- **Context:** The project is in a documentation phase. Locking in a
  language or framework prematurely would bias contributor onboarding
  and architectural choices.
- **Decision:** All v0.1 specs are written without prescribing a
  language, framework, or specific OCR engine. Concrete tech is chosen
  when a reference implementation begins.
- **Consequences:**
  - Slightly more abstract documents.
  - Multiple implementations remain viable.
  - Adapter contracts must be explicit.

---

## ADR-004 — Pipeline modularity (Ingest → OCR → Detect → Redact → Report)

- **Date:** 2026-05-07
- **Status:** Accepted
- **Context:** Detection and redaction will evolve at different
  speeds. We want detectors to be replaceable without rewriting the
  redactor, and vice versa.
- **Decision:** Adopt a five-stage pipeline with explicit inter-stage
  contracts described in
  [`ARCHITECTURE_v0.1.md`](./ARCHITECTURE_v0.1.md).
- **Consequences:**
  - Higher up-front design cost.
  - Easier extensibility (new detectors, new redaction styles).
  - Clear boundaries for testing.

---

## ADR-005 — Fail closed on uncertainty

- **Date:** 2026-05-07
- **Status:** Accepted
- **Context:** A redactor that emits partial output on failure is
  worse than no output, because it gives users a false sense of
  safety.
- **Decision:** On any failure that risks leaking sensitive content,
  `redact-ai` produces no output image and surfaces a clear error.
- **Consequences:**
  - Higher visible failure rate during development.
  - Stronger safety guarantees in production.

---

## ADR-006 — Manifest excludes raw matched text by default

- **Date:** 2026-05-07
- **Status:** Accepted
- **Context:** The redaction manifest is a useful artefact for audit
  and review, but if it includes the raw matched values it becomes a
  secondary leak channel.
- **Decision:** Manifests include category, rule ID, location, and
  confidence — but **not** raw matched text. A `verbose_report` flag
  exists for power users who explicitly opt in.
- **Consequences:**
  - Default manifests are safe to share.
  - Verbose mode requires its own UX warnings.

---

## ADR-007 — v0.1 surface is a local web UI

- **Date:** 2026-05-07
- **Status:** Accepted
- **Context:** [`UX_FLOW_v0.1.md`](./UX_FLOW_v0.1.md) and
  [`PRODUCT_v0.1.md`](./PRODUCT_v0.1.md) both left the v0.1 entry
  point open ("CLI, desktop, or both?"). Pure-Python ingestion of
  screenshots is OS-fragmented across clipboard, drag-drop, and
  share-sheet integrations, and a CLI alone excludes non-power-users
  from the most common moment ("I just took a screenshot — clean it
  before I paste it into ChatGPT"). A local web UI gives every user
  a familiar drag-and-drop canvas (the browser they already have
  open) without compromising the local-first principle.
- **Decision:** The v0.1 user-visible surface is a **local web UI** —
  a Python server bound to `127.0.0.1` plus a single static
  drag-and-drop HTML page served from the same process. The CLI is
  retained for power users and ships as a v0.2 surface (see
  [`ROADMAP.md`](./ROADMAP.md)).
- **Consequences:**
  - Adds a small, well-bounded HTTP attack surface that lives
    entirely on the loopback interface; hardening is captured in
    [`SECURITY_v0.1.md`](./SECURITY_v0.1.md).
  - HTTP roundtrip is included in the end-to-end latency budget
    (see [`NON_FUNCTIONAL_REQUIREMENTS_v0.1.md`](./NON_FUNCTIONAL_REQUIREMENTS_v0.1.md), NFR-1.1).
  - FastAPI (or an equivalent minimal Python web framework) joins
    the recommended MVP stack in
    [`TECH_STACK_OPTIONS_v0.1.md`](./TECH_STACK_OPTIONS_v0.1.md).
  - **Does not** revisit ADR-001 (image-first remains the v0.1 input
    modality) or ADR-002 (the localhost loopback is on-device; no
    user content crosses the network boundary).

---

## ADR-008 — PaddleOCR as the v0.1 default OCR engine

- **Date:** 2026-05-10
- **Status:** Accepted
- **Context:**
  [`TECH_STACK_OPTIONS_v0.1.md`](./TECH_STACK_OPTIONS_v0.1.md) as
  originally drafted positioned Tesseract as the v0.1 baseline OCR
  engine and PaddleOCR as an opt-in `[ocr-paddle]` extras install.
  While drafting [`TECHNICAL_DESIGN_v0.1.md`](./TECHNICAL_DESIGN_v0.1.md)
  the team identified two reasons to invert this choice for v0.1:
  1. **Screenshot accuracy.** `redact-ai`'s primary input
     (ADR-001) is screenshots — anti-aliased UI text at 96–144 DPI,
     mixed fonts, low contrast, and emoji. Published benchmarks
     and prior team experience put Tesseract default-config recall
     on this regime materially below PaddleOCR-PP-OCRv4 (a
     scene-dependent gap, but typically large enough to risk the
     NFR-2.1 95% recall floor).
  2. **Detection coverage is bounded by OCR.** The v0.1 detectors
     are deterministic regex/dictionary detectors (TECHNICAL_DESIGN
     §7) operating on OCR output. Recall ceiling is the OCR's
     ceiling; weak OCR cannot be compensated for by detector
     tuning. In a redactor, missed PII is a privacy failure
     (ADR-005), not a quality issue.
- **Decision:** PaddleOCR is the default OCR engine for v0.1.
  Tesseract is demoted to an opt-in `[ocr-tesseract]` extras
  install for environments where the `paddlepaddle` runtime is
  unavailable (notably some Windows / arm64 configurations).
- **Consequences:**
  - Default install footprint grows from ~50–80 MB to ~500 MB–1 GB.
  - CI matrix complexity increases on Windows and arm64 because of
    `paddlepaddle` wheel availability gaps; a documented
    Tesseract-fallback path remains supported.
  - The `redact-ai prefetch-models` subcommand
    (TECHNICAL_DESIGN §10.3) becomes the documented one-time
    post-install step for the default engine.
  - The §15 "Recall < 95% on the benchmark" trigger in
    TECHNICAL_DESIGN remains the project's empirical check on this
    decision: an in-tree benchmark of Tesseract vs PaddleOCR
    against the curated corpus is a v0.1 release-gate item (DoD
    §16). If Tesseract meets NFR-2.1 within a meaningful margin
    on the curated corpus, this ADR is revisited and the default
    reverted in favour of the smaller install footprint.
  - **Supersedes** the corresponding Tesseract-default framing in
    [`TECH_STACK_OPTIONS_v0.1.md`](./TECH_STACK_OPTIONS_v0.1.md)
    (§A.1 OCR row, §A.3 distribution con, §Operational
    Considerations dependency-footprint paragraph, §Final
    Recommendation reasoning, and the corresponding open
    question). That document is updated in the same change as
    this ADR; the two are intended to ship together.

---

## ADR-009 — Default policy posture is "strict"

- **Date:** 2026-05-10
- **Status:** Accepted
- **Context:**
  [`TECH_STACK_OPTIONS_v0.1.md`](./TECH_STACK_OPTIONS_v0.1.md) and
  [`UX_FLOW_v0.1.md`](./UX_FLOW_v0.1.md) left "strict vs lenient
  default" open. The product's stated bias is "false negatives are
  a safety failure, false positives are a UX failure"
  ([`REDACTION_RULES_v0.1.md`](./REDACTION_RULES_v0.1.md) §4).
- **Decision:** The default policy posture is **strict**:
  LOW-confidence findings are still redacted. Users who prefer a
  lighter touch can switch to a `lenient` policy that raises every
  detector's effective threshold by one step.
- **Consequences:**
  - The v0.1 product errs toward over-redaction on ambiguous
    inputs.
  - The UI surfaces a "Review carefully" badge whenever any
    `low`-confidence finding contributed to the output, so the user
    can spot over-redaction without inspecting the manifest.
  - Lenient mode is documented but not the recommended default.

---

## ADR-010 — Project layout: single Python package under `src/redact_ai/`

- **Date:** 2026-05-10
- **Status:** Accepted
- **Context:** ADR-003 deliberately kept the v0.1 specs
  technology-agnostic. The recommended stack
  ([`TECH_STACK_OPTIONS_v0.1.md`](./TECH_STACK_OPTIONS_v0.1.md) §A)
  is Python; building the v0.1 application requires a concrete
  module map and packaging strategy.
- **Decision:** Use a **single Python package** (`src/redact_ai/`)
  with a `pyproject.toml` (PEP 621) declaring direct dependencies,
  and `uv.lock` for reproducible installs. The full layout is
  pinned in [`BUILD_SPEC_v0.1.md`](./BUILD_SPEC_v0.1.md) §4.
- **Consequences:**
  - The pipeline boundaries from ADR-004 map 1:1 to subpackages
    (`pipeline/ingest`, `pipeline/ocr`, `pipeline/detect`,
    `pipeline/redact`, `pipeline/report`).
  - The FastAPI surface lives in `redact_ai.server`, isolated from
    pipeline modules so the same pipeline can be re-hosted in v1.0+
    (Option D in the tech-stack doc) without touching detection
    code.
  - A future Rust core (Option C) can be introduced as a peer
    package consumed via `pyo3` without restructuring this layout.

---

## ADR-011 — Add spaCy NER as a default name detector (ID-006)

- **Date:** 2026-05-11
- **Status:** Accepted
- **Context:** The v0.1 `FullNameDetector` (ID-001) is dictionary-driven
  using ~744 US-centric English given/family names
  (`names_given_en_us.txt`, `names_family_en_us.txt`). Field testing on
  a GitHub-profile screenshot showed it silently missing common
  non-Western names (e.g. "Nadeem Shaikh") because neither token is in
  the dictionary. This is a recall failure of the kind ADR-005
  ("fail closed") and NFR-2.1 (≥95% recall) explicitly call out as a
  safety issue, not a quality issue.
  [`TECH_STACK_OPTIONS_v0.1.md`](./TECH_STACK_OPTIONS_v0.1.md) §A.2 and
  §Operational Considerations anticipated this exact moment: "spaCy,
  Hugging Face, transformers … re-evaluated only when project-owned
  regex/dictionary detectors miss too much against the golden corpus."
- **Decision:** Add a new IDENTITY detector **ID-006
  PersonNameNerDetector** that runs spaCy NER on every OCR line and
  emits a finding for every `PERSON` entity. `spacy==3.7.5` joins the
  required dependency set, and the `en_core_web_md` model wheel is
  declared as a PEP 508 direct-URL dependency in
  [`pyproject.toml`](../pyproject.toml) so `pip install` / `uv sync`
  / `pipx install` pulls it automatically — no separate
  `python -m spacy download` step is required (the small model is
  rejected because it needs sentential context that OCR rarely
  provides — a bare "Nadeem Shaikh" on a screenshot line is missed
  by `_sm` and caught by `_md`). ID-006 is enabled by default in
  the strict policy at `threshold: medium`. ID-001 is retained
  unchanged as a precision layer; both detectors can co-fire on the
  same span and the merge stage de-duplicates within IDENTITY.
- **Consequences:**
  - Default install footprint grows by ~100 MB (spaCy library
    ~50 MB + `en_core_web_md` weights ~50 MB), staying well under
    NFR-1.2's 1 GB ceiling.
  - Server cold-start is unaffected because the spaCy model is
    lazy-loaded on first detection (cached module-level
    afterwards), matching the existing "Lazy-load OCR + detectors
    after the server is bound" pattern documented in
    [`TECH_STACK_OPTIONS_v0.1.md`](./TECH_STACK_OPTIONS_v0.1.md)
    §Risk Register. First-request latency rises by ~2 s; the 3 s
    end-to-end budget (NFR-1.1) is preserved for steady-state
    requests.
  - Local-first (ADR-002, NFR-3.1) preserved: the model runs
    entirely on-device. The model wheel is fetched at
    `pip install` / `uv sync` time as a normal dependency, not at
    runtime — no network call ever occurs during a redaction
    operation.
  - PyPI distribution caveat: direct-URL deps work transparently
    for installs from a git clone, `pipx install git+...`, or
    `uv sync` from a checkout. If/when `redact-ai` is published to
    PyPI, the install mechanism is revisited (vendoring the model
    into the wheel, or moving to a first-run consent prompt with an
    ADR-002 amendment).
  - Determinism (NFR-2.3) preserved: spaCy NER uses greedy
    decoding and is deterministic for a fixed model version and
    input.
  - Fail-closed (ADR-005) preserved: if the spaCy model is not
    available at runtime, the detector raises `E_POLICY` rather
    than silently returning empty findings.
  - Supersedes the "deliberately not pulled into the v0.1
    baseline" note in
    [`TECH_STACK_OPTIONS_v0.1.md`](./TECH_STACK_OPTIONS_v0.1.md)
    §A.2 and the "not part of the v0.1 stack" note in
    §Operational Considerations. Those two passages are updated
    in the same change as this ADR.
  - The §15 / NFR-2.1 95% recall floor remains the empirical
    check. If a future benchmark shows ID-006 underperforming
    transformer-based NER on the curated corpus, this ADR is
    revisited and a transformer model (e.g. `en_core_web_trf`)
    becomes the default.

---

## ADR-012 — Add face detection as ID-007, splitting detect into text + vision branches

- **Date:** 2026-05-11
- **Status:** Accepted
- **Context:** The v0.1 detect stage operates exclusively on OCR
  output (text tokens with bboxes). The user's reference screenshot
  is a GitHub profile page with a circular headshot in the upper
  left; on a freshly-merged pipeline `Nadeem Shaikh` redacts
  correctly via ID-006 but the avatar itself remains visible
  because no detector consumes pixel data. A privacy tool that
  promises to redact identity-leaking content but leaves the user's
  face untouched fails the product's core promise as starkly as
  missing a name. The original design (see ADR-004 and the LO-002
  "image-based detection deferred" note in
  [`DETECTORS_v0.1.md`](./DETECTORS_v0.1.md)) deferred image-content
  detection to a future release; this ADR reverses that deferral
  for the face-photo case.
- **Decision:** Introduce a new rule **ID-007
  FacePhotoDetector** under the `IDENTITY` category. It runs
  OpenCV's frontal-face Haar cascade
  (`haarcascade_frontalface_default.xml`) against the
  ingest-stage `original` image and emits one finding per face in
  input pixel coordinates. The detect stage gains a parallel
  *vision* branch:
  - `pipeline.detect.registry.REGISTRY` keeps the existing
    OCR-text detectors.
  - A new `VISION_REGISTRY` maps pixel-domain rule IDs to detector
    classes.
  - The pipeline orchestrator runs both branches and concatenates
    findings before the merge stage (which already dedupes
    overlapping bboxes within a category).

  `opencv-python-headless==4.10.0.84` joins the required
  dependencies. ID-007 is enabled by default in the strict policy
  at `threshold: medium`. Findings carry no `matched_text` (image
  regions, not text spans) which is consistent with ADR-006's
  manifest-safety stance.
- **Consequences:**
  - Default install footprint grows by ~30 MB
    (opencv-python-headless), staying well under NFR-1.2's 1 GB
    ceiling and ADR-008's PaddleOCR precedent.
  - Frontal-face cascade is fast (~50 ms on a 1080p screenshot)
    and entirely on-device; ADR-002 and NFR-3.1 preserved.
  - Deterministic per NFR-2.3 — Haar cascades are pure C++ with
    no stochastic components.
  - Known limitation: profile-view and heavily-occluded faces are
    missed. The "Trigger to revisit" is a corpus-wide face-recall
    benchmark dropping below 90 %; in that case the alternatives
    are MediaPipe Face Detection (~20 MB, better at angles) or a
    YOLO-family face model.
  - Supersedes the "LO-002 image-based detection deferred" note
    in [`DETECTORS_v0.1.md`](./DETECTORS_v0.1.md) for the
    face-photo case only. LO-002 (vehicle plates) and other
    image-content detectors remain deferred.

---

## ADR-013 — Add GLiNER as an optional strong PII engine (ML-001)

- **Date:** 2026-07-21
- **Status:** Accepted
- **Context:** The v0.1 detect stage is regex + dictionary +
  label-trigger rules plus spaCy `en_core_web_md` (`ID-006`,
  PERSON-only, en-US). Recall is structurally bounded to what those
  rules encode: non-Western names, unlabeled IDs, addresses without a
  street suffix, and PHI in prose are missed. Adding more regex chases
  the long tail forever. A generalist ML NER raises the floor across
  every category at once. The constraint is that the engine must not
  weaken the two guarantees that define the product: local-first
  operation (ADR-002) and deterministic output (NFR-2.3), and it must
  not bloat the base install (the same footprint concern as ADR-011).
- **Decision:** Introduce rule **ML-001 GlinerPiiDetector**, a
  transformer-based generalist PII engine built on **GLiNER** — the
  current best OSS PII NER (GLiNER2-PII leads the SPY span-F1
  benchmark; the encoder scores an arbitrary label schema in a single
  deterministic forward pass and runs on CPU). It **complements** the
  deterministic detectors rather than replacing them: regex+checksum
  stays authoritative for structured identifiers (Luhn PANs, IBAN
  mod-97, cloud-key prefixes) where a validator beats a probabilistic
  model.
  - **Optional, disabled by default.** The runtime ships in the
    `redact-ai[strong]` extra (`gliner` + its torch/transformers/
    huggingface-hub chain). `ML-001` is present but `enabled: false` in
    the shipped policy, so a base install never imports GLiNER. Users
    opt in with `pip install redact-ai[strong]` and the enabled
    `examples/strong_policy.yaml`.
  - **Single rule id, per-finding category.** The rule-id regex
    (`^[A-Z]{2}-[0-9]{3}$`) forbids a cross-category id; `ML-001` is the
    policy handle (one threshold, one switch) while each
    `Finding.category` comes from a configurable label→category map, so
    merge/threshold/report logic is unchanged.
  - **Default model `urchade/gliner_multi_pii-v1`, pinned to an immutable
    commit revision** (stable runtime, proven); GLiNER2-PII and
    `nvidia/gliner-PII` are reachable via `overrides.model` (+ `revision`).
    Score threshold, label map, and `allow_download` are also
    policy-overridable. The `gliner` runtime is exact-pinned in the extra.
  - **Determinism (NFR-2.3):** model loaded in eval mode, greedy/argmax
    decoding, no sampling, weights pinned by revision — a pure function of
    `(model revision, input)`. `gliner` is imported lazily inside the
    cached loader so registering the detector never pulls torch.
  - **Local-first (ADR-002):** loaded with `local_files_only` from the
    local Hugging Face cache — the redaction hot path never touches the
    network. Fetching is an explicit install/prefetch step (or a one-time
    `allow_download: true`); a cold cache fails closed.
  - **Fail-closed (ADR-005):** enabled without the extra or a cached model
    → `E_POLICY`, which the pipeline propagates as **fatal** for the whole
    request rather than downgrading to a partial-failure warning, so an
    opted-in run never silently misses the strong engine's PII classes.
- **Consequences:**
  - Base install and its footprint are unchanged; only opt-in users pay
    the ~1.2 GB model + torch cost.
  - Recall rises across every category for opt-in users.
  - Byte-identical output across *different* hardware is not yet
    guaranteed (transformer float ops vary by CPU/BLAS threads); logical
    determinism holds per machine. An ONNX-runtime path is a candidate
    follow-up if cross-machine byte-identity becomes required.
  - Behavioral validation against the real model is performed in a
    network-enabled environment; unit tests mock the model loader.

---

## ADR-014 — Add OpenMed as a second optional strong engine (ML-002)

- **Date:** 2026-07-23
- **Status:** Accepted
- **Context:** ML-001 (GLiNER, ADR-013) raised recall broadly but is weak
  on the **structured PHI** a clinical document carries. On a sample OCT eye
  report, GLiNER missed the patient ID, both dates, the appointment time, and
  the "Consultant Ophthalmologist" occupation, while a dedicated PII
  token-classifier (OpenMed) caught them cleanly. Conversely GLiNER is the
  only engine that reads a free-text diagnosis as a health condition. The two
  are complementary, not competing.
- **Decision:** Introduce rule **ML-002 OpenMedPiiDetector**, a transformer
  `token-classification` de-identification engine built on **OpenMed**
  (`OpenMed/OpenMed-PII-SuperClinical-Large-434M-v1` by default). It
  **complements** ML-001 and the deterministic detectors; none is removed.
  - **Same optional extra, disabled by default.** ML-002 ships in the
    existing `redact-ai[strong]` extra and is `enabled: false` in the shipped
    policy. It is enabled alongside ML-001 in `examples/strong_policy.yaml`.
  - **Own loader, not a model swap into ML-001.** GLiNER uses zero-shot label
    prompting (`predict_entities`); OpenMed is a fixed-label `transformers`
    pipeline with `aggregation_strategy="simple"` — different call contracts,
    separate lazy-imported loaders. Separate rule ids let a policy enable
    either engine alone.
  - **Determinism / local-first / fail-closed** are identical to ML-001:
    eval-mode argmax (NFR-2.3), `local_files_only` from the HF cache
    (ADR-002), and `E_POLICY`-fatal when the extra or model is absent
    (ADR-005). Default `score_threshold` 0.5 suppresses the sub-0.5 garble the
    model emits on poor OCR.
  - **Extra pin set resolved.** Enabling both engines forced a dependency
    reconciliation: `gliner` bumped to 0.2.27 (0.2.5 breaks with modern
    huggingface_hub), `transformers` pinned to 4.53.3 (inside gliner's
    supported range and used directly by ML-002), and a hard `numpy<2` guard
    added — the strong extra's graph can otherwise drift numpy to 2.x, which
    breaks spaCy's compiled thinc ABI and takes ID-006 down with it.
- **Consequences:**
  - Opt-in users gain strong structured-PHI recall on top of GLiNER's
    free-text coverage; base install footprint is unchanged.
  - Two ML models load when both are enabled (~1.1 GB each). Overlapping
    findings are deduplicated by the existing merge stage.
  - Same per-machine (not cross-machine) determinism caveat as ADR-013.

## ADR-015 — Two-pass OCR text-region contrast boost

- **Date:** 2026-07-23
- **Status:** Accepted
- **Context:** Detection recall is bounded by OCR (ADR-008). On the sample
  report, Tesseract read a printed "Dr. Laura Bennett, MD" line and the
  signature as sub-0.6-confidence noise (`lie hl`), so **no** NER engine —
  GLiNER, OpenMed, or spaCy — could redact them. The input already clears the
  ingest upscale floor (`_OCR_TARGET_MIN_SIDE`), so more upscaling was not the
  lever; low local contrast on small print was.
- **Decision:** In `TesseractAdapter.recognise`, run a first `image_to_data`
  pass to locate word boxes, dilate them into text regions, apply Otsu
  binarisation **only inside those regions** on a copy, then run the
  authoritative pass on the boosted image. Pixels outside any word box are
  byte-identical, so colour/medical imagery (OCT B-scans, fundus photos) is
  never degraded. Deterministic (fixed kernel + Otsu argmax, NFR-2.3); a
  pure-image input with no word boxes is returned unchanged.
  - This lives in the OCR adapter, not ingest: binarisation does not move
    coordinates, so the ingest `AffineTransform` is not involved, and the step
    is naturally OCR-box-driven. It is engine-agnostic in spirit — a future
    PaddleOCR adapter would apply the same two-pass shape.
- **Consequences:**
  - Recovers small-font printed PII/PHI that all detectors previously missed;
    on the sample report the patient name, ID, referring doctor, DOB, dates,
    time, and occupation are now redacted.
  - Two OCR passes roughly double OCR latency; acceptable for a
    correctness/privacy gain (a missed identifier is a privacy failure,
    ADR-005).
  - **Note — ADR-008 discrepancy.** ADR-008 records PaddleOCR as the intended
    v0.1 default, but the code ships `TesseractAdapter` (a `paddle.py` adapter
    stub exists but is not wired). This preprocessing is engine-agnostic and
    benefits either; reconciling the default-engine choice is tracked
    separately and out of scope here.

---

> TODO: Future ADRs will be appended here as design choices are made.
