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

> TODO: Future ADRs will be appended here as design choices are made.
