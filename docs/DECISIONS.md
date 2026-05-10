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

## ADR-008 — Tesseract is the v0.1 default OCR engine

- **Date:** 2026-05-10
- **Status:** Accepted
- **Context:**
  [`TECH_STACK_OPTIONS_v0.1.md`](./TECH_STACK_OPTIONS_v0.1.md) left
  the v0.1 OCR engine as an open question (Tesseract for breadth vs.
  PaddleOCR for accuracy). Tesseract is ~80 MB total install,
  available on every supported platform via standard package
  managers, and ships with bbox metadata sufficient for our
  document model. PaddleOCR adds 0.5–1 GB and a heavy ML runtime
  (`paddlepaddle`) that conflicts with the v0.1 "lean baseline"
  goal.
- **Decision:** v0.1 ships **Tesseract** (via `pytesseract`) as the
  default OCR adapter. PaddleOCR is provided as the opt-in
  `redact-ai[ocr-paddle]` extra; the adapter exists, is loadable,
  and runs the golden corpus, but is not the recall baseline for
  v0.1 NFR-2.1.
- **Consequences:**
  - `recognise()` returns Tesseract token-level confidence on the
    `0.0–1.0` scale (after dividing the engine's `0–100`).
  - The recall target (≥ 95% on the curated corpus) is measured
    against Tesseract output. A miss attributable to OCR triggers
    re-evaluation of PaddleOCR for v0.2, not a v0.1 default change.
  - First-run OS firewall prompts and Tesseract-install hints are
    documented in `CONTRIBUTING.md`.

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

> TODO: Future ADRs will be appended here as design choices are made.
